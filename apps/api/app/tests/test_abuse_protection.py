"""
TraceHarbor API — Public Demo Abuse Protections & Hardening Tests

Validates:
- Request payload size limit (HTTP 413)
- Bounded sliding-window rate limiting (HTTP 429, Retry-After header)
- Health probe rate limit exemption
- Structlog sensitive token and key redaction
- Safe read-only POST search (/v1/failures/search) under demo mode
- Scoped project listing (/v1/projects) in demo mode
- Production startup demo project validation
"""

import hashlib
import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config import settings
from app.core.logging import redact_sensitive_data
from app.core.rate_limit import (
    BoundedSlidingWindowLimiter,
    get_client_ip,
    is_valid_ip,
    rate_limiter,
)
from app.main import _validate_startup_configuration
from app.models.api_key import ApiKey
from app.models.project import Project
from app.models.user import User

DEMO_KEY_HASH = hashlib.sha256(b"th_demo_abuse_test_key").hexdigest()


@pytest.fixture
async def setup_demo_tenant(db_session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    """Create a dedicated synthetic demo tenant project and demo API key."""
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
async def test_max_request_body_size_blocks_oversized_payload(client: AsyncClient) -> None:
    """Requests exceeding max_request_body_bytes must return HTTP 413 Payload Too Large."""
    orig_max = settings.max_request_body_bytes
    try:
        # Temporarily set max body size to 1 KB for test
        settings.max_request_body_bytes = 1024

        large_payload = {"data": "x" * 2048}
        headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(str(large_payload))),
        }

        res = await client.post("/v1/failures/search", json=large_payload, headers=headers)
        assert res.status_code == 413
        assert "exceeds maximum permitted limit" in res.json()["detail"]
    finally:
        settings.max_request_body_bytes = orig_max


def test_bounded_rate_limiter_unit_enforcement() -> None:
    """Verify BoundedSlidingWindowLimiter tracks window, decrements remaining, and rejects overflow."""
    limiter = BoundedSlidingWindowLimiter(max_keys=10)
    test_key = "test_ip:192.168.1.100"

    # Allow 3 requests
    allowed, remaining, _ = limiter.check(test_key, max_requests=3, window_seconds=60)
    assert allowed is True
    assert remaining == 2

    allowed, remaining, _ = limiter.check(test_key, max_requests=3, window_seconds=60)
    assert allowed is True
    assert remaining == 1

    allowed, remaining, _ = limiter.check(test_key, max_requests=3, window_seconds=60)
    assert allowed is True
    assert remaining == 0

    # 4th request must be rejected
    allowed, remaining, reset_sec = limiter.check(test_key, max_requests=3, window_seconds=60)
    assert allowed is False
    assert remaining == 0
    assert reset_sec > 0


def test_bounded_rate_limiter_lru_memory_bound() -> None:
    """Verify limiter evicts oldest keys when max_keys bound is reached."""
    limiter = BoundedSlidingWindowLimiter(max_keys=3)

    limiter.check("ip:1", max_requests=5)
    limiter.check("ip:2", max_requests=5)
    limiter.check("ip:3", max_requests=5)
    assert len(limiter._store) == 3

    # Adding 4th key should evict "ip:1"
    limiter.check("ip:4", max_requests=5)
    assert len(limiter._store) == 3
    assert "ip:1" not in limiter._store
    assert "ip:4" in limiter._store


@pytest.mark.asyncio
async def test_rate_limit_middleware_enforces_429(client: AsyncClient) -> None:
    """Exceeding configured rate limit returns HTTP 429 with Retry-After header."""
    rate_limiter.reset()
    orig_enabled = settings.rate_limit_enabled
    orig_limit = settings.rate_limit_demo_per_minute

    try:
        settings.rate_limit_enabled = True
        settings.rate_limit_demo_per_minute = 3

        # First 3 requests succeed
        for _ in range(3):
            res = await client.get("/v1/runs")
            assert res.status_code != 429
            assert "X-RateLimit-Limit" in res.headers

        # 4th request hits 429 Too Many Requests
        res_blocked = await client.get("/v1/runs")
        assert res_blocked.status_code == 429
        assert "Rate limit exceeded" in res_blocked.json()["detail"]
        assert "Retry-After" in res_blocked.headers
        assert res_blocked.headers["X-RateLimit-Remaining"] == "0"
    finally:
        settings.rate_limit_enabled = orig_enabled
        settings.rate_limit_demo_per_minute = orig_limit
        rate_limiter.reset()


@pytest.mark.asyncio
async def test_health_probes_exempt_from_rate_limiting(client: AsyncClient) -> None:
    """Health probes (/health, /healthz, /readyz) must never be blocked by rate limiting."""
    rate_limiter.reset()
    orig_enabled = settings.rate_limit_enabled
    orig_limit = settings.rate_limit_demo_per_minute

    try:
        settings.rate_limit_enabled = True
        settings.rate_limit_demo_per_minute = 1  # strict limit of 1

        # Probe healthz 5 times; all must return 200
        for _ in range(5):
            res = await client.get("/healthz")
            assert res.status_code == 200
    finally:
        settings.rate_limit_enabled = orig_enabled
        settings.rate_limit_demo_per_minute = orig_limit
        rate_limiter.reset()


def test_log_redaction_sanitizes_credentials_and_tokens() -> None:
    """Structlog redaction processor must mask sensitive keys and token patterns."""
    raw_event: dict[str, Any] = {
        "event": "user_login_attempt",
        "api_key": "th_live_supersecretliveapikey999",
        "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token",
        "password": "my_secret_password_123",
        "nested": {
            "webhook_secret": "whsec_testsecret12345",
            "safe_field": "public_data",
        },
        "query_log": "Received request with key th_live_anothersecretkey in payload",
    }

    sanitized = redact_sensitive_data(None, "info", raw_event)

    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["authorization"] == "[REDACTED]"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["nested"]["webhook_secret"] == "[REDACTED]"
    assert sanitized["nested"]["safe_field"] == "public_data"
    assert "th_live_anothersecretkey" not in sanitized["query_log"]
    assert "[REDACTED]" in sanitized["query_log"]


@pytest.mark.asyncio
async def test_demo_mode_projects_scoped_to_demo_project_only(
    client: AsyncClient,
    setup_demo_tenant: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """In demo mode, /v1/projects must return ONLY the demo project, preventing tenant enumeration."""
    demo_id, _ = setup_demo_tenant
    orig_demo = settings.demo_mode
    orig_project = settings.demo_project_id

    try:
        settings.demo_mode = True
        settings.demo_project_id = str(demo_id)

        res = await client.get("/v1/projects")
        assert res.status_code == 200
        projects = res.json()
        assert len(projects) == 1
        assert projects[0]["id"] == str(demo_id)
        assert "key_hash" not in projects[0]
    finally:
        settings.demo_mode = orig_demo
        settings.demo_project_id = orig_project


@pytest.mark.asyncio
async def test_demo_mode_safe_post_search_allowed(
    client: AsyncClient,
    setup_demo_tenant: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """In demo mode, /v1/failures/search (safe read query via POST) must be allowed scoped to demo tenant."""
    demo_id, _ = setup_demo_tenant
    orig_demo = settings.demo_mode
    orig_project = settings.demo_project_id

    try:
        settings.demo_mode = True
        settings.demo_project_id = str(demo_id)

        # POST /v1/failures/search should not return 403
        res = await client.post(
            "/v1/failures/search",
            json={"query_text": "database timeout error", "limit": 5},
        )
        assert res.status_code == 200
        data = res.json()
        assert "results" in data
        assert "search_method" in data
    finally:
        settings.demo_mode = orig_demo
        settings.demo_project_id = orig_project


def test_startup_validation_rejects_malformed_demo_project_id() -> None:
    """Startup validation must raise ValueError if DEMO_PROJECT_ID is not a valid UUID."""
    orig_demo_id = settings.demo_project_id
    orig_origins = settings.cors_origins
    try:
        settings.cors_origins = ["https://traceharbor.vercel.app"]
        settings.demo_project_id = "invalid-not-a-uuid"
        with pytest.raises(ValueError, match="Invalid DEMO_PROJECT_ID UUID format"):
            _validate_startup_configuration()
    finally:
        settings.demo_project_id = orig_demo_id
        settings.cors_origins = orig_origins


def _build_request(headers: dict[str, str] | None = None, client_host: str = "127.0.0.1") -> Request:
    """Helper to build a Starlette Request with specific headers and peer client IP."""
    raw_headers = []
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode("latin1"), v.encode("latin1")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/runs",
        "headers": raw_headers,
        "client": (client_host, 54321),
    }
    return Request(scope)


def test_ip_validation_helper() -> None:
    """Verify is_valid_ip correctly validates IPv4 and IPv6 and rejects malformed values."""
    assert is_valid_ip("127.0.0.1") is True
    assert is_valid_ip("203.0.113.195") is True
    assert is_valid_ip("::1") is True
    assert is_valid_ip("2001:db8::1") is True

    # Invalid values
    assert is_valid_ip("999.999.999.999") is False
    assert is_valid_ip("not-an-ip") is False
    assert is_valid_ip("<script>alert(1)</script>") is False
    assert is_valid_ip("../../../etc/passwd") is False
    assert is_valid_ip("") is False


def test_get_client_ip_missing_forwarded_headers() -> None:
    """When no proxy headers are present, client IP defaults to direct peer IP."""
    req = _build_request(headers={}, client_host="198.51.100.22")
    assert get_client_ip(req) == "198.51.100.22"


def test_get_client_ip_valid_trusted_proxy_single_ip() -> None:
    """When peer is trusted, single valid IP in X-Forwarded-For is extracted."""
    req = _build_request(
        headers={"X-Forwarded-For": "203.0.113.45"},
        client_host="127.0.0.1",  # trusted proxy
    )
    assert get_client_ip(req) == "203.0.113.45"


def test_get_client_ip_multiple_ips_anti_spoofing() -> None:
    """
    When a malicious client sends forged IPs (e.g. '10.0.0.1, 203.0.113.88'),
    the reverse proxy appends the real client IP on the right.
    The rate limiter must pick the rightmost valid client IP, rejecting the spoofed IP.
    """
    req = _build_request(
        headers={"X-Forwarded-For": "10.0.0.1, 203.0.113.88"},
        client_host="127.0.0.1",
    )
    # 203.0.113.88 is the actual client IP appended by the reverse proxy
    assert get_client_ip(req) == "203.0.113.88"


def test_get_client_ip_untrusted_peer_ignores_forwarded_headers() -> None:
    """
    If a direct client connection arrives from an untrusted peer (not in trusted_proxies),
    X-Forwarded-For must be completely ignored to prevent arbitrary IP spoofing.
    """
    orig_trusted = settings.trusted_proxies
    orig_enabled = settings.proxy_headers_enabled
    try:
        settings.trusted_proxies = ["127.0.0.1"]
        settings.proxy_headers_enabled = False

        req = _build_request(
            headers={"X-Forwarded-For": "1.2.3.4"},
            client_host="198.51.100.77",  # Untrusted external client
        )
        # Must return the untrusted peer IP, NOT the spoofed 1.2.3.4 header!
        assert get_client_ip(req) == "198.51.100.77"
    finally:
        settings.trusted_proxies = orig_trusted
        settings.proxy_headers_enabled = orig_enabled


def test_get_client_ip_malicious_and_invalid_values_rejected() -> None:
    """Malformed or injection strings in X-Forwarded-For must be rejected, falling back to peer IP."""
    malicious_inputs = [
        "<script>alert(1)</script>",
        "../../etc/passwd",
        "' OR '1'='1",
        "999.888.777.666",
        "invalid_hostname.com",
    ]
    for bad_ip in malicious_inputs:
        req = _build_request(
            headers={"X-Forwarded-For": bad_ip},
            client_host="127.0.0.1",
        )
        assert get_client_ip(req) == "127.0.0.1"


def test_get_client_ip_x_real_ip_fallback() -> None:
    """X-Real-IP is used as a fallback if X-Forwarded-For is missing and peer is trusted."""
    req = _build_request(
        headers={"X-Real-IP": "198.51.100.99"},
        client_host="127.0.0.1",
    )
    assert get_client_ip(req) == "198.51.100.99"


def test_get_client_ip_cf_connecting_ip_precedence() -> None:
    """CF-Connecting-IP provided by Cloudflare / Render edge is trusted and takes precedence."""
    req = _build_request(
        headers={
            "CF-Connecting-IP": "203.0.113.77",
            "X-Forwarded-For": "1.1.1.1, 10.0.0.1",
        },
        client_host="127.0.0.1",
    )
    assert get_client_ip(req) == "203.0.113.77"


@pytest.mark.asyncio
async def test_chunked_streaming_request_body_size_limit(client: AsyncClient) -> None:
    """
    Requests streamed in chunks without Content-Length that exceed max_request_body_bytes
    must be aborted with HTTP 413 by the ASGI streaming middleware.
    """
    orig_max = settings.max_request_body_bytes
    try:
        # Set limit to 256 bytes
        settings.max_request_body_bytes = 256

        # Generator yielding 10 chunks of 50 bytes = 500 bytes (> 256 bytes)
        async def streaming_generator():
            for _ in range(10):
                yield b"x" * 50

        # Send chunked request (no Content-Length header)
        res = await client.post(
            "/v1/failures/search",
            content=streaming_generator(),
            headers={"Content-Type": "application/json"},
        )
        assert res.status_code == 413
        assert "exceeds maximum permitted limit" in res.json()["detail"]
    finally:
        settings.max_request_body_bytes = orig_max


@pytest.mark.asyncio
async def test_invalid_content_length_headers(client: AsyncClient) -> None:
    """Invalid Content-Length headers (negative or non-numeric) must be rejected with HTTP 400."""
    # Negative content length
    res_neg = await client.post(
        "/v1/failures/search",
        content=b"{}",
        headers={"Content-Type": "application/json", "Content-Length": "-10"},
    )
    assert res_neg.status_code == 400
    assert "Invalid negative Content-Length" in res_neg.json()["detail"]

    # Non-integer content length
    res_abc = await client.post(
        "/v1/failures/search",
        content=b"{}",
        headers={"Content-Type": "application/json", "Content-Length": "not-a-number"},
    )
    assert res_abc.status_code == 400
    assert "Invalid Content-Length header format" in res_abc.json()["detail"]

