"""
TraceHarbor API — Alert Rule and Alert History Models
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


class AlertRule(Base):
    """
    Configurable alert condition for monitoring project metrics.
    Triggers alerts and notifications when metrics breach defined thresholds.
    """

    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    metric: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # e.g., 'error_rate', 'p95_latency', 'cost_usd', 'eval_pass_rate', 'regression_count'
    operator: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=">",
    )  # '>', '>=', '<', '<=', '=='
    threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    window_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
    )  # Look-back window in minutes (e.g. 15, 60, 360, 1440)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="in_app",
    )  # 'in_app', 'webhook'
    webhook_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    webhook_secret: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    cooldown_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
    )
    last_triggered_at: Mapped[datetime | None] = mapped_column(
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
        back_populates="alert_rules",
    )
    history: Mapped[list["AlertHistory"]] = relationship(
        "AlertHistory",
        back_populates="rule",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_alert_rules_project_id", "project_id"),
        Index("ix_alert_rules_project_active", "project_id", "is_active"),
    )


class AlertHistory(Base):
    """
    Fired alert record capturing metric state at trigger time,
    human-readable explanation, and notification delivery status.
    """

    __tablename__ = "alert_history"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("alert_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    metric_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    operator: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="triggered",
    )  # 'triggered', 'resolved', 'acknowledged'
    notification_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="delivered",
    )  # 'delivered', 'failed', 'skipped'
    notification_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    acknowledged: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    rule: Mapped["AlertRule"] = relationship(
        "AlertRule",
        back_populates="history",
    )
    project: Mapped["Project"] = relationship(
        "Project",
    )

    __table_args__ = (
        Index("ix_alert_history_project_id", "project_id"),
        Index("ix_alert_history_rule_id", "rule_id"),
        Index("ix_alert_history_project_fired", "project_id", "fired_at"),
    )
