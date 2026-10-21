"""
TraceHarbor API — Health Check Endpoints
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, status

from app.core.config import settings

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
