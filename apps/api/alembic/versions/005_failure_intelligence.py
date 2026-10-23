"""005_failure_intelligence

Migration creating Phase 6 Failure Intelligence tables, pgvector extension, and indexes:
- failure_clusters: persistent clusters of semantically similar failure events
- failure_events: normalized failure events extracted from runs, spans, experiments, and safety benchmarks
- cluster_status_changes: audit log of cluster status transitions and resolution notes

Revision ID: 005_failure_intelligence
Revises: 004_safety_module
Create Date: 2026-10-23 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "005_failure_intelligence"
down_revision: str | None = "004_safety_module"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(JSONB, "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Enable pgvector extension on PostgreSQL
    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Vector type helper
    try:
        from pgvector.sqlalchemy import Vector
        vector_col_type = Vector(64)
    except ImportError:
        vector_col_type = sa.NullType()

    # 2. Table: failure_clusters
    op.create_table(
        "failure_clusters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("dominant_category", sa.String(length=50), server_default="unknown", nullable=False),
        sa.Column("severity_distribution", json_type, server_default="{}", nullable=False),
        sa.Column("event_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("representative_summary", sa.Text(), nullable=True),
        sa.Column("affected_agents", json_type, server_default="[]", nullable=False),
        sa.Column("affected_models", json_type, server_default="[]", nullable=False),
        sa.Column("representative_traces", json_type, server_default="[]", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="new", nullable=False),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("algorithm_version", sa.String(length=50), server_default="threshold_v1", nullable=False),
        sa.Column("similarity_threshold", sa.Float(), nullable=True),
        sa.Column("centroid_embedding", vector_col_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('new', 'investigating', 'resolved', 'ignored')", name="chk_cluster_status"),
        sa.CheckConstraint("event_count >= 0", name="chk_cluster_event_count_nonneg"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_failure_clusters_project_id", "failure_clusters", ["project_id"])
    op.create_index("ix_failure_clusters_project_status", "failure_clusters", ["project_id", "status"])
    op.create_index("ix_failure_clusters_project_last_seen", "failure_clusters", ["project_id", "last_seen_at"])

    # 3. Table: failure_events
    op.create_table(
        "failure_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("trace_id", sa.String(length=255), nullable=True),
        sa.Column("agent_name", sa.String(length=255), nullable=True),
        sa.Column("agent_version", sa.String(length=100), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("model_provider", sa.String(length=100), nullable=True),
        sa.Column("failure_category", sa.String(length=50), server_default="unknown", nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("embedding_status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("embedding_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("embedding_error", sa.Text(), nullable=True),
        sa.Column("embedding", vector_col_type, nullable=True),
        sa.Column("cluster_id", sa.Uuid(), nullable=True),
        sa.Column("metadata", json_type, server_default="{}", nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('run', 'span', 'experiment_result', 'safety_test_result')",
            name="chk_failure_source_type",
        ),
        sa.CheckConstraint("severity IN ('critical', 'high', 'medium', 'low')", name="chk_failure_severity"),
        sa.CheckConstraint(
            "embedding_status IN ('pending', 'completed', 'failed', 'skipped')",
            name="chk_failure_embedding_status",
        ),
        sa.ForeignKeyConstraint(["cluster_id"], ["failure_clusters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_type", "source_id", name="uq_failure_source"),
    )
    op.create_index("ix_failure_events_project_id", "failure_events", ["project_id"])
    op.create_index("ix_failure_events_run_id", "failure_events", ["run_id"])
    op.create_index("ix_failure_events_content_hash", "failure_events", ["content_hash"])
    op.create_index("ix_failure_events_cluster_id", "failure_events", ["cluster_id"])
    op.create_index("ix_failure_events_project_occurred", "failure_events", ["project_id", "occurred_at"])
    op.create_index("ix_failure_events_category", "failure_events", ["failure_category"])
    op.create_index("ix_failure_events_severity", "failure_events", ["severity"])
    op.create_index("ix_failure_events_source", "failure_events", ["source_type", "source_id"])

    # 4. Table: cluster_status_changes
    op.create_table(
        "cluster_status_changes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=False),
        sa.Column("new_status", sa.String(length=20), nullable=False),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["cluster_id"], ["failure_clusters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cluster_status_changes_cluster_id", "cluster_status_changes", ["cluster_id"])


def downgrade() -> None:
    op.drop_table("cluster_status_changes")
    op.drop_table("failure_events")
    op.drop_table("failure_clusters")
