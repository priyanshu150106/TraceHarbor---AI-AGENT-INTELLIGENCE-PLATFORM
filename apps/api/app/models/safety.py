"""
TraceHarbor API — Safety Campaign and Safety Test Result Models

Stores safety red-teaming benchmarks, attack category evaluations,
and per-test outcomes with redacted evidence for AI agents.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
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
    from app.models.project import Project
    from app.models.run import Run
    from app.models.test_case import TestCase

JSONType = JSON().with_variant(JSONB, "postgresql")


class SafetyCampaign(Base):
    """
    SafetyCampaign model recording adversarial red-teaming evaluations
    of an approved agent against a curated safety dataset.
    """

    __tablename__ = "safety_campaigns"

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
    )  # pending, running, completed, error
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
    total_tests: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    passed_tests: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    failed_tests: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    errored_tests: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    critical_failures: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    safety_pass_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    category_scores: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
    )
    severity_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="safety_campaigns",
    )
    dataset: Mapped["Dataset"] = relationship(
        "Dataset",
        back_populates="safety_campaigns",
    )
    results: Mapped[list["SafetyTestResult"]] = relationship(
        "SafetyTestResult",
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="SafetyTestResult.created_at.asc()",
    )

    __table_args__ = (
        CheckConstraint("total_tests >= 0", name="chk_safety_total_tests_nonneg"),
        CheckConstraint("passed_tests >= 0", name="chk_safety_passed_tests_nonneg"),
        CheckConstraint("failed_tests >= 0", name="chk_safety_failed_tests_nonneg"),
        CheckConstraint("critical_failures >= 0", name="chk_safety_critical_nonneg"),
    )


class SafetyTestResult(Base):
    """
    SafetyTestResult model recording the outcome of a single adversarial test case
    within a SafetyCampaign, including evaluated attack category, severity,
    structured evaluator explanations, and sanitized/redacted evidence.
    """

    __tablename__ = "safety_test_results"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("safety_campaigns.id", ondelete="CASCADE"),
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
    stable_case_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # prompt_injection, instruction_hierarchy, sensitive_data, unsafe_tool_use, etc.
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )  # critical, high, medium, low
    adversarial_input: Mapped[dict[str, Any] | str | list[Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )
    agent_output: Mapped[dict[str, Any] | str | list[Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )
    expected_safe_behavior: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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
    evaluator_results: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType,
        default=list,
        nullable=False,
    )
    evidence: Mapped[dict[str, Any] | list[Any] | str | None] = mapped_column(
        JSONType,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    campaign: Mapped["SafetyCampaign"] = relationship(
        "SafetyCampaign",
        back_populates="results",
    )
    test_case: Mapped["TestCase"] = relationship(
        "TestCase",
    )
    run: Mapped["Run | None"] = relationship(
        "Run",
    )
