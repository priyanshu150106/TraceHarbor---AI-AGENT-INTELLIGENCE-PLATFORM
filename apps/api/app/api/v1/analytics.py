"""
TraceHarbor API — Advanced Analytics & Operational Metrics Endpoints
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import AnalyticsService
from app.core.auth import resolve_project_id
from app.core.database import get_db
from app.schemas.analytics import (
    AgentsAnalyticsResponse,
    AnalyticsTimeseriesResponse,
    CostBreakdownResponse,
    ModelsAnalyticsResponse,
)
from app.schemas.runs import AnalyticsOverviewResponse

router = APIRouter(tags=["Analytics"])


@router.get(
    "/analytics/overview",
    response_model=AnalyticsOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Overview Analytics",
    response_description="Aggregated run volume, error rate, p50/p95 latency, tokens, cost, and eval pass rate",
)
async def get_overview_analytics(
    time_range: Annotated[str, Query(description="Look-back window ('24h', '7d', '30d', 'all')")] = "7d",
    agent_name: Annotated[str | None, Query(description="Filter by specific agent name")] = None,
    agent_version: Annotated[str | None, Query(description="Filter by specific agent version")] = None,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsOverviewResponse:
    """
    Return high-level operational metrics and recent runs for the active project.
    Returns zeroed metrics gracefully when no runs have been ingested yet.
    """
    if not project_id:
        return AnalyticsOverviewResponse(time_range=time_range)

    return await AnalyticsService.get_overview(
        project_id=project_id,
        db=db,
        time_range=time_range,
        agent_name=agent_name,
        agent_version=agent_version,
    )


@router.get(
    "/analytics/timeseries",
    response_model=AnalyticsTimeseriesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Time-Series Metrics",
    response_description="Bucketed volume, error rate, p50/p95 latency, tokens, and cost points",
)
async def get_timeseries_analytics(
    time_range: Annotated[str, Query(description="Look-back window ('24h', '7d', '30d')")] = "7d",
    agent_name: Annotated[str | None, Query(description="Filter by specific agent name")] = None,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsTimeseriesResponse:
    """
    Return continuous bucketed time-series telemetry points for charting.
    Empty or sparse periods are automatically padded with clean zero values.
    """
    if not project_id:
        return AnalyticsTimeseriesResponse(time_range=time_range)

    return await AnalyticsService.get_timeseries(
        project_id=project_id,
        db=db,
        time_range=time_range,
        agent_name=agent_name,
    )


@router.get(
    "/analytics/models",
    response_model=ModelsAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get LLM Model Usage Breakdown",
    response_description="Call counts, prompt/completion tokens, total cost, and average latency by model",
)
async def get_models_analytics(
    time_range: Annotated[str, Query(description="Look-back window ('24h', '7d', '30d')")] = "7d",
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> ModelsAnalyticsResponse:
    """
    Aggregate LLM model usage across spans belonging to the project.
    """
    if not project_id:
        return ModelsAnalyticsResponse()

    return await AnalyticsService.get_models(
        project_id=project_id,
        db=db,
        time_range=time_range,
    )


@router.get(
    "/analytics/agents",
    response_model=AgentsAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Agent Performance Comparison",
    response_description="Runs, error rates, p95 latency, tokens, and eval pass rates by agent version",
)
async def get_agents_analytics(
    time_range: Annotated[str, Query(description="Look-back window ('24h', '7d', '30d')")] = "7d",
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> AgentsAnalyticsResponse:
    """
    Compare performance, error rates, costs, and eval pass rates across agents and versions.
    """
    if not project_id:
        return AgentsAnalyticsResponse()

    return await AnalyticsService.get_agents(
        project_id=project_id,
        db=db,
        time_range=time_range,
    )


@router.get(
    "/analytics/cost-breakdown",
    response_model=CostBreakdownResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Cost Breakdown",
    response_description="Attribution of estimated LLM expenses by date, agent, and model",
)
async def get_cost_breakdown(
    time_range: Annotated[str, Query(description="Look-back window ('24h', '7d', '30d')")] = "7d",
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> CostBreakdownResponse:
    """
    Calculate cost attribution across agents, models, and daily intervals.
    """
    if not project_id:
        return CostBreakdownResponse()

    return await AnalyticsService.get_cost_breakdown(
        project_id=project_id,
        db=db,
        time_range=time_range,
    )
