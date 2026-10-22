"""
Tests for Phase 4 Advanced Analytics APIs and Metric Semantics
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.tests.conftest import OTHER_PROJECT_API_KEY, TEST_API_KEY


@pytest.mark.asyncio
async def test_analytics_overview_and_filters(client: AsyncClient) -> None:
    """Test overview analytics with time-range and agent filters."""
    headers = {"X-API-Key": TEST_API_KEY}
    now = datetime.now(UTC)

    # Ingest 3 runs: 2 completed for SupportAgent, 1 error for BillingAgent
    run1_id = str(uuid.uuid4())
    run2_id = str(uuid.uuid4())
    run3_id = str(uuid.uuid4())

    payload = {
        "runs": [
            {
                "id": run1_id,
                "name": "SupportAgent",
                "status": "completed",
                "duration_ms": 500,
                "total_tokens": 100,
                "total_cost_usd": 0.002,
                "started_at": (now - timedelta(hours=2)).isoformat(),
            },
            {
                "id": run2_id,
                "name": "SupportAgent",
                "status": "completed",
                "duration_ms": 1500,
                "total_tokens": 200,
                "total_cost_usd": 0.004,
                "started_at": (now - timedelta(hours=1)).isoformat(),
            },
            {
                "id": run3_id,
                "name": "BillingAgent",
                "status": "error",
                "duration_ms": 200,
                "total_tokens": 50,
                "total_cost_usd": 0.001,
                "started_at": (now - timedelta(minutes=30)).isoformat(),
            },
        ],
        "spans": [],
    }
    ingest_res = await client.post("/v1/ingest/spans", json=payload, headers=headers)
    assert ingest_res.status_code == 200

    # Query overview for all agents
    res = await client.get("/v1/analytics/overview?time_range=24h", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_runs"] == 3
    assert data["successful_runs"] == 2
    assert data["failed_runs"] == 1
    assert round(data["error_rate"], 2) == 0.33
    assert data["total_tokens"] == 350
    assert data["total_cost_usd"] == 0.007
    assert data["cost_reported_runs"] == 3
    assert data["unmetered_runs"] == 0
    assert data["p50_duration_ms"] > 0
    assert data["p95_duration_ms"] > 0

    # Query overview filtered by agent_name
    res_agent = await client.get("/v1/analytics/overview?time_range=24h&agent_name=SupportAgent", headers=headers)
    assert res_agent.status_code == 200
    agent_data = res_agent.json()
    assert agent_data["total_runs"] == 2
    assert agent_data["successful_runs"] == 2
    assert agent_data["failed_runs"] == 0
    assert agent_data["error_rate"] == 0.0


@pytest.mark.asyncio
async def test_analytics_timeseries(client: AsyncClient) -> None:
    """Test time-series endpoint with continuous bucketing."""
    headers = {"X-API-Key": TEST_API_KEY}
    now = datetime.now(UTC)

    run_id = str(uuid.uuid4())
    payload = {
        "runs": [
            {
                "id": run_id,
                "name": "AgentX",
                "status": "completed",
                "duration_ms": 450,
                "total_tokens": 120,
                "total_cost_usd": 0.0015,
                "started_at": (now - timedelta(days=1)).isoformat(),
            }
        ],
        "spans": [],
    }
    await client.post("/v1/ingest/spans", json=payload, headers=headers)

    res = await client.get("/v1/analytics/timeseries?time_range=7d", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["time_range"] == "7d"
    assert data["interval"] == "1d"
    assert len(data["points"]) >= 7
    total_in_points = sum(p["total_runs"] for p in data["points"])
    assert total_in_points >= 1


@pytest.mark.asyncio
async def test_analytics_models_and_cost_breakdown(client: AsyncClient) -> None:
    """Test model usage analytics and cost breakdown attribution."""
    headers = {"X-API-Key": TEST_API_KEY}
    now = datetime.now(UTC)

    run_id = str(uuid.uuid4())
    span1_id = str(uuid.uuid4())
    span2_id = str(uuid.uuid4())

    payload = {
        "runs": [
            {
                "id": run_id,
                "name": "SupportAgent",
                "status": "completed",
                "duration_ms": 600,
                "total_tokens": 250,
                "total_cost_usd": 0.005,
                "started_at": (now - timedelta(hours=3)).isoformat(),
            }
        ],
        "spans": [
            {
                "id": span1_id,
                "run_id": run_id,
                "name": "llm_call",
                "span_type": "llm",
                "model": "gpt-4o-mini",
                "prompt_tokens": 150,
                "completion_tokens": 50,
                "total_tokens": 200,
                "cost_usd": 0.004,
                "duration_ms": 400,
                "started_at": (now - timedelta(hours=3)).isoformat(),
            },
            {
                "id": span2_id,
                "run_id": run_id,
                "name": "embedding_call",
                "span_type": "llm",
                "model": "text-embedding-3-small",
                "prompt_tokens": 50,
                "completion_tokens": 0,
                "total_tokens": 50,
                "cost_usd": 0.001,
                "duration_ms": 100,
                "started_at": (now - timedelta(hours=3)).isoformat(),
            },
        ],
    }
    await client.post("/v1/ingest/spans", json=payload, headers=headers)

    # Models breakdown
    res_models = await client.get("/v1/analytics/models?time_range=24h", headers=headers)
    assert res_models.status_code == 200
    models_data = res_models.json()
    assert models_data["total_models"] == 2
    model_names = [m["model"] for m in models_data["items"]]
    assert "gpt-4o-mini" in model_names
    assert "text-embedding-3-small" in model_names

    # Cost breakdown
    res_cost = await client.get("/v1/analytics/cost-breakdown?time_range=24h", headers=headers)
    assert res_cost.status_code == 200
    cost_data = res_cost.json()
    assert cost_data["total_cost_usd"] == 0.005
    assert cost_data["by_agent"]["SupportAgent"] == 0.005
    assert "gpt-4o-mini" in cost_data["by_model"]


@pytest.mark.asyncio
async def test_analytics_agents_comparison(client: AsyncClient) -> None:
    """Test agents comparison breakdown endpoint."""
    headers = {"X-API-Key": TEST_API_KEY}
    now = datetime.now(UTC)

    payload = {
        "runs": [
            {
                "id": str(uuid.uuid4()),
                "name": "SupportAgent",
                "status": "completed",
                "duration_ms": 500,
                "total_tokens": 100,
                "total_cost_usd": 0.002,
                "tags": ["v1.0"],
                "started_at": (now - timedelta(hours=2)).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "name": "SupportAgent",
                "status": "completed",
                "duration_ms": 300,
                "total_tokens": 80,
                "total_cost_usd": 0.0015,
                "tags": ["v2.0"],
                "started_at": (now - timedelta(hours=1)).isoformat(),
            },
        ],
        "spans": [],
    }
    await client.post("/v1/ingest/spans", json=payload, headers=headers)

    res = await client.get("/v1/analytics/agents?time_range=24h", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_agents"] == 2
    versions = [a["agent_version"] for a in data["items"]]
    assert "1.0" in versions
    assert "2.0" in versions


@pytest.mark.asyncio
async def test_analytics_empty_project(client: AsyncClient) -> None:
    """Ensure zeroed responses for isolated other project without data."""
    headers = {"X-API-Key": OTHER_PROJECT_API_KEY}
    res_ov = await client.get("/v1/analytics/overview", headers=headers)
    assert res_ov.status_code == 200
    assert res_ov.json()["total_runs"] == 0

    res_ts = await client.get("/v1/analytics/timeseries", headers=headers)
    assert res_ts.status_code == 200
    assert len(res_ts.json()["points"]) >= 7

    res_mod = await client.get("/v1/analytics/models", headers=headers)
    assert res_mod.status_code == 200
    assert res_mod.json()["total_models"] == 0
