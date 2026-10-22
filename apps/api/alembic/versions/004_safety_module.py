"""004_safety_module

Migration creating Phase 5 AI safety and red-teaming tables & indexes:
- safety_campaigns: records safety campaigns against approved agents
- safety_test_results: records per-test adversarial evaluation results and redacted evidence
- adds dataset_type column to datasets table

Revision ID: 004_safety_module
Revises: 003_analytics_and_alerts
Create Date: 2026-10-22 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "004_safety_module"
down_revision: str | None = "003_analytics_and_alerts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(JSONB, "postgresql")


def upgrade() -> None:
    # 1. Add dataset_type column to datasets table
    op.add_column(
        "datasets",
        sa.Column(
            "dataset_type",
            sa.String(length=50),
            server_default="general",
            nullable=False,
        ),
    )

    # 2. Table: safety_campaigns
    op.create_table(
        "safety_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("agent_version", sa.String(length=50), nullable=False),
        sa.Column("config", json_type, server_default="{}", nullable=False),
        sa.Column("summary", json_type, nullable=True),
        sa.Column("total_tests", sa.Integer(), server_default="0", nullable=False),
        sa.Column("passed_tests", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_tests", sa.Integer(), server_default="0", nullable=False),
        sa.Column("errored_tests", sa.Integer(), server_default="0", nullable=False),
        sa.Column("critical_failures", sa.Integer(), server_default="0", nullable=False),
        sa.Column("safety_pass_rate", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("category_scores", json_type, server_default="{}", nullable=False),
        sa.Column("severity_summary", json_type, server_default="{}", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("total_tests >= 0", name="chk_safety_total_tests_nonneg"),
        sa.CheckConstraint("passed_tests >= 0", name="chk_safety_passed_tests_nonneg"),
        sa.CheckConstraint("failed_tests >= 0", name="chk_safety_failed_tests_nonneg"),
        sa.CheckConstraint("critical_failures >= 0", name="chk_safety_critical_nonneg"),
    )
    op.create_index("ix_safety_campaigns_project_id", "safety_campaigns", ["project_id"])
    op.create_index("ix_safety_campaigns_dataset_id", "safety_campaigns", ["dataset_id"])
    op.create_index("ix_safety_campaigns_status", "safety_campaigns", ["status"])

    # 3. Table: safety_test_results
    op.create_table(
        "safety_test_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("test_case_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("stable_case_id", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("adversarial_input", json_type, nullable=True),
        sa.Column("agent_output", json_type, nullable=True),
        sa.Column("expected_safe_behavior", sa.Text(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("evaluator_results", json_type, server_default="[]", nullable=False),
        sa.Column("evidence", json_type, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["campaign_id"], ["safety_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_safety_test_results_campaign_id", "safety_test_results", ["campaign_id"])
    op.create_index("ix_safety_test_results_test_case_id", "safety_test_results", ["test_case_id"])
    op.create_index("ix_safety_test_results_stable_case_id", "safety_test_results", ["stable_case_id"])
    op.create_index("ix_safety_test_results_category", "safety_test_results", ["category"])
    op.create_index("ix_safety_test_results_severity", "safety_test_results", ["severity"])


def downgrade() -> None:
    op.drop_table("safety_test_results")
    op.drop_table("safety_campaigns")
    op.drop_column("datasets", "dataset_type")
