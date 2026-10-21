"""
TraceHarbor API — Experiment Execution & Agent Lifecycle Tests
"""

import pytest
from httpx import AsyncClient

from app.tests.conftest import TEST_API_KEY


@pytest.mark.asyncio
async def test_list_approved_agents(client: AsyncClient):
    res = await client.get("/v1/experiments/agents")
    assert res.status_code == 200
    agents = res.json()
    assert len(agents) >= 3
    versions = [a["agent_version"] for a in agents if a["agent_name"] == "support_agent"]
    assert "1.0" in versions
    assert "2.0-improved" in versions
    assert "0.9-buggy" in versions


@pytest.mark.asyncio
async def test_create_and_execute_experiment_lifecycle(client: AsyncClient):
    headers = {"X-API-Key": TEST_API_KEY}

    # 1. Create a dataset with 2 cases (one positive, one with specific criteria)
    dataset_res = await client.post(
        "/v1/datasets",
        json={
            "name": "E2E Support Test",
            "cases": [
                {
                    "input": "What is the return policy?",
                    "expected_output": "Customers can return items within 30 days of purchase for a full refund or exchange.",
                    "criteria": {"required_keywords": ["30 days", "refund"]},
                },
                {
                    "input": "How long does shipping take?",
                    "expected_output": "Standard shipping takes 3-5 business days. Express shipping takes 1-2 business days.",
                    "criteria": {"required_keywords": ["3-5 business days"]},
                },
            ],
        },
        headers=headers,
    )
    assert dataset_res.status_code == 201
    dataset_id = dataset_res.json()["id"]

    # 2. Launch experiment synchronously
    exp_payload = {
        "name": "Benchmark Support v1.0",
        "dataset_id": dataset_id,
        "agent_name": "support_agent",
        "agent_version": "1.0",
        "description": "Evaluating v1.0 baseline against core FAQ dataset",
    }

    create_res = await client.post(
        "/v1/experiments?run_sync=true",
        json=exp_payload,
        headers=headers,
    )
    assert create_res.status_code == 201
    exp_data = create_res.json()
    assert exp_data["name"] == "Benchmark Support v1.0"
    assert exp_data["status"] == "completed"
    assert exp_data["total_cases"] == 2
    assert exp_data["passed_cases"] == 2
    assert exp_data["score"] == 1.0
    assert exp_data["pass_rate"] == 1.0
    experiment_id = exp_data["id"]

    # 3. Retrieve experiment detail and verify per-case results
    detail_res = await client.get(f"/v1/experiments/{experiment_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["status"] == "completed"
    assert len(detail["results"]) == 2

    first_result = detail["results"][0]
    assert first_result["passed"] is True
    assert first_result["status"] == "pass"
    assert first_result["actual_output"] is not None
    assert "30 days" in str(first_result["actual_output"])
    assert len(first_result["evaluation_details"]) > 0

    # 4. Verify linked observability trace run exists
    run_id = first_result["run_id"]
    assert run_id is not None
    run_res = await client.get(f"/v1/runs/{run_id}", headers=headers)
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert "eval:Benchmark Support v1.0" in run_data["name"]
    assert len(run_data["spans"]) >= 1  # Spans recorded!

    # 5. List experiments
    list_res = await client.get("/v1/experiments", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(e["id"] == experiment_id for e in items)


@pytest.mark.asyncio
async def test_experiment_unapproved_agent_rejected(client: AsyncClient):
    headers = {"X-API-Key": TEST_API_KEY}

    dataset_res = await client.post(
        "/v1/datasets",
        json={"name": "Temp Dataset", "cases": [{"input": "Hello"}]},
        headers=headers,
    )
    dataset_id = dataset_res.json()["id"]

    # Attempt to run arbitrary unapproved agent
    res = await client.post(
        "/v1/experiments",
        json={
            "name": "Malicious / Unapproved Agent",
            "dataset_id": dataset_id,
            "agent_name": "arbitrary_custom_evaluator",
            "agent_version": "99.0",
        },
        headers=headers,
    )
    assert res.status_code == 422
    assert "not in the approved agent registry" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_experiment_on_empty_dataset_rejected(client: AsyncClient):
    headers = {"X-API-Key": TEST_API_KEY}

    dataset_res = await client.post(
        "/v1/datasets",
        json={"name": "Empty Dataset"},
        headers=headers,
    )
    dataset_id = dataset_res.json()["id"]

    res = await client.post(
        "/v1/experiments",
        json={
            "name": "Test Run",
            "dataset_id": dataset_id,
            "agent_name": "support_agent",
            "agent_version": "1.0",
        },
        headers=headers,
    )
    assert res.status_code == 422
    assert "has no test cases" in res.json()["detail"].lower()
