"""
TraceHarbor API — Failure Similarity Search and Clustering Engine

Algorithm: Threshold-Based Incremental Clustering (threshold_v1)
==================================================================

Strategy:
  Single-pass incremental clustering using cosine similarity with a
  configurable threshold. New failure events are compared against existing
  cluster centroids (represented by the centroid event's embedding) using
  pgvector nearest-neighbor search. If the closest cluster is within the
  similarity threshold, the event joins that cluster. Otherwise, a new
  single-event cluster is created.

Why this algorithm:
  - Incremental: processes new events without full recomputation
  - Bounded: uses pgvector indexed search (not pairwise comparisons)
  - Conservative: high default threshold avoids merging unrelated failures
  - Simple: predictable behavior, easy to explain and debug

Limitations:
  - Clusters are defined by their first representative — chain drift is
    possible over many similar-but-gradually-changing failures
  - Recomputation replaces all clusters (not incremental refinement)
  - Cosine similarity may group unrelated failures that share common
    boilerplate error phrasing
  - No hierarchical or density-based clustering

Configuration:
  - CLUSTERING_SIMILARITY_THRESHOLD: minimum cosine similarity (0.0–1.0)
    to join a cluster. Default 0.85 (conservative).
  - CLUSTERING_MIN_CLUSTER_SIZE: minimum events to form a reportable
    cluster. Default 2.
  - CLUSTERING_MAX_CANDIDATES: maximum candidate events for a single
    clustering job. Default 1000.
"""

import logging
import math
import re
import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.failures.embedding import get_embedding_provider
from app.models.failure import ClusterStatusChange, FailureCluster, FailureEvent

logger = logging.getLogger(__name__)

# Algorithm version identifier — stored on each cluster
ALGORITHM_VERSION = "threshold_v1"


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    Returns a value in [-1, 1] where 1 means identical direction.
    """
    if len(a) != len(b):
        raise ValueError(f"Vector dimension mismatch: {len(a)} vs {len(b)}")

    dot = sum(x * y for x, y in zip(a, b, strict=True))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot / (mag_a * mag_b)


def find_similar_events(
    query_embedding: list[float],
    candidate_embeddings: list[tuple[uuid.UUID, list[float]]],
    threshold: float = 0.85,
    max_results: int = 50,
) -> list[tuple[uuid.UUID, float]]:
    """
    Find events with embeddings similar to the query.

    Args:
        query_embedding: the query vector
        candidate_embeddings: list of (event_id, embedding) tuples
        threshold: minimum cosine similarity to include
        max_results: maximum number of results

    Returns:
        List of (event_id, similarity_score) sorted by descending similarity
    """
    results: list[tuple[uuid.UUID, float]] = []

    for event_id, embedding in candidate_embeddings:
        try:
            sim = cosine_similarity(query_embedding, embedding)
            if sim >= threshold:
                results.append((event_id, sim))
        except ValueError:
            continue

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:max_results]


def generate_cluster_title(summaries: list[str]) -> str:
    """
    Generate a deterministic cluster title from failure summaries.
    Uses the most common error type/pattern as the title.
    """
    if not summaries:
        return "Unknown failure pattern"

    # Extract common prefixes and error types
    words_counter: Counter = Counter()
    for summary in summaries:
        # Take the first meaningful fragment (up to 80 chars)
        fragment = summary.strip()[:80]
        # Extract error type if present (e.g., "TypeError:", "ConnectionError:")
        for word in fragment.split():
            if word.endswith(":") and len(word) > 3:
                words_counter[word.rstrip(":")] += 1
            elif word.endswith("Error") or word.endswith("Exception"):
                words_counter[word] += 1

    if words_counter:
        most_common = words_counter.most_common(1)[0][0]
        count = len(summaries)
        return f"Similar failure pattern: {most_common} ({count} events)"

    # Fall back to truncated first summary
    first = summaries[0].strip()
    if len(first) > 100:
        first = first[:97] + "..."
    return f"Similar failure pattern: {first}"


def compute_cluster_metadata(
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Compute aggregate metadata for a cluster from its member events.

    Args:
        events: list of event dicts with keys: severity, failure_category,
                agent_name, agent_version, model_name, run_id, trace_id,
                error_summary, occurred_at

    Returns:
        Dict with cluster metadata fields.
    """
    if not events:
        return {
            "dominant_category": "unknown",
            "severity_distribution": {},
            "event_count": 0,
            "first_seen_at": datetime.now(UTC),
            "last_seen_at": datetime.now(UTC),
            "representative_summary": None,
            "affected_agents": [],
            "affected_models": [],
            "representative_traces": [],
        }

    # Severity distribution
    severity_dist: dict[str, int] = Counter()
    category_counts: Counter = Counter()
    agents: set[str] = set()
    models: set[str] = set()
    traces: list[dict[str, str]] = []
    timestamps: list[datetime] = []

    for event in events:
        severity_dist[event.get("severity", "medium")] += 1
        category_counts[event.get("failure_category", "unknown")] += 1

        agent = event.get("agent_name")
        version = event.get("agent_version")
        if agent:
            agent_str = f"{agent}"
            if version:
                agent_str += f"@{version}"
            agents.add(agent_str)

        model = event.get("model_name")
        if model:
            models.add(model)

        run_id = event.get("run_id")
        trace_id = event.get("trace_id")
        if run_id and len(traces) < 5:
            traces.append({"run_id": str(run_id), "trace_id": str(trace_id or "")})

        occurred_at = event.get("occurred_at")
        if occurred_at:
            timestamps.append(occurred_at)

    dominant_category = category_counts.most_common(1)[0][0] if category_counts else "unknown"

    # Sort timestamps
    timestamps.sort()

    return {
        "dominant_category": dominant_category,
        "severity_distribution": dict(severity_dist),
        "event_count": len(events),
        "first_seen_at": timestamps[0] if timestamps else datetime.now(UTC),
        "last_seen_at": timestamps[-1] if timestamps else datetime.now(UTC),
        "representative_summary": events[0].get("error_summary") if events else None,
        "affected_agents": sorted(agents),
        "affected_models": sorted(models),
        "representative_traces": traces[:5],
    }


def assign_events_to_clusters(
    events_with_embeddings: list[tuple[uuid.UUID, list[float], dict[str, Any]]],
    existing_clusters: list[
        tuple[uuid.UUID, list[float], dict[str, Any]]
    ],
    threshold: float = 0.85,
    min_cluster_size: int = 2,
) -> dict[str, Any]:
    """
    Assign failure events to clusters using threshold-based similarity.

    Args:
        events_with_embeddings: list of (event_id, embedding, event_data) tuples
        existing_clusters: list of (cluster_id, centroid_embedding, cluster_data)
        threshold: minimum cosine similarity to join a cluster
        min_cluster_size: minimum events to retain a cluster

    Returns:
        Dict with:
        - assignments: {event_id: cluster_id}
        - new_clusters: list of new cluster data dicts
        - updated_clusters: list of cluster_ids that gained new members
        - unassigned: list of event_ids that didn't reach min_cluster_size
    """
    assignments: dict[uuid.UUID, uuid.UUID] = {}
    cluster_members: dict[uuid.UUID, list[dict[str, Any]]] = {}
    cluster_centroids: dict[uuid.UUID, list[float]] = {}
    new_clusters: list[dict[str, Any]] = []
    updated_cluster_ids: set[uuid.UUID] = set()

    # Initialize existing clusters
    for cluster_id, centroid, _ in existing_clusters:
        cluster_centroids[cluster_id] = centroid
        cluster_members[cluster_id] = []

    # Process each event
    for event_id, embedding, event_data in events_with_embeddings:
        best_cluster_id: uuid.UUID | None = None
        best_similarity: float = 0.0

        # Find the most similar existing cluster
        for cluster_id, centroid in cluster_centroids.items():
            try:
                sim = cosine_similarity(embedding, centroid)
                if sim >= threshold and sim > best_similarity:
                    best_similarity = sim
                    best_cluster_id = cluster_id
            except ValueError:
                continue

        if best_cluster_id is not None:
            # Assign to existing cluster
            assignments[event_id] = best_cluster_id
            cluster_members[best_cluster_id].append(event_data)
            updated_cluster_ids.add(best_cluster_id)
        else:
            # Create a new single-event cluster candidate
            new_cluster_id = uuid.uuid4()
            cluster_centroids[new_cluster_id] = embedding
            cluster_members[new_cluster_id] = [event_data]
            assignments[event_id] = new_cluster_id

    # Build new cluster metadata
    unassigned: list[uuid.UUID] = []
    for cluster_id, members in cluster_members.items():
        is_existing = any(cid == cluster_id for cid, _, _ in existing_clusters)
        if is_existing:
            continue  # existing clusters are updated separately

        if len(members) < min_cluster_size:
            # Below minimum — mark events as unassigned
            for event_id, assigned_cid in list(assignments.items()):
                if assigned_cid == cluster_id:
                    unassigned.append(event_id)
                    del assignments[event_id]
            continue

        summaries = [m.get("error_summary", "") for m in members]
        metadata = compute_cluster_metadata(members)
        new_clusters.append(
            {
                "id": cluster_id,
                "title": generate_cluster_title(summaries),
                **metadata,
                "algorithm_version": ALGORITHM_VERSION,
                "similarity_threshold": threshold,
            }
        )

    return {
        "assignments": assignments,
        "new_clusters": new_clusters,
        "updated_clusters": list(updated_cluster_ids),
        "unassigned": unassigned,
    }


def lexical_similarity(text_a: str, text_b: str) -> float:
    """
    Deterministic lexical similarity metric (token Jaccard index).
    Provided as a clearly-labelled fallback when vector embeddings are not configured.
    Returns a float in [0.0, 1.0].
    """
    if not text_a or not text_b:
        return 0.0

    tokens_a = set(re.findall(r"\w+", text_a.lower()))
    tokens_b = set(re.findall(r"\w+", text_b.lower()))

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return float(intersection / union) if union > 0 else 0.0


async def run_clustering_for_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    threshold: float = 0.85,
    min_cluster_size: int = 2,
    max_candidates: int = 1000,
) -> dict[str, Any]:
    """
    Execute bounded clustering for a given project.
    Groups failure events by similarity and creates/updates clusters.
    """
    # 1. Fetch existing clusters for project
    clusters_query = select(FailureCluster).where(FailureCluster.project_id == project_id)
    existing_cluster_models = (await db.scalars(clusters_query)).all()

    existing_clusters: list[tuple[uuid.UUID, list[float], dict[str, Any]]] = []
    cluster_by_id: dict[uuid.UUID, FailureCluster] = {}

    for c in existing_cluster_models:
        cluster_by_id[c.id] = c
        centroid = list(c.centroid_embedding) if c.centroid_embedding is not None else None
        if centroid is not None:
            existing_clusters.append((c.id, centroid, {
                "id": c.id,
                "title": c.title,
                "dominant_category": c.dominant_category,
            }))

    # 2. Fetch candidate events with embeddings
    events_query = (
        select(FailureEvent)
        .where(
            FailureEvent.project_id == project_id,
            FailureEvent.embedding.isnot(None),
            FailureEvent.embedding_status == "completed",
        )
        .order_by(FailureEvent.occurred_at.asc())
        .limit(max_candidates)
    )
    event_models = (await db.scalars(events_query)).all()
    if not event_models:
        return {
            "clusters_created": 0,
            "clusters_updated": 0,
            "events_assigned": 0,
            "events_unassigned": 0,
            "message": "No embedded events found for clustering",
        }

    events_with_embeddings: list[tuple[uuid.UUID, list[float], dict[str, Any]]] = []
    events_by_id: dict[uuid.UUID, FailureEvent] = {}

    for ev in event_models:
        events_by_id[ev.id] = ev
        vec = list(ev.embedding) if ev.embedding is not None else []
        ev_data = {
            "id": ev.id,
            "severity": ev.severity,
            "failure_category": ev.failure_category,
            "agent_name": ev.agent_name,
            "agent_version": ev.agent_version,
            "model_name": ev.model_name,
            "run_id": ev.run_id,
            "trace_id": ev.trace_id,
            "error_summary": ev.error_summary,
            "occurred_at": ev.occurred_at,
        }
        events_with_embeddings.append((ev.id, vec, ev_data))

    # 3. Run assignment algorithm
    res = assign_events_to_clusters(
        events_with_embeddings=events_with_embeddings,
        existing_clusters=existing_clusters,
        threshold=threshold,
        min_cluster_size=min_cluster_size,
    )

    assignments = res["assignments"]
    new_clusters_data = res["new_clusters"]
    updated_cluster_ids = res["updated_clusters"]
    unassigned = res["unassigned"]

    # 4. Persist new clusters
    created_clusters: list[FailureCluster] = []
    for cd in new_clusters_data:
        cid = cd["id"]
        # Find first member's embedding to serve as centroid
        member_events = [ev for eid, ev in events_by_id.items() if assignments.get(eid) == cid]
        centroid = list(member_events[0].embedding) if member_events and member_events[0].embedding is not None else None

        cluster_obj = FailureCluster(
            id=cid,
            project_id=project_id,
            title=cd["title"],
            dominant_category=cd["dominant_category"],
            severity_distribution=cd["severity_distribution"],
            event_count=cd["event_count"],
            first_seen_at=cd["first_seen_at"],
            last_seen_at=cd["last_seen_at"],
            representative_summary=cd["representative_summary"],
            affected_agents=cd["affected_agents"],
            affected_models=cd["affected_models"],
            representative_traces=cd["representative_traces"],
            status="new",
            algorithm_version=cd["algorithm_version"],
            similarity_threshold=cd["similarity_threshold"],
            centroid_embedding=centroid,
        )
        db.add(cluster_obj)
        created_clusters.append(cluster_obj)

        # Audit log for creation
        audit = ClusterStatusChange(
            cluster_id=cid,
            previous_status="none",
            new_status="new",
            resolution_notes="Cluster created by clustering engine",
        )
        db.add(audit)

    # 5. Update existing clusters
    for cid in updated_cluster_ids:
        if cid in cluster_by_id:
            c = cluster_by_id[cid]
            # Gather all members (existing + newly assigned)
            all_members_query = select(FailureEvent).where(
                (FailureEvent.cluster_id == cid) | (FailureEvent.id.in_([eid for eid, assigned_c in assignments.items() if assigned_c == cid]))
            )
            all_members = (await db.scalars(all_members_query)).all()
            member_dicts = [
                {
                    "severity": m.severity,
                    "failure_category": m.failure_category,
                    "agent_name": m.agent_name,
                    "agent_version": m.agent_version,
                    "model_name": m.model_name,
                    "run_id": m.run_id,
                    "trace_id": m.trace_id,
                    "error_summary": m.error_summary,
                    "occurred_at": m.occurred_at,
                }
                for m in all_members
            ]
            meta = compute_cluster_metadata(member_dicts)
            c.dominant_category = meta["dominant_category"]
            c.severity_distribution = meta["severity_distribution"]
            c.event_count = meta["event_count"]
            c.first_seen_at = meta["first_seen_at"]
            c.last_seen_at = meta["last_seen_at"]
            c.representative_summary = meta["representative_summary"]
            c.affected_agents = meta["affected_agents"]
            c.affected_models = meta["affected_models"]
            c.representative_traces = meta["representative_traces"]

    # 6. Update failure_events cluster_id foreign keys
    for event_id, cluster_id in assignments.items():
        if event_id in events_by_id:
            events_by_id[event_id].cluster_id = cluster_id

    for event_id in unassigned:
        if event_id in events_by_id:
            events_by_id[event_id].cluster_id = None

    await db.commit()

    return {
        "clusters_created": len(created_clusters),
        "clusters_updated": len(updated_cluster_ids),
        "events_assigned": len(assignments),
        "events_unassigned": len(unassigned),
    }


async def search_similar_failures(
    db: AsyncSession,
    project_id: uuid.UUID,
    query_text: str | None = None,
    event_id: uuid.UUID | None = None,
    threshold: float = 0.70,
    limit: int = 20,
) -> tuple[list[dict[str, Any]], str]:
    """
    Find failures similar to either an existing event or raw error text.
    Returns (results, method) where method is 'vector_similarity' or 'lexical_fallback'.
    """
    provider = get_embedding_provider()
    target_embedding: list[float] | None = None
    target_text: str = ""

    if event_id is not None:
        target_event = await db.get(FailureEvent, event_id)
        if not target_event or target_event.project_id != project_id:
            return [], "none"
        target_text = target_event.normalized_text
        if target_event.embedding is not None:
            target_embedding = list(target_event.embedding)

    if target_embedding is None and query_text:
        target_text = query_text
        if provider is not None:
            try:
                vectors = await provider.embed_texts([query_text])
                if vectors:
                    target_embedding = vectors[0]
            except Exception as e:
                logger.warning("Failed to embed query text: %s. Falling back to lexical search.", e)

    # 1. Vector similarity search if genuine embedding is available
    if target_embedding is not None:
        # Load project candidate events with embeddings
        query = (
            select(FailureEvent)
            .where(
                FailureEvent.project_id == project_id,
                FailureEvent.embedding.isnot(None),
            )
        )
        if event_id is not None:
            query = query.where(FailureEvent.id != event_id)

        candidates = (await db.scalars(query.limit(500))).all()
        scored: list[tuple[FailureEvent, float]] = []

        for cand in candidates:
            if cand.embedding is not None:
                try:
                    sim = cosine_similarity(target_embedding, list(cand.embedding))
                    if sim >= threshold:
                        scored.append((cand, sim))
                except ValueError:
                    continue

        scored.sort(key=lambda x: x[1], reverse=True)
        results = [
            {
                "event_id": ev.id,
                "error_summary": ev.error_summary,
                "failure_category": ev.failure_category,
                "severity": ev.severity,
                "agent_name": ev.agent_name,
                "agent_version": ev.agent_version,
                "model_name": ev.model_name,
                "similarity_score": round(score, 4),
                "cluster_id": ev.cluster_id,
                "occurred_at": ev.occurred_at.isoformat(),
            }
            for ev, score in scored[:limit]
        ]
        return results, "vector_similarity"

    # 2. Lexical fallback if no embedding is available
    if not target_text:
        return [], "none"

    query = select(FailureEvent).where(FailureEvent.project_id == project_id)
    if event_id is not None:
        query = query.where(FailureEvent.id != event_id)

    candidates = (await db.scalars(query.limit(500))).all()
    scored_lexical: list[tuple[FailureEvent, float]] = []

    for cand in candidates:
        sim = lexical_similarity(target_text, cand.normalized_text)
        if sim >= max(0.1, threshold - 0.4):  # Relaxed threshold for token overlap
            scored_lexical.append((cand, sim))

    scored_lexical.sort(key=lambda x: x[1], reverse=True)
    results = [
        {
            "event_id": ev.id,
            "error_summary": ev.error_summary,
            "failure_category": ev.failure_category,
            "severity": ev.severity,
            "agent_name": ev.agent_name,
            "agent_version": ev.agent_version,
            "model_name": ev.model_name,
            "similarity_score": round(score, 4),
            "cluster_id": ev.cluster_id,
            "occurred_at": ev.occurred_at.isoformat(),
        }
        for ev, score in scored_lexical[:limit]
    ]
    return results, "lexical_fallback"

