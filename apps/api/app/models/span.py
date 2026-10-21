"""
TraceHarbor API — Span Model
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.run import Run


JSONType = JSON().with_variant(JSONB, "postgresql")


class Span(Base):
    """
    Span model representing one step inside a run (LLM call, tool call, retrieval, etc.).
    Supports recursive nesting through parent_span_id.
    """

    __tablename__ = "spans"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_span_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("spans.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    span_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    input: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )
    output: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="running",
        nullable=False,
    )
    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        default=Decimal("0.000000"),
        nullable=False,
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    span_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONType,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    run: Mapped["Run"] = relationship(
        "Run",
        back_populates="spans",
    )
    parent_span: Mapped[Optional["Span"]] = relationship(
        "Span",
        remote_side=[id],
        back_populates="child_spans",
    )
    child_spans: Mapped[list["Span"]] = relationship(
        "Span",
        back_populates="parent_span",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "span_type IN ('llm', 'tool', 'retrieval', 'chain', 'agent', 'custom')",
            name="check_span_type",
        ),
        CheckConstraint(
            "status IN ('running', 'completed', 'error')",
            name="check_span_status",
        ),
        Index("ix_spans_run_id", "run_id"),
        Index("ix_spans_parent_span_id", "parent_span_id"),
    )
