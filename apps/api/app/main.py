"""
TraceHarbor API — Main Application Entrypoint
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.alerts import router as alerts_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.datasets import router as datasets_router
from app.api.v1.experiments import router as experiments_router
from app.api.v1.failures import router as failures_router
from app.api.v1.health import router as health_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.projects import router as projects_router
from app.api.v1.runs import router as runs_router
from app.api.v1.safety import router as safety_router
from app.api.v1.tasks import router as tasks_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import CorrelationIdMiddleware
from app.core.tasks import task_manager

logger = logging.getLogger("traceharbor.startup")


def _validate_startup_configuration() -> None:
    """
    Validate critical configuration at startup and emit warnings for
    insecure defaults. Does NOT prevent startup — only logs warnings
    so developers can fix them before deploying to production.
    """
    warnings: list[str] = []

    # JWT secret must not be the default placeholder
    if settings.jwt_secret == "change_me_generate_a_random_secret" and not settings.debug:
        warnings.append(
            "JWT_SECRET is set to the default placeholder. "
            "Generate a secure secret for production: "
            "python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    # CORS wildcard in production
    if not settings.debug:
        warnings.append(
            "CORS allow_origins=['*'] is configured. "
            "Restrict to specific origins in production."
        )

    # Database URL still has default password
    if "change_me_in_production" in settings.database_url and not settings.debug:
        warnings.append(
            "DATABASE_URL contains default development credentials. "
            "Change POSTGRES_PASSWORD for production."
        )

    for w in warnings:
        logger.warning("STARTUP_CONFIG_WARNING: %s", w)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager: initial setup and graceful shutdown."""
    setup_logging(log_level=settings.log_level)
    _validate_startup_configuration()
    logger.info(
        "TraceHarbor %s starting (debug=%s, log_level=%s)",
        settings.app_version,
        settings.debug,
        settings.log_level,
    )
    yield
    # Graceful shutdown
    logger.info("TraceHarbor shutting down gracefully")
    await task_manager.shutdown()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="TraceHarbor — AI Agent Observability, Evaluation, and Security Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Request Correlation ID Middleware (must be added before CORS)
app.add_middleware(CorrelationIdMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Health router at root level and at /api/v1
app.include_router(health_router)
app.include_router(health_router, prefix="/api/v1")

# Mount Trace Ingestion router at /v1/ingest and /api/v1/ingest
app.include_router(ingest_router, prefix="/v1/ingest")
app.include_router(ingest_router, prefix="/api/v1/ingest")

# Mount Runs, Analytics, Alerts, Projects, Datasets, Experiments, Safety, Failures, and Tasks routers at /v1 and /api/v1
for prefix in ("/v1", "/api/v1"):
    app.include_router(runs_router, prefix=prefix)
    app.include_router(analytics_router, prefix=prefix)
    app.include_router(alerts_router, prefix=prefix)
    app.include_router(projects_router, prefix=prefix)
    app.include_router(datasets_router, prefix=prefix)
    app.include_router(experiments_router, prefix=prefix)
    app.include_router(safety_router, prefix=prefix)
    app.include_router(failures_router, prefix=prefix)
    app.include_router(tasks_router, prefix=prefix)



@app.get("/", tags=["Root"])
async def root() -> JSONResponse:
    """Root endpoint welcoming users and providing documentation link."""
    return JSONResponse(
        content={
            "app": settings.app_name,
            "version": settings.app_version,
            "tagline": "Observe. Evaluate. Secure.",
            "docs_url": "/docs",
            "health_check": "/health",
        }
    )
