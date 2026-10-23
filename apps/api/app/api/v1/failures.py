"""
TraceHarbor API — Failure Intelligence & Semantic Clustering Endpoints

Phase 6: Provides REST endpoints for:
- Normalized failure events feed, inspection, and trace links
- Nearest-neighbor similarity search (semantic vector and lexical fallback)
- Persistent failure clusters with dominant categories and representative evidence
- Cluster status transitions and resolution audit trails
- Idempotent failure ingestion and clustering execution
"""

import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import resolve_project_id
from app.core.config import settings
from app.core.database import get_db
from app.failures.clustering import run_clustering_for_project, search_similar_failures
from app.failures.embedding import get_embedding_provider
from app.failures.sync import sync_failure_events
from app.models.failure import ClusterStatusChange, FailureCluster, FailureEvent
from app.schemas.failures import (
    ClusteringJobRequest,
    ClusteringJobResponse,
    ClusterStatusChangeResponse,
    ClusterStatusUpdateRequest,
    FailureClusterDetailResponse,
    FailureClusterListResponse,
    FailureClusterSummaryResponse,
    FailureEventListResponse,
    FailureEventResponse,
    FailureOverviewMetricsResponse,
    FailureSyncRequest,
    FailureSyncResponse,
    SimilarFailureItem,
    SimilarFailureSearchRequest,
    SimilarFailureSearchResponse,
)

router = APIRouter(tags=["Failure Intelligence"])


@router.get(
    "/failures/overview",
    response_model=FailureOverviewMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Failure Intelligence Overview Metrics",
)
async def get_failure_overview(
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> FailureOverviewMetricsResponse:
    """Retrieve top-level cluster intelligence metrics and system capability status."""
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID could not be determined.",
        )

    # 1. Total Failure Events
    total_events = (
        await db.scalar(
            select(func.count(FailureEvent.id)).where(FailureEvent.project_id == project_id)
        )
    ) or 0

    # 2. Total Clusters & Status Breakdown
    clusters_query = select(FailureCluster.status, func.count(FailureCluster.id)).where(
        FailureCluster.project_id == project_id
    ).group_by(FailureCluster.status)
    status_counts = dict((await db.execute(clusters_query)).all())
    total_clusters = sum(status_counts.values())

    # 3. Events by Severity
    sev_query = select(FailureEvent.severity, func.count(FailureEvent.id)).where(
        FailureEvent.project_id == project_id
    ).group_by(FailureEvent.severity)
    sev_counts = dict((await db.execute(sev_query)).all())

    # 4. Top Failure Categories
    cat_query = select(
        FailureEvent.failure_category, func.count(FailureEvent.id).label("cnt")
    ).where(
        FailureEvent.project_id == project_id
    ).group_by(
        FailureEvent.failure_category
    ).order_by(desc("cnt")).limit(5)
    top_categories = [
        {"category": cat, "count": cnt}
        for cat, cnt in (await db.execute(cat_query)).all()
    ]

    # 5. Top Affected Agents
    agent_query = select(
        FailureEvent.agent_name, func.count(FailureEvent.id).label("cnt")
    ).where(
        FailureEvent.project_id == project_id,
        FailureEvent.agent_name.isnot(None),
    ).group_by(
        FailureEvent.agent_name
    ).order_by(desc("cnt")).limit(5)
    top_agents = [
        {"agent_name": ag, "count": cnt}
        for ag, cnt in (await db.execute(agent_query)).all()
    ]

    provider = get_embedding_provider()
    provider_name = provider.provider_name if provider else "none"
    vector_available = provider is not None

    return FailureOverviewMetricsResponse(
        total_failure_events=total_events,
        total_clusters=total_clusters,
        clusters_by_status=status_counts,
        events_by_severity=sev_counts,
        top_failure_categories=top_categories,
        top_affected_agents=top_agents,
        embedding_provider=provider_name,
        vector_search_available=vector_available,
    )


@router.get(
    "/failures",
    response_model=FailureEventListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Normalized Failure Events",
)
async def list_failure_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    severity: str | None = Query(None),
    category: str | None = Query(None),
    agent_name: str | None = Query(None),
    cluster_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> FailureEventListResponse:
    """List normalized failure events with filtering, pagination, and tenant isolation."""
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID could not be determined.",
        )

    query = select(FailureEvent).where(FailureEvent.project_id == project_id)

    if severity:
        query = query.where(FailureEvent.severity == severity)
    if category:
        query = query.where(FailureEvent.failure_category == category)
    if agent_name:
        query = query.where(FailureEvent.agent_name == agent_name)
    if cluster_id:
        query = query.where(FailureEvent.cluster_id == cluster_id)
    if search:
        query = query.where(FailureEvent.error_summary.ilike(f"%{search}%"))
    if start_time:
        query = query.where(FailureEvent.occurred_at >= start_time)
    if end_time:
        query = query.where(FailureEvent.occurred_at <= end_time)

    # Count total matching
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.scalar(count_query)) or 0
    total_pages = max(1, math.ceil(total / page_size))

    # Paginate
    query = query.order_by(desc(FailureEvent.occurred_at)).offset((page - 1) * page_size).limit(page_size)
    events = (await db.scalars(query)).all()

    return FailureEventListResponse(
        items=[FailureEventResponse.model_validate(ev) for ev in events],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/failures/clusters",
    response_model=FailureClusterListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Semantic Failure Clusters",
)
async def list_failure_clusters(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    category: str | None = Query(None),
    search: str | None = Query(None),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> FailureClusterListResponse:
    """List semantic failure clusters with status filters and frequency stats."""
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID could not be determined.",
        )

    query = select(FailureCluster).where(FailureCluster.project_id == project_id)

    if status_filter:
        query = query.where(FailureCluster.status == status_filter)
    if category:
        query = query.where(FailureCluster.dominant_category == category)
    if search:
        query = query.where(FailureCluster.title.ilike(f"%{search}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.scalar(count_query)) or 0
    total_pages = max(1, math.ceil(total / page_size))

    query = query.order_by(desc(FailureCluster.last_seen_at)).offset((page - 1) * page_size).limit(page_size)
    clusters = (await db.scalars(query)).all()

    return FailureClusterListResponse(
        items=[FailureClusterSummaryResponse.model_validate(c) for c in clusters],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/failures/clusters/{cluster_id}",
    response_model=FailureClusterDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Failure Cluster Detail with Evidence",
)
async def get_failure_cluster_detail(
    cluster_id: uuid.UUID,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> FailureClusterDetailResponse:
    """Retrieve full failure cluster evidence, member events, and status audit trail."""
    cluster = await db.get(FailureCluster, cluster_id)
    if not cluster or (project_id and cluster.project_id != project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failure cluster not found.",
        )

    # Fetch recent member events
    events_query = (
        select(FailureEvent)
        .where(FailureEvent.cluster_id == cluster_id)
        .order_by(desc(FailureEvent.occurred_at))
        .limit(20)
    )
    events = (await db.scalars(events_query)).all()

    # Fetch status change history
    history_query = (
        select(ClusterStatusChange)
        .where(ClusterStatusChange.cluster_id == cluster_id)
        .order_by(desc(ClusterStatusChange.changed_at))
    )
    history = (await db.scalars(history_query)).all()

    res = FailureClusterSummaryResponse.model_validate(cluster)
    return FailureClusterDetailResponse(
        **res.model_dump(),
        recent_events=[FailureEventResponse.model_validate(ev) for ev in events],
        status_history=[ClusterStatusChangeResponse.model_validate(h) for h in history],
    )


@router.patch(
    "/failures/clusters/{cluster_id}/status",
    response_model=FailureClusterSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Cluster Investigation Status",
)
async def update_failure_cluster_status(
    cluster_id: uuid.UUID,
    payload: ClusterStatusUpdateRequest,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> FailureClusterSummaryResponse:
    """Update cluster investigation status and append an audit change entry."""
    valid_statuses = {"new", "investigating", "resolved", "ignored"}
    if payload.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{payload.status}'. Allowed: {sorted(valid_statuses)}",
        )

    cluster = await db.get(FailureCluster, cluster_id)
    if not cluster or (project_id and cluster.project_id != project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failure cluster not found.",
        )

    prev_status = cluster.status
    cluster.status = payload.status
    if payload.resolution_notes is not None:
        cluster.resolution_notes = payload.resolution_notes

    # Create audit record
    audit = ClusterStatusChange(
        cluster_id=cluster.id,
        previous_status=prev_status,
        new_status=payload.status,
        resolution_notes=payload.resolution_notes,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(cluster)

    return FailureClusterSummaryResponse.model_validate(cluster)


@router.post(
    "/failures/clusters/run",
    response_model=ClusteringJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Semantic Clustering Job",
)
async def trigger_clustering_job(
    payload: ClusteringJobRequest = ClusteringJobRequest(),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> ClusteringJobResponse:
    """Run incremental similarity-based clustering on embedded failure events."""
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID could not be determined.",
        )

    threshold = payload.similarity_threshold or settings.clustering_similarity_threshold
    min_size = payload.min_cluster_size or settings.clustering_min_cluster_size
    max_cand = payload.max_candidates or settings.clustering_max_candidates

    res = await run_clustering_for_project(
        db=db,
        project_id=project_id,
        threshold=threshold,
        min_cluster_size=min_size,
        max_candidates=max_cand,
    )

    return ClusteringJobResponse(
        status="completed",
        clusters_created=res["clusters_created"],
        clusters_updated=res["clusters_updated"],
        events_assigned=res["events_assigned"],
        events_unassigned=res["events_unassigned"],
        algorithm_version=settings.app_version,
    )


@router.post(
    "/failures/search",
    response_model=SimilarFailureSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search for Similar Failures",
)
async def search_similar_failures_endpoint(
    payload: SimilarFailureSearchRequest,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> SimilarFailureSearchResponse:
    """Find similar failures using pgvector semantic distance or lexical fallback."""
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID could not be determined.",
        )

    if not payload.query_text and not payload.event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either query_text or event_id must be provided.",
        )

    results, method = await search_similar_failures(
        db=db,
        project_id=project_id,
        query_text=payload.query_text,
        event_id=payload.event_id,
        threshold=payload.threshold,
        limit=payload.limit,
    )

    items = [
        SimilarFailureItem(
            event_id=r["event_id"],
            error_summary=r["error_summary"],
            failure_category=r["failure_category"],
            severity=r["severity"],
            agent_name=r["agent_name"],
            agent_version=r["agent_version"],
            model_name=r["model_name"],
            similarity_score=r["similarity_score"],
            cluster_id=r["cluster_id"],
            occurred_at=r["occurred_at"],
        )
        for r in results
    ]

    return SimilarFailureSearchResponse(
        results=items,
        total=len(items),
        search_method=method,
        threshold=payload.threshold,
    )


@router.post(
    "/failures/sync",
    response_model=FailureSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync Failure Events from Existing Sources",
)
async def sync_failures_endpoint(
    payload: FailureSyncRequest = FailureSyncRequest(),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> FailureSyncResponse:
    """Idempotently scan runs, spans, experiments, and safety benchmarks to extract failure events."""
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID could not be determined.",
        )

    res = await sync_failure_events(
        db=db,
        project_id=project_id,
        auto_embed=payload.auto_embed,
    )

    return FailureSyncResponse(
        scanned=res["scanned"],
        created=res["created"],
        skipped=res["skipped"],
        status="completed",
    )


@router.get(
    "/failures/{event_id}",
    response_model=FailureEventResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Failure Event Detail",
)
async def get_failure_event_detail(
    event_id: uuid.UUID,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> FailureEventResponse:
    """Get single failure event details with trace linkage and redaction."""
    event = await db.get(FailureEvent, event_id)
    if not event or (project_id and event.project_id != project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failure event not found.",
        )

    return FailureEventResponse.model_validate(event)
