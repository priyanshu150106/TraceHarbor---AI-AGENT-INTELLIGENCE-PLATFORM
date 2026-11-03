"""
TraceHarbor API — Demo Seeder Safety and Tenant Isolation Tests

Validates:
1. Safe seeding into a clean database.
2. Idempotent re-seeding without --reset (no duplicate records).
3. Clean re-seeding with --reset (clean purge and reseed).
4. Failure during seeding triggers a clean rollback (no half-seeded state).
5. Strict tenant isolation: non-demo tenant data is never deleted, modified, or cross-contaminated.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset
from app.models.project import Project
from app.models.run import Run
from app.models.user import User
from scripts.seed_demo_data import (
    DEMO_PROJECT_ID,
    DEMO_USER_ID,
    purge_demo_tenant,
    seed_demo_data,
    verify_demo_tenant,
)


@pytest.mark.asyncio
async def test_seeder_safe_initial_seed(db_session: AsyncSession) -> None:
    """Safe seeding into database creates all synthetic demo entities correctly."""
    # Ensure any previous demo records are cleaned up in this session
    await purge_demo_tenant(db_session)
    await db_session.commit()

    counts = await seed_demo_data(db_session, reset=False)

    assert counts["runs"] >= 2
    assert counts["spans"] >= 5
    assert counts["datasets"] >= 2
    assert counts["test_cases"] >= 2
    assert counts["experiments"] >= 1
    assert counts["safety_campaigns"] >= 1
    assert counts["failure_clusters"] >= 1
    assert counts["alert_rules"] >= 1

    # Verify project exists and matches DEMO_PROJECT_ID
    proj = await db_session.get(Project, DEMO_PROJECT_ID)
    assert proj is not None
    assert proj.id == DEMO_PROJECT_ID
    assert proj.user_id == DEMO_USER_ID


@pytest.mark.asyncio
async def test_seeder_idempotent_reseed_without_reset(db_session: AsyncSession) -> None:
    """Re-running seeder without --reset must be idempotent and create zero duplicate records."""
    # First seed
    counts_first = await seed_demo_data(db_session, reset=False)

    # Second seed without reset
    counts_second = await seed_demo_data(db_session, reset=False)

    assert counts_first == counts_second

    # Verify run count did not double
    total_demo_runs = await db_session.scalar(
        select(func.count(Run.id)).where(Run.project_id == DEMO_PROJECT_ID)
    )
    assert total_demo_runs == counts_first["runs"]


@pytest.mark.asyncio
async def test_seeder_clean_reseed_with_reset(db_session: AsyncSession) -> None:
    """Re-seeding with --reset purges existing demo records and re-creates them cleanly without conflict."""
    # Ensure initial seed exists
    await seed_demo_data(db_session, reset=False)

    # Re-seed with reset
    counts_reset = await seed_demo_data(db_session, reset=True)
    assert counts_reset["runs"] >= 2
    assert counts_reset["experiments"] >= 1

    proj = await db_session.get(Project, DEMO_PROJECT_ID)
    assert proj is not None


@pytest.mark.asyncio
async def test_seeder_failure_rollback(db_session: AsyncSession) -> None:
    """A database error midway through seeding triggers an atomic rollback leaving state clean."""
    # Purge any existing demo tenant first
    await purge_demo_tenant(db_session)
    await db_session.commit()

    # Simulate an error while adding failure events
    with patch("scripts.seed_demo_data.FailureEvent", side_effect=RuntimeError("Simulated DB Crash")):
        with pytest.raises(RuntimeError, match="Simulated DB Crash"):
            await seed_demo_data(db_session, reset=True)

    # Verify rollback: no half-seeded demo project should exist after rollback
    proj = await db_session.get(Project, DEMO_PROJECT_ID)
    assert proj is None, "Failed seed must rollback completely; no demo project should persist"


@pytest.mark.asyncio
async def test_seeder_non_demo_tenant_isolation(db_session: AsyncSession) -> None:
    """
    Non-demo tenant records must be 100% isolated and never touched, deleted,
    or altered before, during, or after running the demo seeder with --reset.
    """
    # 1. Create a customer (non-demo) user, project, run, and dataset
    customer_user_id = uuid.uuid4()
    customer_proj_id = uuid.uuid4()
    customer_run_id = uuid.uuid4()

    customer_user = User(
        id=customer_user_id,
        email="customer@enterprise.acme",
        password_hash="secret_customer_hash",
        display_name="Enterprise Customer",
    )
    db_session.add(customer_user)

    customer_proj = Project(
        id=customer_proj_id,
        user_id=customer_user_id,
        name="Confidential Customer Project",
    )
    db_session.add(customer_proj)

    customer_run = Run(
        id=customer_run_id,
        project_id=customer_proj_id,
        name="confidential_workflow",
        status="completed",
        started_at=datetime.now(UTC),
    )
    db_session.add(customer_run)

    customer_dataset = Dataset(
        id=uuid.uuid4(),
        project_id=customer_proj_id,
        name="Confidential Dataset",
    )
    db_session.add(customer_dataset)
    await db_session.commit()

    # 2. Run demo seeding with --reset
    await seed_demo_data(db_session, reset=True)

    # 3. Assert all customer records remain 100% intact and untouched
    persisted_user = await db_session.get(User, customer_user_id)
    assert persisted_user is not None
    assert persisted_user.email == "customer@enterprise.acme"

    persisted_proj = await db_session.get(Project, customer_proj_id)
    assert persisted_proj is not None
    assert persisted_proj.name == "Confidential Customer Project"

    persisted_run = await db_session.get(Run, customer_run_id)
    assert persisted_run is not None
    assert persisted_run.name == "confidential_workflow"

    persisted_dataset = await db_session.get(Dataset, customer_dataset.id)
    assert persisted_dataset is not None
    assert persisted_dataset.name == "Confidential Dataset"

