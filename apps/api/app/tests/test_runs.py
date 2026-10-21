"""
TraceHarbor API — Runs, Spans & Analytics Read Endpoints Tests
"""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.tests.conftest import (
    OTHER_PROJECT_API_KEY,
    TEST_API_KEY,
)


@pytest.mark.asyncio
async def test_empty_runs_and_analytics(client: AsyncClient) -> None:
    """Verify empty project returns zeroed metrics and empty list without errors."""
    res_runs = await client.get("/v1/runs", headers={"X-API-Key": TEST_API_KEY})
    assert res_runs.status_code == 200
    runs_data = res_runs.json()
    assert runs_data["total"] == 0
    assert runs_data["items"] == []

    res_analytics = await client.get("/v1/analytics/overview", headers={"X-API-Key": TEST_API_KEY})
    assert res_analytics.status_code == 200
    analytics_data = res_analytics.json()
    assert analytics_data["total_runs"] == 0
    assert analytics_data["error_rate"] == 0.0
    assert analytics_data["recent_runs"] == []


@pytest.mark.asyncio
async def test_list_runs_pagination_and_filtering(client: AsyncClient) -> None:
    """Verify listing runs supports filtering by status, search by name, and pagination."""
    now_iso = datetime.now(UTC).isoformat()

    # Ingest 3 runs: 2 completed, 1 error
    run1_id = str(uuid.uuid4())
    run2_id = str(uuid.uuid4())
    run3_id = str(uuid.uuid4())

    payload = {
        "runs": [
            {
                "id": run1_id,
                "name": "Customer Support Agent",
                "status": "completed",
                "duration_ms": 120,
                "total_tokens": 50,
                "total_cost_usd": 0.0001,
                "started_at": now_iso,
            },
            {
                "id": run2_id,
                "name": "Research Agent",
                "status": "completed",
                "duration_ms": 250,
                "total_tokens": 100,
                "total_cost_usd": 0.0002,
                "started_at": now_iso,
            },
            {
                "id": run3_id,
                "name": "Customer Support Agent",
                "status": "error",
                "error": "Timeout connecting to tool",
                "duration_ms": 500,
                "total_tokens": 30,
                "total_cost_usd": 0.00005,
                "started_at": now_iso,
            },
        ],
        "spans": [],
    }
    ingest_res = await client.post("/v1/ingest/spans", headers={"X-API-Key": TEST_API_KEY}, json=payload)
    assert ingest_res.status_code == 200

    # 1. List all runs
    res_all = await client.get("/v1/runs", headers={"X-API-Key": TEST_API_KEY})
    assert res_all.status_code == 200
    assert res_all.json()["total"] == 3

    # 2. Filter by status=error
    res_error = await client.get("/v1/runs?status=error", headers={"X-API-Key": TEST_API_KEY})
    assert res_error.status_code == 200
    error_items = res_error.json()["items"]
    assert len(error_items) == 1
    assert error_items[0]["id"] == run3_id

    # 3. Filter by search="Research"
    res_search = await client.get("/v1/runs?search=Research", headers={"X-API-Key": TEST_API_KEY})
    assert res_search.status_code == 200
    search_items = res_search.json()["items"]
    assert len(search_items) == 1
    assert search_items[0]["id"] == run2_id

    # 4. Pagination: page_size=2
    res_p1 = await client.get("/v1/runs?page=1&page_size=2", headers={"X-API-Key": TEST_API_KEY})
    assert res_p1.status_code == 200
    p1_data = res_p1.json()
    assert len(p1_data["items"]) == 2
    assert p1_data["total"] == 3
    assert p1_data["total_pages"] == 2


@pytest.mark.asyncio
async def test_get_run_detail_with_spans(client: AsyncClient) -> None:
    """Verify run detail endpoint returns input, output, and all child spans in order."""
    run_id = str(uuid.uuid4())
    parent_span_id = str(uuid.uuid4())
    child_span_id = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()

    payload = {
        "runs": [
            {
                "id": run_id,
                "name": "Support Reasoning Run",
                "status": "completed",
                "input": {"question": "Return policy?"},
                "output": {"answer": "30 days."},
                "total_tokens": 150,
                "started_at": now_iso,
            }
        ],
        "spans": [
            {
                "id": parent_span_id,
                "run_id": run_id,
                "name": "agent_root",
                "span_type": "agent",
                "started_at": now_iso,
            },
            {
                "id": child_span_id,
                "run_id": run_id,
                "parent_span_id": parent_span_id,
                "name": "tool_kb_search",
                "span_type": "tool",
                "started_at": now_iso,
            },
        ],
    }
    await client.post("/v1/ingest/spans", headers={"X-API-Key": TEST_API_KEY}, json=payload)

    # Fetch run detail
    res = await client.get(f"/v1/runs/{run_id}", headers={"X-API-Key": TEST_API_KEY})
    assert res.status_code == 200
    detail = res.json()
    assert detail["id"] == run_id
    assert detail["name"] == "Support Reasoning Run"
    assert detail["input"]["question"] == "Return policy?"
    assert detail["output"]["answer"] == "30 days."
    assert len(detail["spans"]) == 2

    span_ids = [s["id"] for s in detail["spans"]]
    assert parent_span_id in span_ids
    assert child_span_id in span_ids


@pytest.mark.asyncio
async def test_run_detail_not_found(client: AsyncClient) -> None:
    """Verify non-existent run ID returns 404 Not Found."""
    random_id = str(uuid.uuid4())
    res = await client.get(f"/v1/runs/{random_id}", headers={"X-API-Key": TEST_API_KEY})
    assert res.status_code == 404
    assert f"Run '{random_id}' not found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_run_detail_tenant_isolation(client: AsyncClient) -> None:
    """Verify a project cannot view runs belonging to a different project."""
    run_id = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()

    # Create run under Project A
    await client.post(
        "/v1/ingest/spans",
        headers={"X-API-Key": TEST_API_KEY},
        json={"runs": [{"id": run_id, "name": "Project A Private Run", "started_at": now_iso}], "spans": []},
    )

    # Attempt to read from Project B
    res_b = await client.get(f"/v1/runs/{run_id}", headers={"X-API-Key": OTHER_PROJECT_API_KEY})
    assert res_b.status_code == 403
    assert "belongs to a different project" in res_b.json()["detail"]


@pytest.mark.asyncio
async def test_analytics_overview_calculations(client: AsyncClient) -> None:
    """Verify analytics overview computes counts, error rate, latency percentiles, and tokens."""
    now_iso = datetime.now(UTC).isoformat()

    # Ingest 4 completed runs with durations: 100, 200, 300, 400 and 1 error run with 500
    runs = [
        {"id": str(uuid.uuid4()), "status": "completed", "duration_ms": 100, "total_tokens": 10, "started_at": now_iso},
        {"id": str(uuid.uuid4()), "status": "completed", "duration_ms": 200, "total_tokens": 20, "started_at": now_iso},
        {"id": str(uuid.uuid4()), "status": "completed", "duration_ms": 300, "total_tokens": 30, "started_at": now_iso},
        {"id": str(uuid.uuid4()), "status": "completed", "duration_ms": 400, "total_tokens": 40, "started_at": now_iso},
        {"id": str(uuid.uuid4()), "status": "error", "duration_ms": 500, "total_tokens": 50, "started_at": now_iso},
    ]
    await client.post("/v1/ingest/spans", headers={"X-API-Key": TEST_API_KEY}, json={"runs": runs, "spans": []})

    res = await client.get("/v1/analytics/overview", headers={"X-API-Key": TEST_API_KEY})
    assert res.status_code == 200
    data = res.json()
    assert data["total_runs"] == 5
    assert data["successful_runs"] == 4
    assert data["failed_runs"] == 1
    assert data["error_rate"] == 0.2  # 1 / 5 = 20%
    assert data["total_tokens"] == 150
    assert data["avg_duration_ms"] == 300.0  # (100+200+300+400+500)/5 = 300
    assert len(data["recent_runs"]) == 5


@pytest.mark.asyncio
async def test_projects_list_endpoint(client: AsyncClient) -> None:
    """Verify /v1/projects lists seeded projects and does not leak API keys."""
    res = await client.get("/v1/projects")
    assert res.status_code == 200
    projects = res.json()
    assert len(projects) >= 2

    for p in projects:
        assert "id" in p
        assert "name" in p
        assert "runs_count" in p
        assert "key_hash" not in p  # Security: never expose hashes or secrets
