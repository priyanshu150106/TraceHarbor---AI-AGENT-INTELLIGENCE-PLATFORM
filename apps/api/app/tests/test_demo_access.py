"""
TraceHarbor API — Safe Demo Access & Tenant Security Tests

Validates:
- Unauthenticated requests in production mode (debug=False, demo_mode=False) return 401.
- Valid normal live authentication continues to work for read and write.
- Demo credentials ('th_demo_') are restricted to read-only access.
- Demo credentials cannot access another tenant's project data (403).
- Demo credentials cannot execute mutations or privileged operations (403).
- Public demo mode allows read-only demo access while strictly blocking cross-tenant and mutation requests.
- Invalid, revoked, or malformed credentials return 401.
"""

import hashlib
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.api_key import ApiKey
from app.models.project import Project
from app.models.user import User
from app.tests.conftest import (
    OTHER_PROJECT_API_KEY,
    REVOKED_API_KEY,
    TEST_API_KEY,
)

# Dedicated demo synthetic key
DEMO_KEY = "th_demo_synthetic_portfolio_key_778899"
DEMO_KEY_HASH = hashlib.sha256(DEMO_KEY.encode("utf-8")).hexdigest()


@pytest.fixture
async def setup_demo_tenant(db_session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    """Create a dedicated synthetic demo tenant project and demo API key."""
    # Find existing test user
    from sqlalchemy import select
    res = await db_session.execute(select(User).limit(1))
    user = res.scalar_one()

    demo_project_id = uuid.uuid4()
    demo_project = Project(
        id=demo_project_id,
        user_id=user.id,
        name="Portfolio Demo Project",
    )
    db_session.add(demo_project)

    demo_key = ApiKey(
        id=uuid.uuid4(),
        project_id=demo_project_id,
        name="Public Portfolio Demo Key",
        key_hash=DEMO_KEY_HASH,
        key_prefix="th_demo_",
        is_active=True,
    )
    db_session.add(demo_key)
    await db_session.commit()

    return demo_project_id, user.id


@pytest.mark.asyncio
async def test_unauthenticated_protected_requests_rejected(client: AsyncClient) -> None:
    """In production mode, unauthenticated access to endpoints must be rejected with 401."""
    orig_debug = settings.debug
    orig_demo = settings.demo_mode
    try:
        settings.debug = False
        settings.demo_mode = False

        # Read attempt
        res_read = await client.get("/v1/runs")
        assert res_read.status_code == 401
        assert "API key" in res_read.json()["detail"]

        # Mutation attempt
        res_write = await client.post("/v1/datasets", json={"name": "Test Dataset"})
        assert res_write.status_code == 401
    finally:
        settings.debug = orig_debug
        settings.demo_mode = orig_demo


@pytest.mark.asyncio
async def test_valid_normal_auth_works_read_and_write(client: AsyncClient) -> None:
    """Valid live key ('th_live_') continues to support both read and write operations."""
    headers = {"X-API-Key": TEST_API_KEY}

    # Write operation: Create dataset
    res_create = await client.post(
        "/v1/datasets",
        json={"name": "Live Tenant Dataset", "cases": [{"input": "Hello World"}]},
        headers=headers,
    )
    assert res_create.status_code == 201
    dataset_id = res_create.json()["id"]

    # Read operation: Fetch dataset
    res_read = await client.get(f"/v1/datasets/{dataset_id}", headers=headers)
    assert res_read.status_code == 200
    assert res_read.json()["id"] == dataset_id


@pytest.mark.asyncio
async def test_demo_credentials_cannot_access_other_tenant_data(
    client: AsyncClient,
    setup_demo_tenant: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Demo key cannot access another project's data (403 Forbidden)."""
    demo_project_id, _ = setup_demo_tenant
    other_project_id = uuid.uuid4()
    headers = {"X-API-Key": DEMO_KEY}

    # Attempt cross-tenant query by specifying another project's UUID
    res = await client.get(f"/v1/runs?project_id={other_project_id}", headers=headers)
    assert res.status_code == 403
    assert "does not match API key project" in res.json()["detail"]


@pytest.mark.asyncio
async def test_demo_credentials_cannot_perform_privileged_mutations(
    client: AsyncClient,
    setup_demo_tenant: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Demo key is strictly forbidden from executing create, update, delete, or ingest."""
    demo_project_id, _ = setup_demo_tenant
    headers = {"X-API-Key": DEMO_KEY}

    # 1. Dataset creation mutation
    res_dataset = await client.post(
        "/v1/datasets",
        json={"name": "Hacked Dataset"},
        headers=headers,
    )
    assert res_dataset.status_code == 403
    assert "restricted to read-only access" in res_dataset.json()["detail"]

    # 2. Experiment launch mutation
    res_exp = await client.post(
        "/v1/experiments",
        json={
            "name": "Unauthorized Experiment",
            "dataset_id": str(uuid.uuid4()),
            "agent_name": "attacker_agent",
        },
        headers=headers,
    )
    assert res_exp.status_code == 403
    assert "restricted to read-only access" in res_exp.json()["detail"]

    # 3. Task cancellation mutation
    random_task_id = f"task_{uuid.uuid4().hex[:12]}"
    res_task = await client.post(f"/v1/tasks/{random_task_id}/cancel", headers=headers)
    assert res_task.status_code == 403
    assert "restricted to read-only access" in res_task.json()["detail"]

    # 4. Telemetry ingestion mutation
    res_ingest = await client.post(
        "/v1/ingest/spans",
        json={"runs": [], "spans": []},
        headers=headers,
    )
    assert res_ingest.status_code == 403
    assert "restricted to read-only access" in res_ingest.json()["detail"]

    # 5. Safety campaign launch mutation
    res_safety = await client.post(
        "/v1/safety/campaigns",
        json={
            "name": "Unauthorized Campaign",
            "agent_name": "agent",
            "attack_categories": ["prompt_injection"],
        },
        headers=headers,
    )
    assert res_safety.status_code == 403
    assert "restricted to read-only access" in res_safety.json()["detail"]

    # 6. Alert rule creation mutation
    res_alert = await client.post(
        "/v1/alerts/rules",
        json={
            "name": "Malicious Rule",
            "metric": "error_rate",
            "threshold": 0.5,
            "window_minutes": 5,
        },
        headers=headers,
    )
    assert res_alert.status_code == 403
    assert "restricted to read-only access" in res_alert.json()["detail"]


@pytest.mark.asyncio
async def test_public_demo_mode_allows_safe_reads_and_blocks_mutations(
    client: AsyncClient,
    setup_demo_tenant: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """
    When demo_mode=True (for public portfolio deployment):
    - Unauthenticated reads succeed scoped to the demo project.
    - Unauthenticated reads attempting cross-tenant access return 403.
    - Unauthenticated mutations return 403.
    """
    demo_project_id, _ = setup_demo_tenant
    other_tenant_id = uuid.uuid4()

    orig_debug = settings.debug
    orig_demo = settings.demo_mode
    orig_demo_project_id = settings.demo_project_id

    try:
        settings.debug = False
        settings.demo_mode = True
        settings.demo_project_id = str(demo_project_id)

        # 1. Unauthenticated read within demo project -> 200 OK
        res_read = await client.get("/v1/runs")
        assert res_read.status_code == 200

        # 2. Unauthenticated read trying to probe another tenant -> 403 Forbidden
        res_cross = await client.get(f"/v1/runs?project_id={other_tenant_id}")
        assert res_cross.status_code == 403
        assert "cannot access other project data" in res_cross.json()["detail"]

        # 3. Unauthenticated mutation attempt -> 403 Forbidden
        res_mutation = await client.post(
            "/v1/datasets",
            json={"name": "Public Mutation"},
        )
        assert res_mutation.status_code == 403
        assert "Public demo access is strictly read-only" in res_mutation.json()["detail"]

        # 4. Unauthenticated task cancellation -> 403 Forbidden
        res_cancel = await client.post("/v1/tasks/any-task/cancel")
        assert res_cancel.status_code == 403
    finally:
        settings.debug = orig_debug
        settings.demo_mode = orig_demo
        settings.demo_project_id = orig_demo_project_id


@pytest.mark.asyncio
async def test_expired_or_invalid_or_malformed_credentials_rejected(client: AsyncClient) -> None:
    """Revoked, invalid, and malformed credentials must be strictly rejected with 401."""
    # Revoked active=False key
    res_revoked = await client.get("/v1/runs", headers={"X-API-Key": REVOKED_API_KEY})
    assert res_revoked.status_code == 401
    assert "Invalid or revoked" in res_revoked.json()["detail"]

    # Completely unknown key
    res_unknown = await client.get("/v1/runs", headers={"X-API-Key": "th_live_unknown_nonexistent_key"})
    assert res_unknown.status_code == 401

    # Whitespace key
    res_blank = await client.get("/v1/runs", headers={"X-API-Key": "   "})
    assert res_blank.status_code == 401

    # Bearer auth with invalid token
    res_bearer = await client.get("/v1/runs", headers={"Authorization": "Bearer invalid_token_123"})
    assert res_bearer.status_code == 401


@pytest.mark.asyncio
async def test_private_demo_seeding_and_read_only_workflow(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Verify complete public demo workflow:
    1. Seed synthetic demo records via private process
    2. Confirm expected demo records exist and are strictly isolated
    3. Confirm unauthenticated public reads expose only approved demo data
    4. Confirm public mutations and ingestion are rejected
    5. Confirm cross-tenant reads are rejected
    """
    from scripts.seed_demo_data import (
        DEMO_PROJECT_ID,
        seed_demo_data,
        verify_demo_tenant,
    )

    # 1. Private seeding execution
    counts = await seed_demo_data(db_session, reset=True)
    assert counts["runs"] >= 2
    assert counts["datasets"] >= 2
    assert counts["experiments"] >= 1
    assert counts["safety_campaigns"] >= 1

    # 2. Verify records exist and belong exclusively to DEMO_PROJECT_ID
    verification = await verify_demo_tenant(db_session)
    assert verification["runs"] == counts["runs"]

    # 3. Enable public demo mode
    orig_debug = settings.debug
    orig_demo = settings.demo_mode
    orig_demo_project_id = settings.demo_project_id

    try:
        settings.debug = False
        settings.demo_mode = True
        settings.demo_project_id = str(DEMO_PROJECT_ID)

        # A. Unauthenticated reads expose approved demo data
        res_runs = await client.get("/v1/runs")
        assert res_runs.status_code == 200
        runs_body = res_runs.json()
        assert runs_body["total"] >= 2
        for r in runs_body["items"]:
            assert r["project_id"] == str(DEMO_PROJECT_ID)

        res_projects = await client.get("/v1/projects")
        assert res_projects.status_code == 200
        proj_list = res_projects.json()
        assert len(proj_list) == 1
        assert proj_list[0]["id"] == str(DEMO_PROJECT_ID)

        res_datasets = await client.get("/v1/datasets")
        assert res_datasets.status_code == 200
        assert res_datasets.json()["total"] >= 2

        res_experiments = await client.get("/v1/experiments")
        assert res_experiments.status_code == 200
        assert res_experiments.json()["total"] >= 1

        res_safety = await client.get("/v1/safety/overview")
        assert res_safety.status_code == 200
        assert res_safety.json()["total_campaigns"] >= 1

        res_failures = await client.get("/v1/failures/overview")
        assert res_failures.status_code == 200

        res_alerts = await client.get("/v1/alerts/rules")
        assert res_alerts.status_code == 200
        assert len(res_alerts.json()) >= 1

        res_analytics = await client.get("/v1/analytics/overview")
        assert res_analytics.status_code == 200

        # B. Unauthenticated mutations are rejected with 403 Forbidden
        res_mut_ds = await client.post("/v1/datasets", json={"name": "Hacked Dataset"})
        assert res_mut_ds.status_code == 403
        assert "strictly read-only" in res_mut_ds.json()["detail"]

        res_mut_ingest = await client.post("/v1/ingest/spans", json={"runs": [], "spans": []})
        assert res_mut_ingest.status_code in (401, 403)

        res_mut_exp = await client.post(
            "/v1/experiments",
            json={"name": "Attacker Exp", "dataset_id": str(uuid.uuid4()), "agent_name": "agent"},
        )
        assert res_mut_exp.status_code == 403

        # C. Cross-tenant queries are rejected with 403 Forbidden
        other_project_id = uuid.uuid4()
        res_cross = await client.get(f"/v1/runs?project_id={other_project_id}")
        assert res_cross.status_code == 403
        assert "cannot access other project data" in res_cross.json()["detail"]

    finally:
        settings.debug = orig_debug
        settings.demo_mode = orig_demo
        settings.demo_project_id = orig_demo_project_id


@pytest.mark.asyncio
async def test_demo_project_resolution_without_fallback_in_production(
    client: AsyncClient,
) -> None:
    """In production mode (debug=False), missing demo project must return 404, never fallback to customer records."""
    orig_debug = settings.debug
    orig_demo = settings.demo_mode
    orig_demo_project_id = settings.demo_project_id

    try:
        settings.debug = False
        settings.demo_mode = True
        # Set to non-existent UUID
        settings.demo_project_id = str(uuid.uuid4())

        # When resolving, since demo project doesn't exist and debug=False, must return 404
        res = await client.get("/v1/runs")
        assert res.status_code == 404
        assert "No demo project is configured or available" in res.json()["detail"]
    finally:
        settings.debug = orig_debug
        settings.demo_mode = orig_demo
        settings.demo_project_id = orig_demo_project_id

