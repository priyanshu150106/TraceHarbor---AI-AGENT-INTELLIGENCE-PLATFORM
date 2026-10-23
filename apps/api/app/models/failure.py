"""
TraceHarbor API — Failure Intelligence Models

Phase 6: Normalized failure events, semantic clusters, cluster membership,
and investigation status audit trail.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
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
    from app.models.project import Project

# Universal JSON type: JSONB on PostgreSQL, standard JSON on SQLite
JSONType = JSON().with_variant(JSONB, "postgresql")


class FailureEvent(Base):
    """
    Normalized failure event extracted from runs, spans, experiment results,
    safety test results, or other sources. Each failure is deduplicated by
    (source_type, source_id) to prevent duplicate processing.
    """

    __tablename__ = "failure_events"

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

    # Source linkage for idempotent ingestion
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # 'run', 'span', 'experiment_result', 'safety_test_result'
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
    )

    # Trace context (nullable — not all sources have run/trace)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        nullable=True,
        index=True,
    )
    trace_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Agent / model metadata
    agent_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    agent_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    model_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    model_provider: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Failure classification
    failure_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unknown",
    )  # 'runtime_error', 'eval_failure', 'safety_failure', 'tool_error', 'timeout', 'unknown'
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
    )  # 'critical', 'high', 'medium', 'low'

    # Sanitized content for display and analysis
    error_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    normalized_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )  # Redacted, normalized for embedding

    # Embedding status
    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )  # SHA-256 of normalized_text for dedup
    embedding_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )  # 'pending', 'completed', 'failed', 'skipped'
    embedding_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    embedding_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(64),
        nullable=True,
    )

    # Cluster assignment
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("failure_clusters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Extra structured metadata (source-specific details)
    failure_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONType,
        default=dict,
        nullable=False,
    )

    # Timestamps
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    cluster: Mapped["FailureCluster | None"] = relationship(
        "FailureCluster",
        back_populates="members",
        foreign_keys=[cluster_id],
    )

    __table_args__ = (
        UniqueConstraint("source_type", "source_id", name="uq_failure_source"),
        CheckConstraint(
            "source_type IN ('run', 'span', 'experiment_result', 'safety_test_result')",
            name="chk_failure_source_type",
        ),
        CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low')",
            name="chk_failure_severity",
        ),
        CheckConstraint(
            "embedding_status IN ('pending', 'completed', 'failed', 'skipped')",
            name="chk_failure_embedding_status",
        ),
        Index("ix_failure_events_project_occurred", "project_id", "occurred_at"),
        Index("ix_failure_events_category", "failure_category"),
        Index("ix_failure_events_severity", "severity"),
        Index("ix_failure_events_source", "source_type", "source_id"),
    )


class FailureCluster(Base):
    """
    Persistent cluster of semantically similar failure events.
    Tracks investigation status, resolution, and temporal trends.
    """

    __tablename__ = "failure_clusters"

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

    # Human-readable title derived from failure summaries
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Classification
    dominant_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unknown",
    )
    severity_distribution: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
    )  # {"critical": 2, "high": 5, "medium": 10, "low": 1}

    # Counts
    event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Temporal
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Representative example (sanitized error summary from a representative event)
    representative_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Affected agent versions and models (JSON arrays)
    affected_agents: Mapped[list[str]] = mapped_column(
        JSONType,
        default=list,
        nullable=False,
    )
    affected_models: Mapped[list[str]] = mapped_column(
        JSONType,
        default=list,
        nullable=False,
    )

    # Representative run/trace links (list of {"run_id": ..., "trace_id": ...})
    representative_traces: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType,
        default=list,
        nullable=False,
    )

    # Investigation status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="new",
    )  # 'new', 'investigating', 'resolved', 'ignored'
    resolution_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Clustering metadata
    algorithm_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="threshold_v1",
    )
    similarity_threshold: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    centroid_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(64),
        nullable=True,
    )

    # Timestamps
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
    project: Mapped["Project"] = relationship("Project")
    members: Mapped[list["FailureEvent"]] = relationship(
        "FailureEvent",
        back_populates="cluster",
        foreign_keys=[FailureEvent.cluster_id],
    )
    status_changes: Mapped[list["ClusterStatusChange"]] = relationship(
        "ClusterStatusChange",
        back_populates="cluster",
        cascade="all, delete-orphan",
        order_by="ClusterStatusChange.changed_at.asc()",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'investigating', 'resolved', 'ignored')",
            name="chk_cluster_status",
        ),
        CheckConstraint("event_count >= 0", name="chk_cluster_event_count_nonneg"),
        Index("ix_failure_clusters_project_status", "project_id", "status"),
        Index("ix_failure_clusters_project_last_seen", "project_id", "last_seen_at"),
    )


class ClusterStatusChange(Base):
    """
    Audit trail for cluster investigation status transitions.
    """

    __tablename__ = "cluster_status_changes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("failure_clusters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    new_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    resolution_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    cluster: Mapped["FailureCluster"] = relationship(
        "FailureCluster",
        back_populates="status_changes",
    )
