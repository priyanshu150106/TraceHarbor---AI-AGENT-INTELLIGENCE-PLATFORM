"""
TraceHarbor API — Safety & Red-Teaming Pydantic Schemas
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

SUPPORTED_SAFETY_CATEGORIES = {
    "prompt_injection",
    "instruction_hierarchy",
    "sensitive_data",
    "unsafe_tool_use",
    "policy_boundary",
    "data_exfiltration",
    "jailbreak_refusal",
}

SUPPORTED_SEVERITIES = {"critical", "high", "medium", "low"}


class SafetyTestCaseCreate(BaseModel):
    """Schema for individual safety test case definition or import."""

    test_case_id: str = Field(..., min_length=1, max_length=100, description="Stable test case identifier (e.g. SEC-PI-001)")
    category: str = Field(..., description="Adversarial category")
    severity: str = Field(default="medium", description="Risk severity (critical, high, medium, low)")
    description: str = Field(..., min_length=1, max_length=500, description="Human-readable test purpose")
    adversarial_input: Any = Field(..., description="Adversarial attack prompt or payload dictionary")
    expected_safe_behavior: str = Field(..., min_length=1, max_length=1000, description="Safe behavior requirements (refusal, redaction, policy adherence)")
    evaluation_method: list[str] | str | None = Field(default=None, description="Optional explicit safety evaluator name(s)")
    tool_restrictions: dict[str, Any] | None = Field(default=None, description="Optional allowed/disallowed tool rules")
    tags: list[str] = Field(default_factory=list, description="Categorical tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Supplementary test parameters or synthetic canary values")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        clean = v.strip().lower().replace("-", "_")
        if clean not in SUPPORTED_SAFETY_CATEGORIES:
            raise ValueError(f"Unsupported category '{v}'. Supported: {sorted(SUPPORTED_SAFETY_CATEGORIES)}")
        return clean

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in SUPPORTED_SEVERITIES:
            raise ValueError(f"Unsupported severity '{v}'. Supported: {sorted(SUPPORTED_SEVERITIES)}")
        return clean


class SafetyDatasetCreateRequest(BaseModel):
    """Schema for creating a dedicated safety benchmark dataset."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    test_cases: list[SafetyTestCaseCreate] = Field(default_factory=list)


class SafetyCampaignCreateRequest(BaseModel):
    """Schema for launching a safety evaluation campaign against an approved agent."""

    dataset_id: uuid.UUID = Field(..., description="ID of the safety benchmark dataset")
    agent_name: str = Field(..., min_length=1, max_length=100, description="Target approved agent identifier")
    agent_version: str = Field(..., min_length=1, max_length=50, description="Target approved agent version")
    name: str = Field(..., min_length=1, max_length=100, description="Descriptive campaign title")
    description: str | None = Field(default=None, max_length=1000)
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional campaign configuration (case_timeout_seconds, enable_llm_judge)",
    )


class SafetyTestResultResponse(BaseModel):
    """Schema for individual test case outcome in a safety campaign."""

    id: uuid.UUID
    campaign_id: uuid.UUID
    test_case_id: uuid.UUID
    run_id: uuid.UUID | None = None
    stable_case_id: str
    category: str
    severity: str
    adversarial_input: Any
    agent_output: Any
    expected_safe_behavior: str | None = None
    passed: bool | None = None
    status: str
    error: str | None = None
    duration_ms: int | None = None
    evaluator_results: list[dict[str, Any]] = Field(default_factory=list)
    evidence: Any | None = None
    created_at: datetime


class SafetyCampaignSummaryResponse(BaseModel):
    """Summary schema for campaign listings."""

    id: uuid.UUID
    project_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_name: str | None = None
    name: str
    description: str | None = None
    status: str
    agent_name: str
    agent_version: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    errored_tests: int
    critical_failures: int
    safety_pass_rate: float | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime


class SafetyCampaignDetailResponse(SafetyCampaignSummaryResponse):
    """Full detail schema for a single campaign including breakdown and results."""

    config: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] | None = None
    category_scores: dict[str, Any] = Field(default_factory=dict)
    severity_summary: dict[str, Any] = Field(default_factory=dict)
    results: list[SafetyTestResultResponse] = Field(default_factory=list)


class SafetyCampaignListResponse(BaseModel):
    """Paginated list of safety campaigns."""

    items: list[SafetyCampaignSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SafetyOverviewResponse(BaseModel):
    """Aggregated safety overview metrics for dashboard."""

    total_campaigns: int
    overall_safety_pass_rate: float | None
    total_critical_failures: int
    recent_campaigns: list[SafetyCampaignSummaryResponse]
    category_breakdown: dict[str, Any]
    severity_breakdown: dict[str, Any]
