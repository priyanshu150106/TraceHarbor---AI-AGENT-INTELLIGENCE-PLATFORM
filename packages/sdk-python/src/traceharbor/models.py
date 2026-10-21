"""
TraceHarbor SDK — Internal Telemetry Data Models
"""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass
class RunData:
    """Represents a top-level agent execution run."""

    id: uuid.UUID
    name: str | None = None
    status: str = "running"
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    total_tokens: int = 0
    total_cost_usd: Decimal = field(default_factory=lambda: Decimal("0.000000"))
    duration_ms: int | None = None
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["id"] = str(self.id)
        d["started_at"] = self.started_at.isoformat()
        d["ended_at"] = self.ended_at.isoformat() if self.ended_at else None
        d["total_cost_usd"] = float(self.total_cost_usd)
        return d


@dataclass
class SpanData:
    """Represents an individual step or tool call within a run."""

    id: uuid.UUID
    run_id: uuid.UUID
    name: str
    span_type: str = "agent"
    parent_span_id: uuid.UUID | None = None
    status: str = "running"
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    model: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: Decimal = field(default_factory=lambda: Decimal("0.000000"))
    duration_ms: int | None = None
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["id"] = str(self.id)
        d["run_id"] = str(self.run_id)
        d["parent_span_id"] = str(self.parent_span_id) if self.parent_span_id else None
        d["started_at"] = self.started_at.isoformat()
        d["ended_at"] = self.ended_at.isoformat() if self.ended_at else None
        d["cost_usd"] = float(self.cost_usd)
        return d
