"""
TraceHarbor API — Alert Rule & Alert History Pydantic Schemas
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

SUPPORTED_METRICS = {
    "error_rate",
    "p95_latency",
    "cost_usd",
    "eval_pass_rate",
    "regression_count",
}

SUPPORTED_OPERATORS = {">", ">=", "<", "<=", "=="}
SUPPORTED_CHANNELS = {"in_app", "webhook"}


class AlertRuleCreate(BaseModel):
    """Schema for creating a new alert rule."""

    name: str = Field(..., min_length=1, max_length=100)
    metric: str = Field(..., description="Target metric (error_rate, p95_latency, cost_usd, eval_pass_rate, regression_count)")
    operator: str = Field(default=">", description="Comparison operator (>, >=, <, <=, ==)")
    threshold: float = Field(..., description="Numerical threshold value")
    window_minutes: int = Field(default=60, ge=1, le=10080, description="Evaluation look-back window in minutes")
    channel: str = Field(default="in_app", description="Notification destination (in_app, webhook)")
    webhook_url: str | None = Field(default=None, description="Destination URL if channel is webhook")
    webhook_secret: str | None = Field(default=None, max_length=255, description="Optional secret for signing outbound webhook payloads")
    cooldown_minutes: int = Field(default=60, ge=0, le=10080, description="Minimum minutes between successive alerts")

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if v_clean not in SUPPORTED_METRICS:
            raise ValueError(f"Unsupported metric '{v}'. Supported: {sorted(SUPPORTED_METRICS)}")
        return v_clean

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        v_clean = v.strip()
        if v_clean not in SUPPORTED_OPERATORS:
            raise ValueError(f"Unsupported operator '{v}'. Supported: {sorted(SUPPORTED_OPERATORS)}")
        return v_clean

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if v_clean not in SUPPORTED_CHANNELS:
            raise ValueError(f"Unsupported channel '{v}'. Supported: {sorted(SUPPORTED_CHANNELS)}")
        return v_clean


class AlertRuleUpdate(BaseModel):
    """Schema for modifying an existing alert rule."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    metric: str | None = None
    operator: str | None = None
    threshold: float | None = None
    window_minutes: int | None = Field(default=None, ge=1, le=10080)
    is_active: bool | None = None
    channel: str | None = None
    webhook_url: str | None = None
    webhook_secret: str | None = None
    cooldown_minutes: int | None = Field(default=None, ge=0, le=10080)

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v_clean = v.strip().lower()
        if v_clean not in SUPPORTED_METRICS:
            raise ValueError(f"Unsupported metric '{v}'. Supported: {sorted(SUPPORTED_METRICS)}")
        return v_clean

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v_clean = v.strip()
        if v_clean not in SUPPORTED_OPERATORS:
            raise ValueError(f"Unsupported operator '{v}'. Supported: {sorted(SUPPORTED_OPERATORS)}")
        return v_clean

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v_clean = v.strip().lower()
        if v_clean not in SUPPORTED_CHANNELS:
            raise ValueError(f"Unsupported channel '{v}'. Supported: {sorted(SUPPORTED_CHANNELS)}")
        return v_clean


class AlertRuleResponse(BaseModel):
    """Public representation of an alert rule."""

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    metric: str
    operator: str
    threshold: float
    window_minutes: int
    is_active: bool
    channel: str
    webhook_url: str | None = None
    has_webhook_secret: bool = False
    cooldown_minutes: int
    last_triggered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AlertHistoryResponse(BaseModel):
    """Fired alert instance with observed values and delivery status."""

    id: uuid.UUID
    rule_id: uuid.UUID
    rule_name: str | None = None
    project_id: uuid.UUID
    metric: str
    metric_value: float
    threshold: float
    operator: str
    message: str
    status: str
    notification_status: str
    notification_error: str | None = None
    acknowledged: bool
    fired_at: datetime
    created_at: datetime


class AlertHistoryListResponse(BaseModel):
    """Paginated list of fired alert records."""

    items: list[AlertHistoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AlertEvaluationResult(BaseModel):
    """Single rule evaluation outcome."""

    rule_id: uuid.UUID
    rule_name: str
    metric: str
    observed_value: float
    threshold: float
    operator: str
    triggered: bool
    cooldown_active: bool
    notification_status: str | None = None
    message: str


class AlertEvaluationBatchResponse(BaseModel):
    """Batch evaluation response across all active rules."""

    rules_evaluated: int
    alerts_triggered: int
    cooldown_suppressed: int
    results: list[AlertEvaluationResult] = Field(default_factory=list)
