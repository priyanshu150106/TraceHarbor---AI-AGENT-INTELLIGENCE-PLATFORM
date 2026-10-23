"""
TraceHarbor API — Failure Event Normalizer

Extracts and normalizes failure events from existing data sources:
- Failed or errored agent runs
- Failed evaluation results (experiment results)
- Safety benchmark failures (safety test results)
- Tool execution failures and errors in trace spans

Idempotent: uses (source_type, source_id) unique constraint to prevent
duplicate failure events on repeated processing.
"""

import hashlib
import uuid
from datetime import datetime
from typing import Any

from app.failures.redaction import normalize_error_text, sanitize_error_summary


def _compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of normalized text for embedding deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_agent_info(metadata: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract agent name and version from run metadata."""
    agent_name = metadata.get("agent_name") or metadata.get("agent")
    agent_version = metadata.get("agent_version") or metadata.get("version")
    return agent_name, agent_version


def _categorize_error(error_text: str, source_type: str) -> str:
    """Derive a failure category from the error text and source type."""
    if not error_text:
        return "unknown"

    lower = error_text.lower()

    if source_type == "safety_test_result":
        return "safety_failure"

    if source_type == "experiment_result":
        return "eval_failure"

    # Check for timeout patterns
    if any(kw in lower for kw in ("timeout", "timed out", "deadline exceeded")):
        return "timeout"

    # Check for tool errors
    if any(kw in lower for kw in ("tool", "function call", "tool_call")):
        return "tool_error"

    return "runtime_error"


def _infer_severity(
    source_type: str,
    error_text: str,
    severity_hint: str | None = None,
) -> str:
    """Infer severity from source type and error characteristics."""
    if severity_hint and severity_hint in ("critical", "high", "medium", "low"):
        return severity_hint

    if source_type == "safety_test_result":
        return "high"

    lower = (error_text or "").lower()
    if any(kw in lower for kw in ("critical", "fatal", "panic", "segfault", "oom")):
        return "critical"
    if any(kw in lower for kw in ("timeout", "connection refused", "auth")):
        return "high"

    return "medium"


class FailureEventData:
    """
    Plain data object representing a normalized failure event
    ready for persistence. Not an ORM model — used as an intermediate
    representation before creating or updating FailureEvent records.
    """

    def __init__(
        self,
        project_id: uuid.UUID,
        source_type: str,
        source_id: uuid.UUID,
        error_text: str,
        occurred_at: datetime,
        run_id: uuid.UUID | None = None,
        trace_id: str | None = None,
        agent_name: str | None = None,
        agent_version: str | None = None,
        model_name: str | None = None,
        model_provider: str | None = None,
        failure_category: str | None = None,
        severity: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.project_id = project_id
        self.source_type = source_type
        self.source_id = source_id
        self.run_id = run_id
        self.trace_id = trace_id
        self.agent_name = agent_name
        self.agent_version = agent_version
        self.model_name = model_name
        self.model_provider = model_provider

        # Sanitize and normalize
        self.error_summary = sanitize_error_summary(error_text)
        self.normalized_text = normalize_error_text(error_text)
        self.content_hash = _compute_content_hash(self.normalized_text)

        # Classification
        self.failure_category = failure_category or _categorize_error(
            error_text, source_type
        )
        self.severity = _infer_severity(source_type, error_text, severity)

        self.occurred_at = occurred_at
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for ORM model creation."""
        return {
            "project_id": self.project_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "agent_version": self.agent_version,
            "model_name": self.model_name,
            "model_provider": self.model_provider,
            "failure_category": self.failure_category,
            "severity": self.severity,
            "error_summary": self.error_summary,
            "normalized_text": self.normalized_text,
            "content_hash": self.content_hash,
            "occurred_at": self.occurred_at,
            "failure_metadata": self.metadata,
        }


def normalize_run_failure(
    run_id: uuid.UUID,
    project_id: uuid.UUID,
    error: str,
    started_at: datetime,
    metadata: dict[str, Any] | None = None,
) -> FailureEventData:
    """Create a FailureEventData from a failed/errored Run."""
    meta = metadata or {}
    agent_name, agent_version = _extract_agent_info(meta)

    return FailureEventData(
        project_id=project_id,
        source_type="run",
        source_id=run_id,
        error_text=error,
        occurred_at=started_at,
        run_id=run_id,
        agent_name=agent_name,
        agent_version=agent_version,
        metadata={"run_status": "error"},
    )


def normalize_span_failure(
    span_id: uuid.UUID,
    run_id: uuid.UUID,
    project_id: uuid.UUID,
    error: str,
    span_type: str,
    span_name: str,
    model: str | None,
    started_at: datetime,
) -> FailureEventData:
    """Create a FailureEventData from a failed/errored Span."""
    return FailureEventData(
        project_id=project_id,
        source_type="span",
        source_id=span_id,
        error_text=error,
        occurred_at=started_at,
        run_id=run_id,
        model_name=model,
        failure_category="tool_error" if span_type == "tool" else None,
        metadata={"span_type": span_type, "span_name": span_name},
    )


def normalize_experiment_result_failure(
    result_id: uuid.UUID,
    project_id: uuid.UUID,
    error: str | None,
    status: str,
    experiment_name: str,
    agent_name: str,
    agent_version: str,
    run_id: uuid.UUID | None,
    created_at: datetime,
) -> FailureEventData:
    """Create a FailureEventData from a failed ExperimentResult."""
    error_text = error or f"Evaluation {status}: {experiment_name}"

    return FailureEventData(
        project_id=project_id,
        source_type="experiment_result",
        source_id=result_id,
        error_text=error_text,
        occurred_at=created_at,
        run_id=run_id,
        agent_name=agent_name,
        agent_version=agent_version,
        failure_category="eval_failure",
        metadata={
            "experiment_name": experiment_name,
            "result_status": status,
        },
    )


def normalize_safety_test_failure(
    result_id: uuid.UUID,
    project_id: uuid.UUID,
    error: str | None,
    category: str,
    severity: str,
    agent_name: str,
    agent_version: str,
    campaign_name: str,
    run_id: uuid.UUID | None,
    created_at: datetime,
) -> FailureEventData:
    """Create a FailureEventData from a failed SafetyTestResult."""
    error_text = error or f"Safety test failed: {category} ({severity})"

    return FailureEventData(
        project_id=project_id,
        source_type="safety_test_result",
        source_id=result_id,
        error_text=error_text,
        occurred_at=created_at,
        run_id=run_id,
        agent_name=agent_name,
        agent_version=agent_version,
        failure_category="safety_failure",
        severity=severity,
        metadata={
            "campaign_name": campaign_name,
            "safety_category": category,
        },
    )
