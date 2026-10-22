"""
TraceHarbor API — Run, Span & Analytics Response Schemas
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class SpanResponse(BaseModel):
    """Detailed trace span response."""

    id: uuid.UUID
    run_id: uuid.UUID
    parent_span_id: uuid.UUID | None = None
    name: str
    span_type: str
    status: str
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    model: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: Decimal = Decimal("0.000000")
    duration_ms: int | None = None
    started_at: datetime
    ended_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunSummaryResponse(BaseModel):
    """Summary of a run for list and dashboard views."""

    id: uuid.UUID
    project_id: uuid.UUID
    name: str | None = None
    status: str
    total_tokens: int = 0
    total_cost_usd: Decimal = Decimal("0.000000")
    duration_ms: int | None = None
    started_at: datetime
    ended_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunDetailResponse(RunSummaryResponse):
    """Full details of a run including input, output, error, and child spans."""

    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    spans: list[SpanResponse] = Field(default_factory=list)


class RunListResponse(BaseModel):
    """Paginated list of runs."""

    items: list[RunSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AnalyticsOverviewResponse(BaseModel):
    """Aggregated operational metrics for the overview dashboard."""

    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    error_rate: float = 0.0
    p50_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    cost_reported_runs: int = 0
    unmetered_runs: int = 0
    eval_pass_rate: float | None = None
    regression_count: int = 0
    time_range: str = "7d"
    recent_runs: list[RunSummaryResponse] = Field(default_factory=list)


class ProjectResponse(BaseModel):
    """Project metadata with total run counts."""

    id: uuid.UUID
    name: str
    description: str | None = None
    created_at: datetime
    runs_count: int = 0
