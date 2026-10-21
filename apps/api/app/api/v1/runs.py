"""
TraceHarbor API — Runs Read Endpoints
"""

import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import resolve_project_id
from app.core.database import get_db
from app.models.run import Run
from app.models.span import Span
from app.schemas.runs import RunDetailResponse, RunListResponse, RunSummaryResponse, SpanResponse

router = APIRouter(tags=["Runs"])


@router.get(
    "/runs",
    response_model=RunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Agent Runs",
    response_description="Paginated list of execution runs with filtering options",
)
async def list_runs(
    status_filter: str | None = Query(None, alias="status", description="Filter by run status (running, completed, error)"),
    search: str | None = Query(None, description="Search run by name"),
    from_date: datetime | None = Query(None, description="Start date (ISO 8601)"),
    to_date: datetime | None = Query(None, description="End date (ISO 8601)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> RunListResponse:
    """
    Retrieve a paginated, filterable list of agent execution runs.
    Enforces project isolation when an API key is provided.
    """
    if not project_id:
        return RunListResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)

    # Base query conditions
    conditions = [Run.project_id == project_id]
    if status_filter:
        conditions.append(Run.status == status_filter)
    if search:
        conditions.append(Run.name.ilike(f"%{search.strip()}%"))
    if from_date:
        conditions.append(Run.started_at >= from_date)
    if to_date:
        conditions.append(Run.started_at <= to_date)

    # Count total
    count_stmt = select(func.count(Run.id)).where(*conditions)
    count_res = await db.execute(count_stmt)
    total = count_res.scalar_one()

    # Query items
    stmt = (
        select(Run)
        .where(*conditions)
        .order_by(desc(Run.started_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    res = await db.execute(stmt)
    runs = res.scalars().all()

    items = [
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
        for r in runs
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return RunListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/runs/{run_id}",
    response_model=RunDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Run Details & Spans",
    response_description="Full execution trace including nested tool and LLM spans",
)
async def get_run_detail(
    run_id: uuid.UUID,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> RunDetailResponse:
    """
    Retrieve full execution details for a single run, including all child spans
    in chronological sequence for tree and waterfall reconstruction.
    """
    stmt = select(Run).where(Run.id == run_id)
    res = await db.execute(stmt)
    run_record = res.scalar_one_or_none()

    if not run_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )

    # Tenant isolation check
    if project_id and run_record.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Run belongs to a different project.",
        )

    # Fetch all spans for this run in chronological order
    spans_stmt = (
        select(Span)
        .where(Span.run_id == run_id)
        .order_by(Span.started_at.asc(), Span.created_at.asc())
    )
    spans_res = await db.execute(spans_stmt)
    spans_records = spans_res.scalars().all()

    span_items = [
        SpanResponse(
            id=s.id,
            run_id=s.run_id,
            parent_span_id=s.parent_span_id,
            name=s.name,
            span_type=s.span_type,
            status=s.status,
            input=s.input,
            output=s.output,
            error=s.error,
            model=s.model,
            prompt_tokens=s.prompt_tokens,
            completion_tokens=s.completion_tokens,
            total_tokens=s.total_tokens,
            cost_usd=s.cost_usd,
            duration_ms=s.duration_ms,
            started_at=s.started_at,
            ended_at=s.ended_at,
            metadata=s.span_metadata or {},
        )
        for s in spans_records
    ]

    return RunDetailResponse(
        id=run_record.id,
        project_id=run_record.project_id,
        name=run_record.name,
        status=run_record.status,
        input=run_record.input,
        output=run_record.output,
        error=run_record.error,
        total_tokens=run_record.total_tokens,
        total_cost_usd=run_record.total_cost_usd,
        duration_ms=run_record.duration_ms,
        started_at=run_record.started_at,
        ended_at=run_record.ended_at,
        tags=run_record.tags or [],
        metadata=run_record.run_metadata or {},
        spans=span_items,
    )
