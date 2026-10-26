"""
TraceHarbor API — Health Check Endpoints

Provides three distinct health endpoints:

- ``/health``  — Human-friendly status for dashboards and docs
- ``/healthz`` — Liveness probe: is the process alive? (fast, no deps)
- ``/readyz``  — Readiness probe: are essential dependencies reachable?
                  Checks PostgreSQL connectivity. Does NOT require optional
                  services (Redis, embedding providers) to be available.

Security: no secrets, database URLs, or internal config are exposed.
"""

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

logger = structlog.get_logger("traceharbor.health")

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    response_description="Returns the current operational status of the API",
)
async def health_check() -> dict[str, Any]:
    """
    Public health check endpoint.
    Used by orchestrators, container health checks, and uptime monitors.
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get(
    "/healthz",
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    response_description="Returns 200 if the process is running",
)
async def liveness() -> dict[str, str]:
    """
    Liveness probe for container orchestrators (Kubernetes, Docker, etc.).
    Returns immediately — does NOT check external dependencies.
    """
    return {"status": "alive"}


@router.get(
    "/readyz",
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    response_description="Returns 200 if essential dependencies are reachable",
)
async def readiness(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Readiness probe verifying that essential dependencies are usable.
    Checks PostgreSQL connectivity. Does NOT require optional services
    (Redis, embedding providers) to be available.

    Returns HTTP 503 if the database is unreachable.
    """
    checks: dict[str, str] = {}
    all_ok = True

    # Check database connectivity
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = "unreachable"
        all_ok = False
        logger.warning("readiness_check_failed", component="database", error=str(e))

    result: dict[str, Any] = {
        "status": "ready" if all_ok else "not_ready",
        "checks": checks,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if not all_ok:
        from fastapi.responses import JSONResponse

        return JSONResponse(content=result, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    return result
