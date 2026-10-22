"""
Tests for Phase 4 Alert Rules, Evaluation Engine, SSRF Protection, and Notification Delivery
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.alerts.notifications import SSRFValidationError, validate_webhook_url
from app.tests.conftest import OTHER_PROJECT_API_KEY, TEST_API_KEY


@pytest.mark.asyncio
async def test_alert_rule_crud_lifecycle(client: AsyncClient) -> None:
    """Test creating, listing, updating, and deleting alert rules."""
    headers = {"X-API-Key": TEST_API_KEY}

    # 1. Create Rule
    create_payload = {
        "name": "High Error Rate Alert",
        "metric": "error_rate",
        "operator": ">",
        "threshold": 0.05,
        "window_minutes": 60,
        "channel": "in_app",
        "cooldown_minutes": 30,
    }
    res_create = await client.post("/v1/alerts/rules", json=create_payload, headers=headers)
    assert res_create.status_code == 201
    rule_data = res_create.json()
    assert rule_data["name"] == "High Error Rate Alert"
    assert rule_data["threshold"] == 0.05
    assert rule_data["is_active"] is True
    rule_id = rule_data["id"]

    # 2. List Rules
    res_list = await client.get("/v1/alerts/rules", headers=headers)
    assert res_list.status_code == 200
    rules = res_list.json()
    assert len(rules) >= 1
    assert any(r["id"] == rule_id for r in rules)

    # 3. Update Rule (Disable it and change threshold)
    res_patch = await client.patch(
        f"/v1/alerts/rules/{rule_id}",
        json={"threshold": 0.10, "is_active": False},
        headers=headers,
    )
    assert res_patch.status_code == 200
    patched = res_patch.json()
    assert patched["threshold"] == 0.10
    assert patched["is_active"] is False

    # 4. Delete Rule
    res_del = await client.delete(f"/v1/alerts/rules/{rule_id}", headers=headers)
    assert res_del.status_code == 200

    # Verify deleted
    res_list_after = await client.get("/v1/alerts/rules", headers=headers)
    assert res_list_after.status_code == 200
    assert not any(r["id"] == rule_id for r in res_list_after.json())


@pytest.mark.asyncio
async def test_alert_rule_validation(client: AsyncClient) -> None:
    """Test validation errors for invalid metrics, operators, channels, and thresholds."""
    headers = {"X-API-Key": TEST_API_KEY}

    # Unsupported metric
    res1 = await client.post(
        "/v1/alerts/rules",
        json={"name": "Bad Metric", "metric": "invented_metric", "threshold": 10},
        headers=headers,
    )
    assert res1.status_code == 422

    # Unsupported operator
    res2 = await client.post(
        "/v1/alerts/rules",
        json={"name": "Bad Op", "metric": "error_rate", "operator": "LIKE", "threshold": 0.1},
        headers=headers,
    )
    assert res2.status_code == 422

    # Webhook channel without URL
    res3 = await client.post(
        "/v1/alerts/rules",
        json={"name": "Missing URL", "metric": "error_rate", "channel": "webhook", "threshold": 0.1},
        headers=headers,
    )
    assert res3.status_code == 422


@pytest.mark.asyncio
async def test_alert_rule_tenant_isolation(client: AsyncClient) -> None:
    """Verify that Project A cannot access, modify, or delete Project B's alert rules."""
    # Create rule in Project 1
    res_create = await client.post(
        "/v1/alerts/rules",
        json={
            "name": "P1 Isolated Alert",
            "metric": "error_rate",
            "operator": ">",
            "threshold": 0.05,
            "channel": "in_app",
        },
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert res_create.status_code == 201
    rule_id = res_create.json()["id"]

    # Project 2 tries to patch Project 1's rule -> 404
    res_patch = await client.patch(
        f"/v1/alerts/rules/{rule_id}",
        json={"name": "Hijacked"},
        headers={"X-API-Key": OTHER_PROJECT_API_KEY},
    )
    assert res_patch.status_code == 404

    # Project 2 tries to delete Project 1's rule -> 404
    res_del = await client.delete(
        f"/v1/alerts/rules/{rule_id}",
        headers={"X-API-Key": OTHER_PROJECT_API_KEY},
    )
    assert res_del.status_code == 404


@pytest.mark.asyncio
async def test_alert_evaluation_and_cooldown(client: AsyncClient) -> None:
    """
    Test alert threshold triggering, history logging,
    and subsequent cooldown suppression.
    """
    headers = {"X-API-Key": TEST_API_KEY}
    now = datetime.now(UTC)

    # Ingest runs with 100% error rate (2 errors out of 2)
    payload = {
        "runs": [
            {
                "id": str(uuid.uuid4()),
                "name": "Agent",
                "status": "error",
                "started_at": (now - timedelta(minutes=10)).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Agent",
                "status": "error",
                "started_at": (now - timedelta(minutes=5)).isoformat(),
            },
        ],
        "spans": [],
    }
    await client.post("/v1/ingest/spans", json=payload, headers=headers)

    # Create rule: error_rate > 0.10 (cooldown: 60 mins)
    rule_res = await client.post(
        "/v1/alerts/rules",
        json={
            "name": "Error Spike Rule",
            "metric": "error_rate",
            "operator": ">",
            "threshold": 0.10,
            "window_minutes": 60,
            "cooldown_minutes": 60,
            "channel": "in_app",
        },
        headers=headers,
    )
    assert rule_res.status_code == 201
    rule_id = rule_res.json()["id"]

    # 1. Trigger evaluation -> Alert should fire!
    res_eval = await client.post("/v1/alerts/evaluate", headers=headers)
    assert res_eval.status_code == 200
    data = res_eval.json()
    assert data["rules_evaluated"] >= 1
    assert data["alerts_triggered"] >= 1
    assert any(r["rule_id"] == rule_id and r["triggered"] for r in data["results"])

    # 2. Check alert history has recorded the trigger
    res_hist = await client.get("/v1/alerts/history", headers=headers)
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert hist_data["total"] >= 1
    assert any(h["rule_id"] == rule_id and h["metric"] == "error_rate" for h in hist_data["items"])

    # 3. Evaluate again immediately -> should be suppressed by cooldown!
    res_eval2 = await client.post("/v1/alerts/evaluate", headers=headers)
    assert res_eval2.status_code == 200
    data2 = res_eval2.json()
    assert data2["cooldown_suppressed"] >= 1
    rule_res2 = next(r for r in data2["results"] if r["rule_id"] == rule_id)
    assert rule_res2["cooldown_active"] is True

    # 4. Test single rule endpoint without persisting history
    test_res = await client.post(f"/v1/alerts/test/{rule_id}", headers=headers)
    assert test_res.status_code == 200
    test_data = test_res.json()
    assert test_data["triggered"] is True


def test_ssrf_url_validation() -> None:
    """Test SSRF rejection of private, link-local, and loopback destinations."""
    with pytest.raises(SSRFValidationError, match="localhost/loopback"):
        validate_webhook_url("http://localhost:8000/webhook")

    with pytest.raises(SSRFValidationError, match="localhost/loopback"):
        validate_webhook_url("http://127.0.0.1:9000/hook")

    with pytest.raises(SSRFValidationError, match="cloud instance metadata"):
        validate_webhook_url("http://169.254.169.254/latest/meta-data")

    # Valid external HTTPS URL
    valid_url = "https://httpbin.org/post"
    assert validate_webhook_url(valid_url) == valid_url
