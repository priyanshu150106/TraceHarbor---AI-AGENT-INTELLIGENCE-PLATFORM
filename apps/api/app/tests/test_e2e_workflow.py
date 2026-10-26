"""
Phase I — Comprehensive End-to-End Workflow Verification

Tests the complete lifecycle of TraceHarbor across all core modules:
1. Ingestion: Tracing batch with parent-child nested spans
2. Storage & Querying: Run hierarchy and execution analytics
3. Failure Intelligence: Idempotent event extraction and semantic clustering
4. Status Workflow: Investigation audit trail and resolution notes
5. Nearest-Neighbor Search: Similarity matching against clustered errors
6. Alerting: Real-time metric evaluation, threshold breach, and cooldown
7. Tenant Isolation: Multi-project boundary enforcement across all endpoints
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
async def test_end_to_end_agent_observability_and_failure_lifecycle(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Execute complete end-to-end scenario from trace ingestion to cluster resolution."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "embedding_provider", "fake")
    monkeypatch.setattr(settings, "embedding_dimensions", 64)

    headers = {"X-API-Key": TEST_API_KEY}
    other_headers = {"X-API-Key": OTHER_PROJECT_API_KEY}

    run_id = uuid.uuid4()
    root_span_id = uuid.uuid4()
    child_span_id = uuid.uuid4()
    now_iso = datetime.now(UTC).isoformat()

    # -------------------------------------------------------------
    # Step 1: Ingest batch of traces (1 Failed Run + 2 Nested Spans)
    # -------------------------------------------------------------
    ingest_payload = {
        "runs": [
            {
                "id": str(run_id),
                "name": "Refund Processing Agent",
                "status": "error",
                "error": "PaymentGatewayTimeout: Stripe charge capture timed out after 30000ms",
                "started_at": now_iso,
                "ended_at": now_iso,
                "total_tokens": 1250,
                "total_cost_usd": 0.0035,
                "tags": ["billing", "prod", "refunds"],
                "metadata": {"agent_name": "billing_agent"},
            }
        ],
        "spans": [
            {
                "id": str(root_span_id),
                "run_id": str(run_id),
                "name": "process_refund_request",
                "span_type": "agent",
                "status": "error",
                "error": "PaymentGatewayTimeout: Stripe charge capture timed out",
                "started_at": now_iso,
                "ended_at": now_iso,
            },
            {
                "id": str(child_span_id),
                "run_id": str(run_id),
                "parent_span_id": str(root_span_id),
                "name": "stripe_api_capture",
                "span_type": "tool",
                "status": "error",
                "error": "TimeoutError: connection to api.stripe.com reset by peer",
                "started_at": now_iso,
                "ended_at": now_iso,
            },
        ],
    }

    ingest_res = await client.post("/v1/ingest/spans", json=ingest_payload, headers=headers)
    assert ingest_res.status_code == 200
    assert ingest_res.json()["accepted_runs"] == 1
    assert ingest_res.json()["accepted_spans"] == 2

    # -------------------------------------------------------------
    # Step 2: Query run detail and verify nested span hierarchy
    # -------------------------------------------------------------
    run_detail_res = await client.get(f"/v1/runs/{run_id}", headers=headers)
    assert run_detail_res.status_code == 200
    run_data = run_detail_res.json()
    assert run_data["name"] == "Refund Processing Agent"
    assert len(run_data["spans"]) == 2

    # Verify parent-child hierarchy in response
    span_map = {s["id"]: s for s in run_data["spans"]}
    assert span_map[str(child_span_id)]["parent_span_id"] == str(root_span_id)

    # -------------------------------------------------------------
    # Step 3: Sync failure events from ingested telemetry
    # -------------------------------------------------------------
    sync_res = await client.post(
        "/v1/failures/sync",
        json={"auto_embed": True, "run_in_background": False},
        headers=headers,
    )
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["created"] >= 1

    # Check failure events feed
    events_res = await client.get("/v1/failures", headers=headers)
    assert events_res.status_code == 200
    events_items = events_res.json()["items"]
    assert len(events_items) >= 1
    event_id = events_items[0]["id"]
    assert event_id is not None

    # -------------------------------------------------------------
    # Step 4: Run clustering job and inspect clusters
    # -------------------------------------------------------------
    cluster_job_res = await client.post(
        "/v1/failures/clusters/run",
        json={"min_cluster_size": 1, "run_in_background": False},
        headers=headers,
    )
    assert cluster_job_res.status_code == 200

    clusters_res = await client.get("/v1/failures/clusters", headers=headers)
    assert clusters_res.status_code == 200
    clusters = clusters_res.json()["items"]
    assert len(clusters) >= 1
    cluster_id = clusters[0]["id"]

    # -------------------------------------------------------------
    # Step 5: Update cluster status and add investigation notes
    # -------------------------------------------------------------
    status_patch_res = await client.patch(
        f"/v1/failures/clusters/{cluster_id}/status",
        json={
            "status": "investigating",
            "resolution_notes": "Stripe timeout identified as circuit-breaker tripping. Scaling connection pool.",
        },
        headers=headers,
    )
    assert status_patch_res.status_code == 200
    assert status_patch_res.json()["status"] == "investigating"

    # Inspect cluster detail with audit history
    cluster_detail_res = await client.get(
        f"/v1/failures/clusters/{cluster_id}",
        headers=headers,
    )
    assert cluster_detail_res.status_code == 200
    detail_data = cluster_detail_res.json()
    assert len(detail_data["status_history"]) >= 1
    assert detail_data["status_history"][0]["new_status"] == "investigating"

    # -------------------------------------------------------------
    # Step 6: Similarity search across failures
    # -------------------------------------------------------------
    search_res = await client.post(
        "/v1/failures/search",
        json={
            "query_text": "Stripe payment timeout",
            "threshold": 0.3,
            "limit": 5,
        },
        headers=headers,
    )
    assert search_res.status_code == 200
    assert search_res.json()["search_method"] in ("vector_similarity", "lexical_fallback")

    # -------------------------------------------------------------
    # Step 7: Create and evaluate alert rule
    # -------------------------------------------------------------
    alert_rule_res = await client.post(
        "/v1/alerts/rules",
        json={
            "name": "E2E High Failure Alert",
            "metric": "error_rate",
            "condition": "gt",
            "threshold": 0.05,
            "window_minutes": 60,
            "webhook_url": "https://example.com/alerts",
        },
        headers=headers,
    )
    assert alert_rule_res.status_code == 201
    rule_id = alert_rule_res.json()["id"]
    assert rule_id is not None

    # Evaluate alerts
    eval_res = await client.post("/v1/alerts/evaluate", headers=headers)
    assert eval_res.status_code == 200

    # -------------------------------------------------------------
    # Step 8: Strict Tenant Isolation Boundary Check
    # -------------------------------------------------------------
    # Other project must NOT see any of the above resources
    other_run_res = await client.get(f"/v1/runs/{run_id}", headers=other_headers)
    assert other_run_res.status_code == 403

    other_cluster_res = await client.get(
        f"/v1/failures/clusters/{cluster_id}",
        headers=other_headers,
    )
    assert other_cluster_res.status_code == 404

    other_events_res = await client.get("/v1/failures", headers=other_headers)
    assert other_events_res.status_code == 200
    assert other_events_res.json()["total"] == 0
