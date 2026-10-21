"""
TraceHarbor API — Trace Ingestion Schemas
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class RunIngestSchema(BaseModel):
    """Schema for ingesting or updating an agent execution run."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str | None = Field(default=None, max_length=255)
    status: Literal["running", "completed", "error"] = "running"
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    total_tokens: int = Field(default=0, ge=0)
    total_cost_usd: Decimal = Field(default=Decimal("0.000000"), ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    started_at: datetime
    ended_at: datetime | None = None


class SpanIngestSchema(BaseModel):
    """Schema for ingesting a single trace span within a run."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    run_id: uuid.UUID
    parent_span_id: uuid.UUID | None = None
    name: str = Field(..., min_length=1, max_length=255)
    span_type: Literal["llm", "tool", "retrieval", "chain", "agent", "custom"]
    status: Literal["running", "completed", "error"] = "running"
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    model: str | None = Field(default=None, max_length=100)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    cost_usd: Decimal = Field(default=Decimal("0.000000"), ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    started_at: datetime
    ended_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestBatchRequest(BaseModel):
    """
    Flexible batch ingestion payload.
    Supports either {"runs": [...], "spans": [...]} or a list of spans.
    """

    runs: list[RunIngestSchema] = Field(default_factory=list)
    spans: list[SpanIngestSchema] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def validate_flexible_format(cls, data: Any) -> Any:
        if isinstance(data, list):
            # If a top-level list of spans is submitted
            return {"spans": data, "runs": []}
        return data


class IngestResponse(BaseModel):
    """Response returned upon successful batch ingestion."""

    status: str = "accepted"
    accepted_runs: int
    accepted_spans: int
    project_id: uuid.UUID
    run_ids: list[uuid.UUID] = Field(default_factory=list)
    span_ids: list[uuid.UUID] = Field(default_factory=list)
