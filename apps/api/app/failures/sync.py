"""
TraceHarbor API — Failure Event Synchronization & Embedding Ingestion Pipeline

Idempotently scans existing runs, spans, evaluation experiments, and safety campaigns
to extract and normalize failure events without duplicates. Handles content-hash deduplication
and bounded batch embedding generation.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.failures.embedding import EmbeddingError, get_embedding_provider
from app.failures.normalizer import (
    FailureEventData,
    normalize_experiment_result_failure,
    normalize_run_failure,
    normalize_safety_test_failure,
    normalize_span_failure,
)
from app.models.experiment import Experiment
from app.models.experiment_result import ExperimentResult
from app.models.failure import FailureEvent
from app.models.run import Run
from app.models.safety import SafetyCampaign, SafetyTestResult
from app.models.span import Span

logger = logging.getLogger(__name__)


async def sync_failure_events(
    db: AsyncSession,
    project_id: uuid.UUID,
    auto_embed: bool = True,
) -> dict[str, int]:
    """
    Idempotently scan all supported failure sources for the given project and
    create normalized FailureEvent records if they do not already exist.

    Sources:
    1. Runs with status='error' or non-empty error field
    2. Spans with status='error' or non-empty error field
    3. Experiment results with status in ('failed', 'error')
    4. Safety test results with passed=False
    """
    scanned = 0
    created = 0
    skipped = 0

    candidate_events: list[FailureEventData] = []

    # 1. Failed Runs
    run_query = (
        select(Run)
        .where(
            Run.project_id == project_id,
            (Run.status == "error") | (Run.error.isnot(None) & (Run.error != "")),
        )
    )
    run_rows = (await db.scalars(run_query)).all()
    for run in run_rows:
        scanned += 1
        err_msg = run.error or f"Run failed with status: {run.status}"
        data = normalize_run_failure(
            run_id=run.id,
            project_id=run.project_id,
            error=err_msg,
            started_at=run.started_at,
            metadata=run.run_metadata,
        )
        candidate_events.append(data)

    # 2. Failed Spans
    span_query = (
        select(Span, Run.project_id)
        .join(Run, Span.run_id == Run.id)
        .where(
            Run.project_id == project_id,
            (Span.status == "error") | (Span.error.isnot(None) & (Span.error != "")),
        )
    )
    span_rows = (await db.execute(span_query)).all()
    for span, proj_id in span_rows:
        scanned += 1
        err_msg = span.error or f"Span error in {span.name}"
        data = normalize_span_failure(
            span_id=span.id,
            run_id=span.run_id,
            project_id=proj_id,
            error=err_msg,
            span_type=span.span_type,
            span_name=span.name,
            model=span.model,
            started_at=span.started_at,
        )
        candidate_events.append(data)

    # 3. Failed Experiment Results
    exp_query = (
        select(ExperimentResult, Experiment)
        .join(Experiment, ExperimentResult.experiment_id == Experiment.id)
        .where(
            Experiment.project_id == project_id,
            ExperimentResult.status.in_(["failed", "error"]),
        )
    )
    exp_rows = (await db.execute(exp_query)).all()
    for res, exp in exp_rows:
        scanned += 1
        data = normalize_experiment_result_failure(
            result_id=res.id,
            project_id=exp.project_id,
            error=res.error,
            status=res.status,
            experiment_name=exp.name,
            agent_name=exp.agent_name,
            agent_version=exp.agent_version,
            run_id=None,
            created_at=res.created_at,
        )
        candidate_events.append(data)

    # 4. Failed Safety Test Results
    safety_query = (
        select(SafetyTestResult, SafetyCampaign)
        .join(SafetyCampaign, SafetyTestResult.campaign_id == SafetyCampaign.id)
        .where(
            SafetyCampaign.project_id == project_id,
            SafetyTestResult.passed.is_(False),
        )
    )
    safety_rows = (await db.execute(safety_query)).all()
    for s_res, camp in safety_rows:
        scanned += 1
        err_msg = s_res.output_text or f"Safety test failed: {s_res.category} ({s_res.severity})"
        data = normalize_safety_test_failure(
            result_id=s_res.id,
            project_id=camp.project_id,
            error=err_msg,
            category=s_res.category,
            severity=s_res.severity,
            agent_name=camp.agent_name,
            agent_version=camp.agent_version,
            campaign_name=camp.name,
            run_id=None,
            created_at=s_res.created_at,
        )
        candidate_events.append(data)

    # Deduplicate against existing failure_events
    if candidate_events:
        existing_sources_query = select(FailureEvent.source_type, FailureEvent.source_id).where(
            FailureEvent.project_id == project_id
        )
        existing_set = set((await db.execute(existing_sources_query)).all())

        new_events: list[FailureEvent] = []
        for c in candidate_events:
            if (c.source_type, c.source_id) in existing_set:
                skipped += 1
                continue

            existing_set.add((c.source_type, c.source_id))
            ev = FailureEvent(**c.to_dict())
            new_events.append(ev)
            db.add(ev)
            created += 1

        if new_events:
            await db.commit()
            if auto_embed:
                await embed_pending_failure_events(db, project_id=project_id)

    return {
        "scanned": scanned,
        "created": created,
        "skipped": skipped,
    }


async def embed_pending_failure_events(
    db: AsyncSession,
    project_id: uuid.UUID | None = None,
    limit: int = 100,
) -> int:
    """
    Process pending or failed failure events and generate embeddings.
    Uses content-hash caching so unchanged texts are never re-embedded.
    """
    provider = get_embedding_provider()
    if provider is None:
        # Mark all pending as skipped since no provider is configured
        query = select(FailureEvent).where(
            FailureEvent.embedding_status == "pending"
        )
        if project_id:
            query = query.where(FailureEvent.project_id == project_id)
        events = (await db.scalars(query.limit(limit))).all()
        for ev in events:
            ev.embedding_status = "skipped"
            ev.embedding_error = "No embedding provider configured"
        if events:
            await db.commit()
        return 0

    # Query pending or failed events with attempts < 3
    query = (
        select(FailureEvent)
        .where(
            FailureEvent.embedding_status.in_(["pending", "failed"]),
            FailureEvent.embedding_attempts < 3,
        )
    )
    if project_id:
        query = query.where(FailureEvent.project_id == project_id)

    pending_events = (await db.scalars(query.limit(limit))).all()
    if not pending_events:
        return 0

    # 1. Content-hash cache lookup: find vectors for existing hashes
    content_hashes = {ev.content_hash for ev in pending_events if ev.content_hash}
    cached_vectors: dict[str, list[float]] = {}

    if content_hashes:
        cached_query = select(FailureEvent.content_hash, FailureEvent.embedding).where(
            FailureEvent.content_hash.in_(content_hashes),
            FailureEvent.embedding_status == "completed",
            FailureEvent.embedding.isnot(None),
        )
        for h, vec in (await db.execute(cached_query)).all():
            if vec is not None and h not in cached_vectors:
                cached_vectors[h] = list(vec)

    # 2. Separate events into cached vs need embedding
    to_embed_texts: list[str] = []
    text_to_events: dict[str, list[FailureEvent]] = {}
    completed_count = 0

    for ev in pending_events:
        if ev.content_hash and ev.content_hash in cached_vectors:
            # Reuse cached embedding!
            ev.embedding = cached_vectors[ev.content_hash]
            ev.embedding_status = "completed"
            ev.embedding_error = None
            completed_count += 1
        else:
            txt = ev.normalized_text
            if txt not in text_to_events:
                text_to_events[txt] = []
                to_embed_texts.append(txt)
            text_to_events[txt].append(ev)

    # 3. Call provider for un-cached texts
    if to_embed_texts:
        try:
            vectors = await provider.embed_texts(to_embed_texts)
            for txt, vec in zip(to_embed_texts, vectors, strict=True):
                for ev in text_to_events[txt]:
                    ev.embedding = vec
                    ev.embedding_status = "completed"
                    ev.embedding_error = None
                    completed_count += 1
        except EmbeddingError as e:
            logger.error("Embedding provider failed: %s", str(e))
            for txt in to_embed_texts:
                for ev in text_to_events[txt]:
                    ev.embedding_attempts += 1
                    ev.embedding_status = "failed"
                    ev.embedding_error = str(e)
        except Exception as e:
            logger.exception("Unexpected error during embedding: %s", str(e))
            for txt in to_embed_texts:
                for ev in text_to_events[txt]:
                    ev.embedding_attempts += 1
                    ev.embedding_status = "failed"
                    ev.embedding_error = str(e)

    await db.commit()
    return completed_count
