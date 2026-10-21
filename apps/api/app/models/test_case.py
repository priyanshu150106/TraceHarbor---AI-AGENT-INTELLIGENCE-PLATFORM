"""
TraceHarbor API — TestCase Model
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.experiment_result import ExperimentResult


JSONType = JSON().with_variant(JSONB, "postgresql")


class TestCase(Base):
    """
    TestCase model representing an individual test prompt/query, optional expected output,
    and evaluation criteria within a dataset.
    """

    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input: Mapped[dict[str, Any] | str | list[Any]] = mapped_column(
        JSONType,
        nullable=False,
    )
    expected_output: Mapped[dict[str, Any] | str | list[Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )
    criteria: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )
    # Named test_metadata in Python to avoid conflict with Base.metadata, mapped to 'metadata'
    test_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONType,
        default=dict,
        nullable=False,
    )
    tags: Mapped[list[str]] = mapped_column(
        JSONType,
        default=list,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    dataset: Mapped["Dataset"] = relationship(
        "Dataset",
        back_populates="test_cases",
    )
    results: Mapped[list["ExperimentResult"]] = relationship(
        "ExperimentResult",
        back_populates="test_case",
        cascade="all, delete-orphan",
    )
