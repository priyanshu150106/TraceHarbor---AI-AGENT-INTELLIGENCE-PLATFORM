"""
TraceHarbor API — Evaluation Base Classes & Schemas
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal


def safe_truncate(val: Any, max_len: int = 500) -> Any:
    """
    Safely stringifies and truncates long values to protect DB and frontend payloads.
    Preserves small primitives (numbers, booleans, None) as-is.
    """
    if val is None:
        return None
    if isinstance(val, bool | int | float):
        return val

    # If it's a dict or list, format as JSON string first
    if isinstance(val, dict | list):
        try:
            val_str = json.dumps(val, default=str)
        except Exception:
            val_str = str(val)
    else:
        val_str = str(val)

    if len(val_str) > max_len:
        return val_str[:max_len] + f"... [truncated {len(val_str) - max_len} chars]"
    return val_str


@dataclass
class EvaluationResult:
    """
    Common result schema returned by every evaluator.
    """

    evaluator_name: str
    evaluator_version: str
    passed: bool
    outcome: Literal["pass", "fail", "error"]
    score: float  # Normalized numeric score (0.0 to 1.0)
    explanation: str
    expected_value: Any | None = None
    actual_value: Any | None = None
    severity: str | None = None  # critical, high, medium, low, info
    evidence: Any | None = None  # Redacted evidence snippet or details
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluator_name": self.evaluator_name,
            "evaluator_version": self.evaluator_version,
            "passed": self.passed,
            "outcome": self.outcome,
            "score": round(self.score, 4),
            "severity": self.severity,
            "explanation": self.explanation,
            "evidence": self.evidence,
            "expected_value": safe_truncate(self.expected_value),
            "actual_value": safe_truncate(self.actual_value),
            "timestamp": self.timestamp.isoformat(),
        }


class BaseEvaluator(ABC):
    """
    Modular evaluator abstract base class.
    All deterministic rule-based evaluators and LLM judges inherit from this class.
    """

    name: str = "base"
    version: str = "1.0"
    description: str = ""

    @abstractmethod
    async def evaluate(
        self,
        actual_output: Any,
        expected_output: Any = None,
        criteria: dict[str, Any] | None = None,
        run_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """
        Execute evaluation against agent output and context.

        :param actual_output: The final output produced by the agent.
        :param expected_output: Optional golden reference output.
        :param criteria: Optional criteria config (keywords, regex patterns, thresholds, schema).
        :param run_context: Optional execution metadata (spans, duration_ms, total_tokens, cost_usd).
        :return: EvaluationResult with pass/fail/error, score, and explanation.
        """
        pass
