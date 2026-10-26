"""
TraceHarbor API — Reliability, Security, & Middleware Tests

Tests:
- Request correlation ID middleware (X-Request-ID propagation)
- Liveness (/healthz), Readiness (/readyz), and General Health (/health)
- Tenant security: production mode auth rejection in resolve_project_id
- SSRF URL validation safety rules
- Startup configuration validation
"""

import uuid

import pytest
from httpx import AsyncClient

from app.alerts.notifications import SSRFValidationError, validate_webhook_url
from app.core.config import settings
from app.main import _validate_startup_configuration


@pytest.mark.asyncio
async def test_correlation_id_middleware_generates_id(client: AsyncClient) -> None:
    """Verify that every response includes an X-Request-ID header when none was provided."""
    res = await client.get("/healthz")
    assert res.status_code == 200
    assert "x-request-id" in res.headers
    request_id = res.headers["x-request-id"]
    # Verify it is a valid UUID
    parsed = uuid.UUID(request_id)
    assert parsed.version == 4


@pytest.mark.asyncio
async def test_correlation_id_middleware_propagates_incoming_id(client: AsyncClient) -> None:
    """Verify that client-provided X-Request-ID is preserved and echoed back."""
    custom_id = "req_distributed_trace_abc123"
    res = await client.get("/healthz", headers={"X-Request-ID": custom_id})
    assert res.status_code == 200
    assert res.headers.get("x-request-id") == custom_id


@pytest.mark.asyncio
async def test_liveness_and_readiness_endpoints(client: AsyncClient) -> None:
    """Verify separate liveness and readiness probe semantics."""
    # Liveness probe (fast, no DB query)
    live_res = await client.get("/healthz")
    assert live_res.status_code == 200
    assert live_res.json() == {"status": "alive"}

    # Readiness probe (verifies database)
    ready_res = await client.get("/readyz")
    assert ready_res.status_code == 200
    ready_data = ready_res.json()
    assert ready_data["status"] == "ready"
    assert ready_data["checks"]["database"] == "ok"


@pytest.mark.asyncio
async def test_resolve_project_id_production_mode_rejects_unauthenticated(
    client: AsyncClient,
) -> None:
    """
    In production mode (debug=False), unauthenticated requests without
    an explicit project_id or API key MUST return HTTP 401 Unauthorized.
    """
    original_debug = settings.debug
    try:
        settings.debug = False

        # Attempt to access an endpoint that depends on resolve_project_id without API key
        res = await client.get("/v1/failures/overview")
        assert res.status_code == 401
        assert "API key or explicit project_id required" in res.json()["detail"]
    finally:
        settings.debug = original_debug


@pytest.mark.asyncio
async def test_resolve_project_id_dev_mode_falls_back(client: AsyncClient) -> None:
    """In development mode (debug=True), unauthenticated requests fall back to primary project."""
    original_debug = settings.debug
    try:
        settings.debug = True
        res = await client.get("/v1/failures/overview")
        assert res.status_code == 200
    finally:
        settings.debug = original_debug


def test_ssrf_validation_rejects_private_and_loopback_ips() -> None:
    """Verify SSRF validator blocks internal, private, loopback, and link-local ranges."""
    # Loopback
    with pytest.raises(SSRFValidationError, match="prohibited|blocked"):
        validate_webhook_url("http://127.0.0.1:8000/webhook")

    with pytest.raises(SSRFValidationError, match="prohibited|blocked"):
        validate_webhook_url("http://localhost:8000/webhook")

    # Cloud metadata service IP
    with pytest.raises(SSRFValidationError, match="metadata|prohibited|blocked"):
        validate_webhook_url("http://169.254.169.254/latest/meta-data/")

    # Non-HTTP schemes
    with pytest.raises(SSRFValidationError, match="scheme"):
        validate_webhook_url("file:///etc/passwd")

    with pytest.raises(SSRFValidationError, match="scheme"):
        validate_webhook_url("ftp://example.com/webhook")


def test_startup_configuration_validation_runs() -> None:
    """Verify startup validation runs without throwing exceptions on default config."""
    # Should not raise exception
    _validate_startup_configuration()


@pytest.mark.asyncio
async def test_unhandled_exception_sanitization(client: AsyncClient) -> None:
    """Verify that unhandled exceptions do not leak stack traces or secrets in non-debug mode."""
    from app.main import app

    @app.get("/test-unhandled-crash")
    async def crash_endpoint() -> None:
        raise RuntimeError("database credentials password=supersecret_leak_12345")

    original_debug = settings.debug
    try:
        settings.debug = False
        res = await client.get("/test-unhandled-crash", headers={"X-Request-ID": "test-crash-trace-1"})
        assert res.status_code == 500
        data = res.json()
        assert data["detail"] == "Internal server error"
        assert "supersecret_leak_12345" not in res.text
        assert data["request_id"] == "test-crash-trace-1"
        assert res.headers.get("x-request-id") == "test-crash-trace-1"
    finally:
        settings.debug = original_debug
