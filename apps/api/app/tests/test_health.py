"""
TraceHarbor API — Health Check Endpoint Tests
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_root_endpoint(client: AsyncClient) -> None:
    """Verify GET /health returns 200 OK and expected structure."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "TraceHarbor"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_v1_endpoint(client: AsyncClient) -> None:
    """Verify GET /api/v1/health returns 200 OK and expected structure."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "TraceHarbor"


@pytest.mark.asyncio
async def test_root_welcome_endpoint(client: AsyncClient) -> None:
    """Verify GET / returns 200 OK and basic API information."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "TraceHarbor"
    assert data["tagline"] == "Observe. Evaluate. Secure."
    assert data["docs_url"] == "/docs"
