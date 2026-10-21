"""
TraceHarbor API — Trace Ingestion Endpoint Tests
"""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.tests.conftest import (
    OTHER_PROJECT_API_KEY,
    REVOKED_API_KEY,
    TEST_API_KEY,
)


@pytest.mark.asyncio
async def test_ingest_spans_missing_api_key(client: AsyncClient) -> None:
    """Verify ingestion requests without an API key are rejected with 401 Unauthorized."""
    response = await client.post(
        "/v1/ingest/spans",
        json={"runs": [], "spans": []},
    )
    assert response.status_code == 401
    assert "API key required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ingest_spans_invalid_or_revoked_key(client: AsyncClient) -> None:
    """Verify unknown or revoked API keys are rejected with 401 Unauthorized."""
    # Unknown key
    res_unknown = await client.post(
        "/v1/ingest/spans",
        headers={"X-API-Key": "th_live_nonexistent_key"},
        json={"runs": [], "spans": []},
    )
    assert res_unknown.status_code == 401
    assert "Invalid or revoked API key" in res_unknown.json()["detail"]

    # Revoked key
    res_revoked = await client.post(
        "/v1/ingest/spans",
        headers={"X-API-Key": REVOKED_API_KEY},
        json={"runs": [], "spans": []},
    )
    assert res_revoked.status_code == 401


@pytest.mark.asyncio
async def test_ingest_valid_batch(client: AsyncClient) -> None:
    """Verify valid batch with Run and Span records persists and returns 200 OK."""
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()

    payload = {
        "runs": [
            {
                "id": run_id,
                "name": "Customer Support Test Run",
                "status": "completed",
                "input": {"question": "What is the return policy?"},
                "output": {"answer": "30 days refund guarantee."},
                "tags": ["support", "unit-test"],
                "metadata": {"environment": "test"},
                "total_tokens": 120,
                "total_cost_usd": 0.000240,
                "duration_ms": 350,
                "started_at": now_iso,
                "ended_at": now_iso,
            }
        ],
        "spans": [
            {
                "id": span_id,
                "run_id": run_id,
                "name": "search_faq_tool",
                "span_type": "tool",
                "status": "completed",
                "input": {"query": "return policy"},
                "output": {"match": "30 days policy"},
                "prompt_tokens": 50,
                "completion_tokens": 70,
                "total_tokens": 120,
                "cost_usd": 0.000240,
                "duration_ms": 150,
                "started_at": now_iso,
                "ended_at": now_iso,
            }
        ],
    }

    response = await client.post(
        "/v1/ingest/spans",
        headers={"X-API-Key": TEST_API_KEY},
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["accepted_runs"] == 1
    assert data["accepted_spans"] == 1
    assert run_id in data["run_ids"]
    assert span_id in data["span_ids"]


@pytest.mark.asyncio
async def test_ingest_parent_child_nested_spans(client: AsyncClient) -> None:
    """Verify nested parent and child spans within the same batch persist accurately."""
    run_id = str(uuid.uuid4())
    parent_span_id = str(uuid.uuid4())
    child_span_id = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()

    payload = {
        "spans": [
            {
                "id": parent_span_id,
                "run_id": run_id,
                "name": "root_agent_span",
                "span_type": "agent",
                "started_at": now_iso,
            },
            {
                "id": child_span_id,
                "run_id": run_id,
                "parent_span_id": parent_span_id,
                "name": "nested_tool_call",
                "span_type": "tool",
                "started_at": now_iso,
            },
        ]
    }

    response = await client.post(
        "/api/v1/ingest/spans",
        headers={"X-API-Key": TEST_API_KEY},
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accepted_spans"] == 2
    assert child_span_id in data["span_ids"]
    assert parent_span_id in data["span_ids"]


@pytest.mark.asyncio
async def test_self_parenting_span_rejected(client: AsyncClient) -> None:
    """Verify a span that references itself as parent is rejected with 400 Bad Request."""
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()

    payload = {
        "spans": [
            {
                "id": span_id,
                "run_id": run_id,
                "parent_span_id": span_id,  # Self parent
                "name": "self_parenting_span",
                "span_type": "agent",
                "started_at": now_iso,
            }
        ]
    }

    response = await client.post(
        "/v1/ingest/spans",
        headers={"X-API-Key": TEST_API_KEY},
        json=payload,
    )
    assert response.status_code == 400
    assert "cannot reference itself as parent" in response.json()["detail"]


@pytest.mark.asyncio
async def test_nonexistent_external_parent_rejected(client: AsyncClient) -> None:
    """Verify references to non-existent parent spans are rejected with 400 Bad Request."""
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    ghost_parent_id = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()

    payload = {
        "spans": [
            {
                "id": span_id,
                "run_id": run_id,
                "parent_span_id": ghost_parent_id,
                "name": "orphan_span",
                "span_type": "tool",
                "started_at": now_iso,
            }
        ]
    }

    response = await client.post(
        "/v1/ingest/spans",
        headers={"X-API-Key": TEST_API_KEY},
        json=payload,
    )
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


@pytest.mark.asyncio
async def test_circular_parent_spans_rejected(client: AsyncClient) -> None:
    """Verify circular parent references within a batch are detected and rejected."""
    run_id = str(uuid.uuid4())
    span_a = str(uuid.uuid4())
    span_b = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()

    payload = {
        "spans": [
            {
                "id": span_a,
                "run_id": run_id,
                "parent_span_id": span_b,
                "name": "span_a",
                "span_type": "tool",
                "started_at": now_iso,
            },
            {
                "id": span_b,
                "run_id": run_id,
                "parent_span_id": span_a,
                "name": "span_b",
                "span_type": "tool",
                "started_at": now_iso,
            },
        ]
    }

    response = await client.post(
        "/v1/ingest/spans",
        headers={"X-API-Key": TEST_API_KEY},
        json=payload,
    )
    assert response.status_code == 400
    assert "Circular parent-child reference detected" in response.json()["detail"]


@pytest.mark.asyncio
async def test_project_tenant_isolation(client: AsyncClient) -> None:
    """Verify an API key cannot write or modify runs belonging to another project."""
    run_id = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()

    # 1. Project A creates the run
    res_a = await client.post(
        "/v1/ingest/spans",
        headers={"X-API-Key": TEST_API_KEY},
        json={
            "runs": [{"id": run_id, "name": "Project A Run", "started_at": now_iso}],
            "spans": [],
        },
    )
    assert res_a.status_code == 200

    # 2. Project B attempts to write a span to Project A's run
    span_id = str(uuid.uuid4())
    res_b = await client.post(
        "/v1/ingest/spans",
        headers={"X-API-Key": OTHER_PROJECT_API_KEY},
        json={
            "spans": [
                {
                    "id": span_id,
                    "run_id": run_id,  # Owned by Project A
                    "name": "malicious_cross_project_span",
                    "span_type": "tool",
                    "started_at": now_iso,
                }
            ]
        },
    )
    assert res_b.status_code == 403
    assert "belongs to a different project" in res_b.json()["detail"]


@pytest.mark.asyncio
async def test_batch_size_limit_enforced(client: AsyncClient) -> None:
    """Verify batches exceeding MAX_BATCH_SIZE (500 items) are rejected with 400."""
    now_iso = datetime.now(UTC).isoformat()
    run_id = str(uuid.uuid4())

    # Create 501 spans
    oversized_spans = [
        {
            "id": str(uuid.uuid4()),
            "run_id": run_id,
            "name": f"span_{i}",
            "span_type": "tool",
            "started_at": now_iso,
        }
        for i in range(501)
    ]

    response = await client.post(
        "/v1/ingest/spans",
        headers={"X-API-Key": TEST_API_KEY},
        json={"spans": oversized_spans},
    )
    assert response.status_code == 400
    assert "exceeds maximum limit" in response.json()["detail"]


@pytest.mark.asyncio
async def test_malformed_payload_validation(client: AsyncClient) -> None:
    """Verify malformed payloads (e.g. invalid span_type or missing name) return 422."""
    now_iso = datetime.now(UTC).isoformat()
    payload = {
        "spans": [
            {
                "id": str(uuid.uuid4()),
                "run_id": str(uuid.uuid4()),
                "name": "",  # Empty name violates min_length=1
                "span_type": "invalid_type_xyz",  # Invalid enum value
                "started_at": now_iso,
            }
        ]
    }
    response = await client.post(
        "/v1/ingest/spans",
        headers={"X-API-Key": TEST_API_KEY},
        json=payload,
    )
    assert response.status_code == 422
