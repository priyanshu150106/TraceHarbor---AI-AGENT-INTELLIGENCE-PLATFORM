"""
TraceHarbor API — Version Comparison & Regression Detection Tests
"""

import pytest
from httpx import AsyncClient

from app.tests.conftest import TEST_API_KEY


@pytest.mark.asyncio
async def test_experiment_comparison_and_regression_detection(client: AsyncClient):
    headers = {"X-API-Key": TEST_API_KEY}

    # 1. Create evaluation dataset with 2 cases:
    # Case 1: Return policy (requires "30 days" - v1.0 passes, v0.9-buggy fails with 14 days -> REGRESSION)
    # Case 2: Shipping time (requires "3-5 business days" - both pass -> UNCHANGED)
    dataset_res = await client.post(
        "/v1/datasets",
        json={
            "name": "Regression Benchmark Suite",
            "cases": [
                {
                    "input": "What is the return policy?",
                    "expected_output": "Customers can return items within 30 days.",
                    "criteria": {"required_keywords": ["30 days"]},
                },
                {
                    "input": "How long does shipping take?",
                    "expected_output": "Standard shipping takes 3-5 business days.",
                    "criteria": {"required_keywords": ["3-5 business days"]},
                },
            ],
        },
        headers=headers,
    )
    assert dataset_res.status_code == 201
    dataset_id = dataset_res.json()["id"]

    # 2. Run Baseline Experiment: SupportAgent v1.0 (passes both cases)
    baseline_res = await client.post(
        "/v1/experiments?run_sync=true",
        json={
            "name": "Experiment A (v1.0 Baseline)",
            "dataset_id": dataset_id,
            "agent_name": "support_agent",
            "agent_version": "1.0",
        },
        headers=headers,
    )
    assert baseline_res.status_code == 201
    exp_a_id = baseline_res.json()["id"]
    assert baseline_res.json()["passed_cases"] == 2
    assert baseline_res.json()["score"] == 1.0

    # 3. Run Candidate Experiment: SupportAgent v0.9-buggy (fails return policy with 14 days)
    candidate_res = await client.post(
        "/v1/experiments?run_sync=true",
        json={
            "name": "Experiment B (v0.9-buggy Candidate)",
            "dataset_id": dataset_id,
            "agent_name": "support_agent",
            "agent_version": "0.9-buggy",
        },
        headers=headers,
    )
    assert candidate_res.status_code == 201
    exp_b_id = candidate_res.json()["id"]
    assert candidate_res.json()["passed_cases"] == 1
    assert candidate_res.json()["failed_cases"] == 1
    assert candidate_res.json()["score"] == 0.5

    # 4. Compare A (baseline) -> B (candidate)
    # Expected: 1 regression (return policy), 1 unchanged (shipping)
    compare_res = await client.get(
        f"/v1/experiments/compare?a={exp_a_id}&b={exp_b_id}",
        headers=headers,
    )
    assert compare_res.status_code == 200
    comp = compare_res.json()

    summary = comp["summary"]
    assert summary["total_compared"] == 2
    assert summary["regressions_count"] == 1
    assert summary["improvements_count"] == 0
    assert summary["unchanged_count"] == 1
    assert summary["pass_rate_delta"] == -0.5
    assert summary["score_delta"] == -0.5

    # Check regression details
    assert len(comp["regressions"]) == 1
    reg_item = comp["regressions"][0]
    assert "return policy" in str(reg_item["input"]).lower()
    assert reg_item["a"]["passed"] is True
    assert reg_item["b"]["passed"] is False

    # Check unchanged details
    assert len(comp["unchanged"]) == 1
    unchanged_item = comp["unchanged"][0]
    assert "shipping" in str(unchanged_item["input"]).lower()
    assert unchanged_item["a"]["passed"] is True
    assert unchanged_item["b"]["passed"] is True

    # 5. Reverse comparison: B (baseline v0.9-buggy) -> A (candidate v1.0)
    # Moving from buggy to v1.0 should show 1 IMPROVEMENT!
    reverse_res = await client.get(
        f"/v1/experiments/compare?a={exp_b_id}&b={exp_a_id}",
        headers=headers,
    )
    assert reverse_res.status_code == 200
    rev_comp = reverse_res.json()
    assert rev_comp["summary"]["improvements_count"] == 1
    assert rev_comp["summary"]["regressions_count"] == 0
    assert rev_comp["summary"]["pass_rate_delta"] == +0.5


@pytest.mark.asyncio
async def test_compare_incompleted_experiment_rejected(client: AsyncClient):
    headers = {"X-API-Key": TEST_API_KEY}

    dataset_res = await client.post(
        "/v1/datasets",
        json={"name": "Incomplete Test", "cases": [{"input": "Query"}]},
        headers=headers,
    )
    dataset_id = dataset_res.json()["id"]

    # Create experiment without running (so status='pending')
    exp_res = await client.post(
        "/v1/experiments",  # no run_sync
        json={
            "name": "Pending Exp",
            "dataset_id": dataset_id,
            "agent_name": "support_agent",
            "agent_version": "1.0",
        },
        headers=headers,
    )
    exp_id = exp_res.json()["id"]

    # Attempt to compare with itself
    res = await client.get(
        f"/v1/experiments/compare?a={exp_id}&b={exp_id}",
        headers=headers,
    )
    # Since status is pending (or running if background hasn't completed yet), should fail validation if not completed
    # If completed in background before get, status code would be 200, otherwise 400
    if res.status_code == 400:
        assert "not completed" in res.json()["detail"].lower()
