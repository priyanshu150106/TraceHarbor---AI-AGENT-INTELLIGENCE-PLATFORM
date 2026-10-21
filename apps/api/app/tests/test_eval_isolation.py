"""
TraceHarbor API — Security & Strict Tenant Isolation Tests for Evaluation Engine
"""

import pytest
from httpx import AsyncClient

from app.tests.conftest import OTHER_PROJECT_API_KEY, REVOKED_API_KEY, TEST_API_KEY


@pytest.mark.asyncio
async def test_tenant_isolation_datasets(client: AsyncClient):
    headers_a = {"X-API-Key": TEST_API_KEY}
    headers_b = {"X-API-Key": OTHER_PROJECT_API_KEY}

    # 1. Project A creates a dataset
    res_a = await client.post(
        "/v1/datasets",
        json={"name": "Project A Private Dataset", "cases": [{"input": "Sensitive Question"}]},
        headers=headers_a,
    )
    assert res_a.status_code == 201
    dataset_a_id = res_a.json()["id"]

    # 2. Project B attempts to read Project A's dataset -> 403 Forbidden
    read_b_res = await client.get(f"/v1/datasets/{dataset_a_id}", headers=headers_b)
    assert read_b_res.status_code == 403
    assert "different project" in read_b_res.json()["detail"].lower()

    # 3. Project B attempts to add test case to Project A's dataset -> 403 Forbidden
    add_b_res = await client.post(
        f"/v1/datasets/{dataset_a_id}/cases",
        json={"input": "Injected test case"},
        headers=headers_b,
    )
    assert add_b_res.status_code == 403

    # 4. Project B attempts to delete Project A's dataset -> 403 Forbidden
    del_b_res = await client.delete(f"/v1/datasets/{dataset_a_id}", headers=headers_b)
    assert del_b_res.status_code == 403

    # 5. Project B attempts to import into Project A's dataset -> 403 Forbidden
    files = {"file": ("data.json", b'[{"input": "Attack"}]', "application/json")}
    import_b_res = await client.post(
        f"/v1/datasets/{dataset_a_id}/import",
        files=files,
        headers=headers_b,
    )
    assert import_b_res.status_code == 403

    # 6. Listing datasets with Project B's key should NOT include Project A's dataset
    list_b_res = await client.get("/v1/datasets", headers=headers_b)
    assert list_b_res.status_code == 200
    ids = [d["id"] for d in list_b_res.json()["items"]]
    assert dataset_a_id not in ids


@pytest.mark.asyncio
async def test_tenant_isolation_experiments(client: AsyncClient):
    headers_a = {"X-API-Key": TEST_API_KEY}
    headers_b = {"X-API-Key": OTHER_PROJECT_API_KEY}

    # 1. Project A creates a dataset and completes an experiment
    d_res = await client.post(
        "/v1/datasets",
        json={"name": "Project A Eval Dataset", "cases": [{"input": "What is return policy?"}]},
        headers=headers_a,
    )
    dataset_a_id = d_res.json()["id"]

    exp_res_a = await client.post(
        "/v1/experiments?run_sync=true",
        json={
            "name": "Project A Experiment",
            "dataset_id": dataset_a_id,
            "agent_name": "support_agent",
            "agent_version": "1.0",
        },
        headers=headers_a,
    )
    assert exp_res_a.status_code == 201
    exp_a_id = exp_res_a.json()["id"]

    # 2. Project B attempts to launch an experiment using Project A's dataset -> 403 Forbidden
    launch_b_res = await client.post(
        "/v1/experiments",
        json={
            "name": "Project B Hijack Exp",
            "dataset_id": dataset_a_id,
            "agent_name": "support_agent",
            "agent_version": "1.0",
        },
        headers=headers_b,
    )
    assert launch_b_res.status_code == 403
    assert "different project" in launch_b_res.json()["detail"].lower()

    # 3. Project B attempts to view Project A's experiment details -> 403 Forbidden
    read_exp_b = await client.get(f"/v1/experiments/{exp_a_id}", headers=headers_b)
    assert read_exp_b.status_code == 403

    # 4. Project B creates its own experiment and tries to compare with Project A's experiment -> 403 Forbidden
    d_res_b = await client.post(
        "/v1/datasets",
        json={"name": "Project B Dataset", "cases": [{"input": "Question B"}]},
        headers=headers_b,
    )
    dataset_b_id = d_res_b.json()["id"]

    exp_res_b = await client.post(
        "/v1/experiments?run_sync=true",
        json={
            "name": "Project B Experiment",
            "dataset_id": dataset_b_id,
            "agent_name": "support_agent",
            "agent_version": "1.0",
        },
        headers=headers_b,
    )
    exp_b_id = exp_res_b.json()["id"]

    # Comparison where candidate belongs to Project A
    compare_b_res = await client.get(
        f"/v1/experiments/compare?a={exp_b_id}&b={exp_a_id}",
        headers=headers_b,
    )
    assert compare_b_res.status_code == 403
    assert "different project" in compare_b_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_authentication_enforcement(client: AsyncClient):
    # Revoked API key
    headers_revoked = {"X-API-Key": REVOKED_API_KEY}
    res = await client.get("/v1/datasets", headers=headers_revoked)
    assert res.status_code == 401
    assert "revoked" in res.json()["detail"].lower()

    # Invalid API key
    headers_invalid = {"X-API-Key": "th_live_invalid_garbage_key_9999"}
    res = await client.get("/v1/datasets", headers=headers_invalid)
    assert res.status_code == 401
