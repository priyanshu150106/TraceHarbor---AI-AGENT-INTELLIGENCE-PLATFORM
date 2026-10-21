"""
TraceHarbor API — ExperimentResult Model
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.experiment import Experiment
    from app.models.run import Run
    from app.models.test_case import TestCase


JSONType = JSON().with_variant(JSONB, "postgresql")


class ExperimentResult(Base):
    """
    ExperimentResult model recording evaluation outcome for one test case within an experiment.
    Links to optional execution Run and detailed per-evaluator outcome metadata.
    """

    __tablename__ = "experiment_results"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actual_output: Mapped[dict[str, Any] | str | list[Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )
    scores: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
    )
    passed: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )  # pass, fail, error, pending
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    evaluation_details: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType,
        default=list,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    experiment: Mapped["Experiment"] = relationship(
        "Experiment",
        back_populates="results",
    )
    test_case: Mapped["TestCase"] = relationship(
        "TestCase",
        back_populates="results",
    )
    run: Mapped["Run | None"] = relationship(
        "Run",
    )

    __table_args__ = (
        UniqueConstraint("experiment_id", "test_case_id", name="uq_experiment_test_case"),
    )
