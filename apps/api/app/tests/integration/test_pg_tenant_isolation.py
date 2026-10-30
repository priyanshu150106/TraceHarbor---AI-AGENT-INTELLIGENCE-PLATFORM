"""
Phase C4 — Real PostgreSQL Tenant Isolation Integration Tests

Verifies that project-based tenant boundary isolation is strictly enforced
across multiple projects at the database layer in PostgreSQL.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import AlertRule
from app.models.dataset import Dataset
from app.models.failure import FailureCluster, FailureEvent
from app.models.project import Project
from app.models.run import Run
from app.models.span import Span
from app.models.user import User


@pytest.mark.integration
async def test_cross_tenant_isolation_in_postgres(pg_session: AsyncSession) -> None:
    """
    Create two completely separate tenants (Project A and Project B) with
    identical resource names and identical error payloads in PostgreSQL.
    Verify that tenant-scoped queries never leak data across projects.
    """
    user = User(
        id=uuid.uuid4(),
        email=f"multi_tenant_{uuid.uuid4().hex[:6]}@traceharbor.test",
        password_hash="$2b$12$hashgoeshere",
        display_name="Multi-tenant User",
    )
    pg_session.add(user)

    # Tenant A
    project_a = Project(id=uuid.uuid4(), user_id=user.id, name="Tenant Alpha")
    pg_session.add(project_a)

    # Tenant B
    project_b = Project(id=uuid.uuid4(), user_id=user.id, name="Tenant Beta")
    pg_session.add(project_b)
    await pg_session.flush()

    now = datetime.now(UTC)

    # Seed Tenant A resources
    run_a = Run(
        id=uuid.uuid4(),
        project_id=project_a.id,
        name="Production Agent",
        status="completed",
        started_at=now,
    )
    span_a = Span(
        id=uuid.uuid4(),
        run_id=run_a.id,
        name="execute_tool",
        span_type="tool",
        status="completed",
        started_at=now,
    )
    alert_a = AlertRule(
        id=uuid.uuid4(),
        project_id=project_a.id,
        name="Production Alert",
        metric="error_rate",
        operator=">",
        threshold=0.01,
        channel="webhook",
        webhook_url="https://tenant-a.com/webhook",
    )
    cluster_a = FailureCluster(
        id=uuid.uuid4(),
        project_id=project_a.id,
        title="Common Auth Error",
        first_seen_at=now,
        last_seen_at=now,
    )
    event_a = FailureEvent(
        id=uuid.uuid4(),
        project_id=project_a.id,
        source_type="run",
        source_id=str(uuid.uuid4()),
        error_summary="Unauthorized access token expired",
        normalized_text="unauthorized access token expired",
        occurred_at=now,
    )
    dataset_a = Dataset(
        id=uuid.uuid4(),
        project_id=project_a.id,
        name="Evaluation Golden Set",
    )
    pg_session.add_all([run_a, span_a, alert_a, cluster_a, event_a, dataset_a])

    # Seed Tenant B resources (with same resource names)
    run_b = Run(
        id=uuid.uuid4(),
        project_id=project_b.id,
        name="Production Agent",
        status="completed",
        started_at=now,
    )
    span_b = Span(
        id=uuid.uuid4(),
        run_id=run_b.id,
        name="execute_tool",
        span_type="tool",
        status="completed",
        started_at=now,
    )
    alert_b = AlertRule(
        id=uuid.uuid4(),
        project_id=project_b.id,
        name="Production Alert",
        metric="error_rate",
        operator=">",
        threshold=0.01,
        channel="webhook",
        webhook_url="https://tenant-b.com/webhook",
    )
    cluster_b = FailureCluster(
        id=uuid.uuid4(),
        project_id=project_b.id,
        title="Common Auth Error",
        first_seen_at=now,
        last_seen_at=now,
    )
    event_b = FailureEvent(
        id=uuid.uuid4(),
        project_id=project_b.id,
        source_type="run",
        source_id=str(uuid.uuid4()),
        error_summary="Unauthorized access token expired",
        normalized_text="unauthorized access token expired",
        occurred_at=now,
    )
    dataset_b = Dataset(
        id=uuid.uuid4(),
        project_id=project_b.id,
        name="Evaluation Golden Set",
    )
    pg_session.add_all([run_b, span_b, alert_b, cluster_b, event_b, dataset_b])
    await pg_session.commit()

    # Verify Project A queries only return Project A data
    runs_a = (await pg_session.scalars(select(Run).where(Run.project_id == project_a.id))).all()
    assert len(runs_a) == 1
    assert runs_a[0].id == run_a.id

    spans_a = (await pg_session.scalars(select(Span).join(Run).where(Run.project_id == project_a.id))).all()
    assert len(spans_a) == 1
    assert spans_a[0].id == span_a.id

    alerts_a = (await pg_session.scalars(select(AlertRule).where(AlertRule.project_id == project_a.id))).all()
    assert len(alerts_a) == 1
    assert alerts_a[0].webhook_url == "https://tenant-a.com/webhook"

    clusters_a = (await pg_session.scalars(select(FailureCluster).where(FailureCluster.project_id == project_a.id))).all()
    assert len(clusters_a) == 1
    assert clusters_a[0].id == cluster_a.id

    events_a = (await pg_session.scalars(select(FailureEvent).where(FailureEvent.project_id == project_a.id))).all()
    assert len(events_a) == 1
    assert events_a[0].id == event_a.id

    datasets_a = (await pg_session.scalars(select(Dataset).where(Dataset.project_id == project_a.id))).all()
    assert len(datasets_a) == 1
    assert datasets_a[0].id == dataset_a.id

    # Verify Project B queries only return Project B data
    runs_b = (await pg_session.scalars(select(Run).where(Run.project_id == project_b.id))).all()
    assert len(runs_b) == 1
    assert runs_b[0].id == run_b.id
