"""
TraceHarbor API — Experiment Model
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
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
    from app.models.dataset import Dataset
    from app.models.experiment_result import ExperimentResult
    from app.models.project import Project


JSONType = JSON().with_variant(JSONB, "postgresql")


class Experiment(Base):
    """
    Experiment model recording the benchmark evaluation of an approved agent version
    against a specific dataset.
    """

    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )
    agent_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    agent_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
    )
    summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )
    total_cases: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    passed_cases: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    failed_cases: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    errored_cases: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="experiments",
    )
    dataset: Mapped["Dataset"] = relationship(
        "Dataset",
        back_populates="experiments",
    )
    results: Mapped[list["ExperimentResult"]] = relationship(
        "ExperimentResult",
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="ExperimentResult.created_at.asc()",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'error', 'cancelled')",
            name="check_experiment_status",
        ),
    )
