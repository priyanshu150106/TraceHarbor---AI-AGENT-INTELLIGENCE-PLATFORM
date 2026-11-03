"""
TraceHarbor API — CORS Security & Middleware Tests

Tests covering:
1. Allowed configured origin receives Access-Control-Allow-Origin header
2. Unapproved origin is rejected / receives no CORS header
3. Multiple configured origins are properly respected
4. Missing production CORS configuration raises CorsConfigurationError at startup
5. Wildcard-origin ('*') rejection when credentials are enabled in production
6. Development behavior automatically permits localhost without explicit config
"""

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.middleware.cors import CORSMiddleware

from app.core.config import Settings
from app.core.cors import (
    CorsConfigurationError,
    resolve_cors_origins,
    validate_production_cors_at_startup,
    validate_single_origin,
)
from app.main import app


@pytest.mark.asyncio
async def test_cors_development_allows_localhost() -> None:
    """In development mode (debug=True), localhost origins are allowed by default."""
    dev_settings = Settings(debug=True, cors_origins=[])
    origins = resolve_cors_origins(dev_settings)
    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:3000" in origins


@pytest.mark.asyncio
async def test_cors_multiple_configured_origins() -> None:
    """Multiple origins configured via comma-separated string or list are supported."""
    settings = Settings(
        debug=False,
        cors_origins=["https://traceharbor.vercel.app", "https://staging.traceharbor.com"],
    )
    origins = resolve_cors_origins(settings)
    assert len(origins) == 2
    assert "https://traceharbor.vercel.app" in origins
    assert "https://staging.traceharbor.com" in origins


@pytest.mark.asyncio
async def test_cors_missing_production_configuration_raises() -> None:
    """In production mode (debug=False), missing CORS configuration raises an error at startup."""
    prod_settings = Settings(debug=False, cors_origins=[])
    with pytest.raises(CorsConfigurationError, match="CORS_ORIGINS must be explicitly configured"):
        validate_production_cors_at_startup(prod_settings)


@pytest.mark.asyncio
async def test_cors_wildcard_rejection() -> None:
    """Wildcard origin '*' is rejected when credentials are enabled."""
    with pytest.raises(CorsConfigurationError, match="Wildcard origin.*strictly prohibited"):
        validate_single_origin("*", allow_wildcard=False)


@pytest.mark.asyncio
async def test_cors_malformed_origin_rejection() -> None:
    """Malformed origins (missing scheme or trailing slash) are rejected."""
    with pytest.raises(CorsConfigurationError, match="Must begin with 'http://' or 'https://'"):
        validate_single_origin("traceharbor.vercel.app")

    with pytest.raises(CorsConfigurationError, match="Must not contain a trailing slash"):
        validate_single_origin("https://traceharbor.vercel.app/")


@pytest.mark.asyncio
async def test_cors_middleware_allowed_and_unapproved_origins() -> None:
    """
    Test actual Starlette/FastAPI CORS middleware execution against:
    - An allowed configured origin
    - An unapproved origin
    """
    # Create an app instance with specific origins configured
    test_settings = Settings(
        debug=False,
        cors_origins=["https://approved-portfolio.vercel.app"],
    )
    allowed = resolve_cors_origins(test_settings)
    assert allowed == ["https://approved-portfolio.vercel.app"]

    # Test live against app middleware
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @test_app.get("/test-endpoint")
    async def sample():
        return {"ok": True}

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Request from approved origin
        res_approved = await client.get(
            "/test-endpoint",
            headers={"Origin": "https://approved-portfolio.vercel.app"},
        )
        assert res_approved.status_code == 200
        assert res_approved.headers.get("access-control-allow-origin") == "https://approved-portfolio.vercel.app"
        assert res_approved.headers.get("access-control-allow-credentials") == "true"

        # 2. Request from unapproved origin
        res_unapproved = await client.get(
            "/test-endpoint",
            headers={"Origin": "https://malicious-attacker.com"},
        )
        assert res_unapproved.status_code == 200
        assert "access-control-allow-origin" not in res_unapproved.headers

        # 3. Preflight OPTIONS request from approved origin
        res_options = await client.options(
            "/test-endpoint",
            headers={
                "Origin": "https://approved-portfolio.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert res_options.status_code == 200
        assert res_options.headers.get("access-control-allow-origin") == "https://approved-portfolio.vercel.app"
