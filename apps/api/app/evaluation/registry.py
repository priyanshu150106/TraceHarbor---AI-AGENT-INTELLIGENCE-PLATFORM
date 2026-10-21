"""
TraceHarbor API — Evaluator Registry
"""

from typing import Any

from app.evaluation.base import BaseEvaluator
from app.evaluation.llm_judge import LLMJudgeEvaluator
from app.evaluation.rule_evaluators import (
    CaseInsensitiveExactMatchEvaluator,
    ExactMatchEvaluator,
    JsonSchemaEvaluator,
    JsonValidEvaluator,
    LatencyThresholdEvaluator,
    OutputPresenceEvaluator,
    RegexMatchEvaluator,
    RequiredKeywordsEvaluator,
    RequiredToolCallEvaluator,
    TokenCostThresholdEvaluator,
)


class EvaluatorRegistry:
    """
    Registry for discovering and managing evaluation modules.
    Enables new evaluators to be added without modifying conditional blocks.
    """

    def __init__(self) -> None:
        self._evaluators: dict[str, BaseEvaluator] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        defaults = [
            ExactMatchEvaluator(),
            CaseInsensitiveExactMatchEvaluator(),
            RequiredKeywordsEvaluator(),
            RegexMatchEvaluator(),
            JsonValidEvaluator(),
            JsonSchemaEvaluator(),
            RequiredToolCallEvaluator(),
            LatencyThresholdEvaluator(),
            TokenCostThresholdEvaluator(),
            OutputPresenceEvaluator(),
            LLMJudgeEvaluator(),
        ]
        for ev in defaults:
            self.register(ev)

    def register(self, evaluator: BaseEvaluator) -> None:
        """Register an evaluator instance under its name."""
        self._evaluators[evaluator.name] = evaluator

    def get(self, name: str) -> BaseEvaluator | None:
        """Retrieve an evaluator by name."""
        return self._evaluators.get(name)

    def list_evaluators(self) -> list[dict[str, Any]]:
        """List all available evaluators and their descriptions."""
        return [
            {
                "name": ev.name,
                "version": ev.version,
                "description": ev.description,
            }
            for ev in self._evaluators.values()
        ]


# Singleton instance
evaluator_registry = EvaluatorRegistry()
