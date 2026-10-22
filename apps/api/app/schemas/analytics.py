"""
TraceHarbor API — Advanced Analytics Pydantic Schemas
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TimeseriesPoint(BaseModel):
    """Aggregated metrics for a single time bucket."""

    timestamp: datetime
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    error_rate: float = 0.0
    p50_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    eval_pass_rate: float | None = None


class AnalyticsTimeseriesResponse(BaseModel):
    """Time-series telemetry response for charts."""

    time_range: str = "7d"
    interval: str = "1d"
    points: list[TimeseriesPoint] = Field(default_factory=list)
    total_points: int = 0


class ModelUsageItem(BaseModel):
    """Breakdown metrics for a single LLM model."""

    model: str
    call_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_latency_ms: float = 0.0


class ModelsAnalyticsResponse(BaseModel):
    """Breakdown of LLM model usage across spans."""

    items: list[ModelUsageItem] = Field(default_factory=list)
    total_models: int = 0


class AgentUsageItem(BaseModel):
    """Comparison metrics for an agent and version."""

    agent_name: str
    agent_version: str
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    error_rate: float = 0.0
    avg_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    eval_pass_rate: float | None = None


class AgentsAnalyticsResponse(BaseModel):
    """Breakdown and comparison of agent versions."""

    items: list[AgentUsageItem] = Field(default_factory=list)
    total_agents: int = 0


class CostBreakdownItem(BaseModel):
    """Daily cost attribution record."""

    date: str
    agent_name: str
    model: str
    cost_usd: float = 0.0
    token_count: int = 0


class CostBreakdownResponse(BaseModel):
    """Detailed cost breakdown by date, agent, and model."""

    total_cost_usd: float = 0.0
    cost_reported_runs: int = 0
    unmetered_runs: int = 0
    by_agent: dict[str, float] = Field(default_factory=dict)
    by_model: dict[str, float] = Field(default_factory=dict)
    daily_breakdown: list[CostBreakdownItem] = Field(default_factory=list)
