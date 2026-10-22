"""
TraceHarbor API — Main Application Entrypoint
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.alerts import router as alerts_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.datasets import router as datasets_router
from app.api.v1.experiments import router as experiments_router
from app.api.v1.health import router as health_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.projects import router as projects_router
from app.api.v1.runs import router as runs_router
from app.api.v1.safety import router as safety_router
from app.core.config import settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager: initial setup and graceful shutdown."""
    setup_logging(log_level=settings.log_level)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="TraceHarbor — AI Agent Observability, Evaluation, and Security Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

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

# Mount Runs, Analytics, Alerts, Projects, Datasets, Experiments, and Safety routers at /v1 and /api/v1
for prefix in ("/v1", "/api/v1"):
    app.include_router(runs_router, prefix=prefix)
    app.include_router(analytics_router, prefix=prefix)
    app.include_router(alerts_router, prefix=prefix)
    app.include_router(projects_router, prefix=prefix)
    app.include_router(datasets_router, prefix=prefix)
    app.include_router(experiments_router, prefix=prefix)
    app.include_router(safety_router, prefix=prefix)



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
