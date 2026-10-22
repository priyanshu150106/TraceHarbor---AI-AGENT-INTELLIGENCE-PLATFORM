"""003_analytics_and_alerts

Migration creating Phase 4 analytics, monitoring, and alerting tables & indexes:
- alert_rules: configurable alert rules per project (metric, threshold, window, channel, cooldown)
- alert_history: audit log of triggered alerts and delivery status
- performance composite indexes on runs and spans for analytical queries

Revision ID: 003_analytics_and_alerts
Revises: 002_evaluation_engine
Create Date: 2026-10-22 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003_analytics_and_alerts"
down_revision: str | None = "002_evaluation_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Table: alert_rules
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("metric", sa.String(length=50), nullable=False),
        sa.Column("operator", sa.String(length=10), server_default=">", nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("window_minutes", sa.Integer(), server_default="60", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("channel", sa.String(length=20), server_default="in_app", nullable=False),
        sa.Column("webhook_url", sa.Text(), nullable=True),
        sa.Column("webhook_secret", sa.String(length=255), nullable=True),
        sa.Column("cooldown_minutes", sa.Integer(), server_default="60", nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_rules_project_id", "alert_rules", ["project_id"])
    op.create_index("ix_alert_rules_project_active", "alert_rules", ["project_id", "is_active"])

    # 2. Table: alert_history
    op.create_table(
        "alert_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("metric", sa.String(length=50), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("operator", sa.String(length=10), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="triggered", nullable=False),
        sa.Column("notification_status", sa.String(length=20), server_default="delivered", nullable=False),
        sa.Column("notification_error", sa.Text(), nullable=True),
        sa.Column("acknowledged", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "fired_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["alert_rules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_history_project_id", "alert_history", ["project_id"])
    op.create_index("ix_alert_history_rule_id", "alert_history", ["rule_id"])
    op.create_index("ix_alert_history_project_fired", "alert_history", ["project_id", "fired_at"])

    # 3. Performance composite indexes for analytical time-series and model queries
    op.create_index("ix_runs_project_started", "runs", ["project_id", "started_at"])
    op.create_index("ix_spans_run_model", "spans", ["run_id", "model"])


def downgrade() -> None:
    op.drop_index("ix_spans_run_model", table_name="spans")
    op.drop_index("ix_runs_project_started", table_name="runs")
    op.drop_table("alert_history")
    op.drop_table("alert_rules")
