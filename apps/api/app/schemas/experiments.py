"""
TraceHarbor API — Experiment & Results Pydantic Schemas
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExperimentCreateRequest(BaseModel):
    """Schema for requesting a new agent experiment run."""

    name: str = Field(..., min_length=1, max_length=100, description="Experiment title or version label")
    dataset_id: uuid.UUID = Field(..., description="Target evaluation dataset identifier")
    agent_name: str = Field(..., min_length=1, max_length=100, description="Approved agent name (e.g. support_agent)")
    agent_version: str = Field(..., min_length=1, max_length=50, description="Approved agent version (e.g. 1.0, 2.0-improved, 0.9-buggy)")
    description: str | None = Field(None, description="Optional notes on prompts or model hyperparameters")
    config: dict[str, Any] = Field(default_factory=dict, description="Custom evaluation and execution parameters")


class ExperimentSummaryResponse(BaseModel):
    """Experiment summary row for listing."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_name: str | None = None
    name: str
    description: str | None
    status: str
    agent_name: str
    agent_version: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    errored_cases: int
    score: float | None = None
    pass_rate: float | None = None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


class ExperimentResultResponse(BaseModel):
    """Detailed evaluation result for one test case."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    experiment_id: uuid.UUID
    test_case_id: uuid.UUID
    run_id: uuid.UUID | None = None
    test_input: Any | None = None
    expected_output: Any | None = None
    actual_output: Any | None = None
    scores: dict[str, Any] = Field(default_factory=dict)
    passed: bool | None = None
    status: str
    error: str | None = None
    duration_ms: int | None = None
    evaluation_details: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class ExperimentDetailResponse(BaseModel):
    """Full experiment details including per-case evaluation results."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_name: str | None = None
    name: str
    description: str | None
    status: str
    agent_name: str
    agent_version: str
    config: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] | None = None
    total_cases: int
    passed_cases: int
    failed_cases: int
    errored_cases: int
    score: float | None = None
    pass_rate: float | None = None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
    results: list[ExperimentResultResponse] = Field(default_factory=list)


class ExperimentListResponse(BaseModel):
    """Paginated list of experiments."""

    items: list[ExperimentSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
