"""
TraceHarbor API — Analytics & Overview Endpoints
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import resolve_project_id
from app.core.database import get_db
from app.models.run import Run
from app.schemas.runs import AnalyticsOverviewResponse, RunSummaryResponse

router = APIRouter(tags=["Analytics"])


@router.get(
    "/analytics/overview",
    response_model=AnalyticsOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Overview Analytics",
    response_description="Aggregated run volume, error rate, latency percentiles, and token usage",
)
async def get_overview_analytics(
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsOverviewResponse:
    """
    Return high-level operational metrics and recent runs for the active project.
    Returns zeroed metrics gracefully when no runs have been ingested yet.
    """
    if not project_id:
        return AnalyticsOverviewResponse()

    # Query aggregate totals
    agg_stmt = select(
        func.count(Run.id).label("total_runs"),
        func.sum(Run.total_tokens).label("total_tokens"),
        func.sum(Run.total_cost_usd).label("total_cost"),
        func.avg(Run.duration_ms).label("avg_duration"),
    ).where(Run.project_id == project_id)
    agg_res = await db.execute(agg_stmt)
    agg_row = agg_res.one()

    total_runs = agg_row.total_runs or 0
    if total_runs == 0:
        return AnalyticsOverviewResponse()

    total_tokens = agg_row.total_tokens or 0
    total_cost_usd = float(agg_row.total_cost or 0.0)
    avg_duration_ms = float(agg_row.avg_duration or 0.0)

    # Success & Failure counts
    status_stmt = select(
        Run.status,
        func.count(Run.id),
    ).where(Run.project_id == project_id).group_by(Run.status)
    status_res = await db.execute(status_stmt)
    status_map = {row[0]: row[1] for row in status_res.all()}

    successful_runs = status_map.get("completed", 0)
    failed_runs = status_map.get("error", 0)
    error_rate = round(failed_runs / total_runs, 4) if total_runs > 0 else 0.0

    # Calculate p95 latency from durations of completed runs
    p95_stmt = (
        select(Run.duration_ms)
        .where(Run.project_id == project_id, Run.duration_ms.is_not(None))
        .order_by(Run.duration_ms.asc())
    )
    p95_res = await db.execute(p95_stmt)
    durations = [d for d in p95_res.scalars().all() if d is not None]

    p95_duration_ms = 0.0
    if durations:
        idx = int(len(durations) * 0.95)
        p95_duration_ms = float(durations[min(idx, len(durations) - 1)])

    # Recent 5 runs
    recent_stmt = (
        select(Run)
        .where(Run.project_id == project_id)
        .order_by(desc(Run.started_at))
        .limit(5)
    )
    recent_res = await db.execute(recent_stmt)
    recent_runs = [
        RunSummaryResponse(
            id=r.id,
            project_id=r.project_id,
            name=r.name,
            status=r.status,
            total_tokens=r.total_tokens,
            total_cost_usd=r.total_cost_usd,
            duration_ms=r.duration_ms,
            started_at=r.started_at,
            ended_at=r.ended_at,
            tags=r.tags or [],
            metadata=r.run_metadata or {},
        )
        for r in recent_res.scalars().all()
    ]

    return AnalyticsOverviewResponse(
        total_runs=total_runs,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        error_rate=error_rate,
        avg_duration_ms=round(avg_duration_ms, 2),
        p95_duration_ms=round(p95_duration_ms, 2),
        total_tokens=total_tokens,
        total_cost_usd=round(total_cost_usd, 6),
        recent_runs=recent_runs,
    )
