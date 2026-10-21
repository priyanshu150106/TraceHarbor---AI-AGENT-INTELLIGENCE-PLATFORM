"""
TraceHarbor API — Trace Ingestion Router & Controller
"""

import time
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_authenticated_api_key
from app.core.database import get_db
from app.models.api_key import ApiKey
from app.models.run import Run
from app.models.span import Span
from app.schemas.ingest import IngestBatchRequest, IngestResponse, SpanIngestSchema

logger = structlog.get_logger("traceharbor.ingest")

router = APIRouter(tags=["Trace Ingestion"])

# Configurable batch limits
MAX_BATCH_SIZE = 500


def _sort_spans_topologically(spans: list[SpanIngestSchema]) -> list[SpanIngestSchema]:
    """
    Sort spans so that parent spans appear before child spans in persistence order.
    Detects circular parent-child references.
    """
    span_map = {s.id: s for s in spans}
    visited: set[uuid.UUID] = set()
    visiting: set[uuid.UUID] = set()
    ordered: list[SpanIngestSchema] = []

    def visit(span_id: uuid.UUID) -> None:
        if span_id in visiting:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Circular parent-child reference detected involving span ID {span_id}",
            )
        if span_id not in visited:
            visiting.add(span_id)
            span = span_map[span_id]
            if span.parent_span_id and span.parent_span_id in span_map:
                visit(span.parent_span_id)
            visiting.remove(span_id)
            visited.add(span_id)
            ordered.append(span)

    for s in spans:
        if s.id not in visited:
            visit(s.id)

    return ordered


@router.post(
    "/spans",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest Trace Spans & Runs",
    response_description="Returns count and identifiers of accepted runs and spans",
)
async def ingest_spans(
    payload: IngestBatchRequest,
    auth_key: ApiKey = Depends(get_authenticated_api_key),
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """
    Ingest a batch of runs and spans emitted by the TraceHarbor SDK.
    Validates payload integrity, checks parent-child span hierarchy,
    enforces project tenant isolation, and writes atomically.
    """
    start_time = time.perf_counter()
    project_id = auth_key.project_id
    total_items = len(payload.runs) + len(payload.spans)

    if total_items == 0:
        return IngestResponse(
            status="accepted",
            accepted_runs=0,
            accepted_spans=0,
            project_id=project_id,
            run_ids=[],
            span_ids=[],
        )

    # 1. Enforce batch size limit
    if total_items > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size of {total_items} exceeds maximum limit of {MAX_BATCH_SIZE} items.",
        )

    # 2. Self-parenting check
    for span in payload.spans:
        if span.parent_span_id is not None and span.parent_span_id == span.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Span '{span.name}' ({span.id}) cannot reference itself as parent.",
            )

    # 3. Topological sorting & Cycle detection for batch spans
    ordered_spans = _sort_spans_topologically(payload.spans)

    # 4. Check external parent spans (parents not in this batch must exist in the database)
    batch_span_ids = {s.id for s in payload.spans}
    external_parent_ids = {
        s.parent_span_id
        for s in payload.spans
        if s.parent_span_id is not None and s.parent_span_id not in batch_span_ids
    }

    if external_parent_ids:
        existing_parents_stmt = select(Span.id, Span.run_id).where(
            Span.id.in_(external_parent_ids)
        )
        existing_parents_res = await db.execute(existing_parents_stmt)
        existing_parents_map = {row[0]: row[1] for row in existing_parents_res.all()}

        for pid in external_parent_ids:
            if pid not in existing_parents_map:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Referenced parent span '{pid}' does not exist.",
                )

    # 5. Project isolation check for runs
    referenced_run_ids = {r.id for r in payload.runs} | {s.run_id for s in payload.spans}
    existing_runs_stmt = select(Run).where(Run.id.in_(referenced_run_ids))
    existing_runs_res = await db.execute(existing_runs_stmt)
    existing_runs = {r.id: r for r in existing_runs_res.scalars().all()}

    for rid, existing_run in existing_runs.items():
        if existing_run.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Run '{rid}' belongs to a different project.",
            )

    try:
        accepted_run_ids: list[uuid.UUID] = []
        accepted_span_ids: list[uuid.UUID] = []

        # 6. Process Runs
        runs_in_payload = {r.id: r for r in payload.runs}

        # Auto-create missing Run records referenced by spans but not in runs list
        for span in payload.spans:
            if span.run_id not in existing_runs and span.run_id not in runs_in_payload:
                new_run = Run(
                    id=span.run_id,
                    project_id=project_id,
                    name=f"Run-{str(span.run_id)[:8]}",
                    status="running",
                    started_at=span.started_at,
                )
                db.add(new_run)
                existing_runs[span.run_id] = new_run
                accepted_run_ids.append(span.run_id)

        # Upsert explicit runs
        for run_in in payload.runs:
            if run_in.id in existing_runs:
                # Update existing run
                r = existing_runs[run_in.id]
                if run_in.name:
                    r.name = run_in.name
                r.status = run_in.status
                if run_in.input is not None:
                    r.input = run_in.input
                if run_in.output is not None:
                    r.output = run_in.output
                if run_in.error is not None:
                    r.error = run_in.error
                if run_in.tags:
                    r.tags = run_in.tags
                if run_in.metadata:
                    r.run_metadata = run_in.metadata
                if run_in.total_tokens:
                    r.total_tokens = run_in.total_tokens
                if run_in.total_cost_usd:
                    r.total_cost_usd = run_in.total_cost_usd
                if run_in.duration_ms is not None:
                    r.duration_ms = run_in.duration_ms
                if run_in.ended_at:
                    r.ended_at = run_in.ended_at
            else:
                # Create new run
                new_run = Run(
                    id=run_in.id,
                    project_id=project_id,
                    name=run_in.name,
                    status=run_in.status,
                    input=run_in.input,
                    output=run_in.output,
                    error=run_in.error,
                    tags=run_in.tags,
                    run_metadata=run_in.metadata,
                    total_tokens=run_in.total_tokens,
                    total_cost_usd=run_in.total_cost_usd,
                    duration_ms=run_in.duration_ms,
                    started_at=run_in.started_at,
                    ended_at=run_in.ended_at,
                )
                db.add(new_run)
                existing_runs[run_in.id] = new_run

            accepted_run_ids.append(run_in.id)

        # Flush runs before persisting spans so foreign key constraints hold
        await db.flush()

        # 7. Process Spans (in topological order)
        existing_spans_stmt = select(Span).where(
            Span.id.in_([s.id for s in ordered_spans])
        )
        existing_spans_res = await db.execute(existing_spans_stmt)
        existing_spans = {s.id: s for s in existing_spans_res.scalars().all()}

        for s_in in ordered_spans:
            if s_in.id in existing_spans:
                # Update existing span
                s = existing_spans[s_in.id]
                s.status = s_in.status
                if s_in.output is not None:
                    s.output = s_in.output
                if s_in.error is not None:
                    s.error = s_in.error
                if s_in.model is not None:
                    s.model = s_in.model
                if s_in.prompt_tokens:
                    s.prompt_tokens = s_in.prompt_tokens
                if s_in.completion_tokens:
                    s.completion_tokens = s_in.completion_tokens
                if s_in.total_tokens:
                    s.total_tokens = s_in.total_tokens
                if s_in.cost_usd:
                    s.cost_usd = s_in.cost_usd
                if s_in.duration_ms is not None:
                    s.duration_ms = s_in.duration_ms
                if s_in.ended_at:
                    s.ended_at = s_in.ended_at
                if s_in.metadata:
                    s.span_metadata = s_in.metadata
            else:
                # Insert new span
                new_span = Span(
                    id=s_in.id,
                    run_id=s_in.run_id,
                    parent_span_id=s_in.parent_span_id,
                    name=s_in.name,
                    span_type=s_in.span_type,
                    status=s_in.status,
                    input=s_in.input,
                    output=s_in.output,
                    error=s_in.error,
                    model=s_in.model,
                    prompt_tokens=s_in.prompt_tokens,
                    completion_tokens=s_in.completion_tokens,
                    total_tokens=s_in.total_tokens,
                    cost_usd=s_in.cost_usd,
                    duration_ms=s_in.duration_ms,
                    started_at=s_in.started_at,
                    ended_at=s_in.ended_at,
                    span_metadata=s_in.metadata,
                )
                db.add(new_span)
                # Flush incrementally so any child spans in this batch see their parent
                await db.flush()

            accepted_span_ids.append(s_in.id)

        # Commit entire batch transaction
        await db.commit()

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            "trace_batch_ingested",
            project_id=str(project_id),
            runs_count=len(accepted_run_ids),
            spans_count=len(accepted_span_ids),
            elapsed_ms=elapsed_ms,
        )

        return IngestResponse(
            status="accepted",
            accepted_runs=len(accepted_run_ids),
            accepted_spans=len(accepted_span_ids),
            project_id=project_id,
            run_ids=accepted_run_ids,
            span_ids=accepted_span_ids,
        )

    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        logger.error(
            "trace_batch_ingest_failed",
            project_id=str(project_id),
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist trace batch: {type(exc).__name__}",
        ) from exc
