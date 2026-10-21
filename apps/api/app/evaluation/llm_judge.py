"""
TraceHarbor API — Optional LLM-as-Judge Evaluator

Provides automated semantic judging using an LLM (e.g., GPT-4o-mini).
Evaluates correctness, helpfulness, groundedness, and tone using structured rubrics.

Safety & Resilience Contracts:
1. Provider keys remain server-side and are NEVER exposed to the frontend.
2. If no provider key is configured, the evaluator cleanly reports 'skipped / not configured'
   without failing the test suite or breaking deterministic pipelines.
3. Network timeouts (10s) and bounded retries (2 max) isolate external API hiccups.
4. Distinguishes transport/parsing errors (outcome='error') from actual agent failures (outcome='fail').
5. Transparently documents that LLM-as-a-judge scoring can suffer from stochasticity and position bias.
"""

import asyncio
import json
import logging
from typing import Any

from app.core.config import settings
from app.evaluation.base import BaseEvaluator, EvaluationResult, safe_truncate

logger = logging.getLogger(__name__)

# Standard evaluation rubrics
RUBRICS = {
    "correctness": (
        "Evaluate whether the actual answer is factually correct, complete, and aligns with the user query and expected output. "
        "Score 1.0 if completely correct, 0.5 if partially correct with minor inaccuracies, 0.0 if incorrect or contradictory."
    ),
    "helpfulness": (
        "Evaluate whether the answer is polite, clear, well-structured, and directly solves the user's issue. "
        "Score 1.0 for helpful and actionable responses, 0.0 for unhelpful or confusing responses."
    ),
    "groundedness": (
        "Evaluate whether the answer is strictly grounded in the reference knowledge/context and does not hallucinate facts. "
        "Score 1.0 if fully grounded, 0.0 if it hallucinates unsupported claims."
    ),
    "tone": (
        "Evaluate whether the agent maintains a courteous, professional, and empathetic tone suitable for customer support. "
        "Score 1.0 for courteous and professional tone, 0.0 for rude, abrupt, or unprofessional tone."
    ),
}


class LLMJudgeEvaluator(BaseEvaluator):
    """
    Provider-neutral LLM-as-a-Judge evaluator.
    Supports OpenAI-compatible API or in-memory deterministic mock for tests.
    """

    name: str = "llm_judge"
    version: str = "1.0"
    description: str = "Semantic LLM-based evaluation for correctness, helpfulness, groundedness, and tone"

    def __init__(self, provider: str | None = None, model: str | None = None) -> None:
        self.provider = provider or settings.llm_judge_provider
        self.model = model or settings.llm_judge_model

    def _get_api_key(self) -> str | None:
        if self.provider == "anthropic":
            return settings.anthropic_api_key
        return settings.openai_api_key

    async def evaluate(
        self,
        actual_output: Any,
        expected_output: Any = None,
        criteria: dict[str, Any] | None = None,
        run_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        criteria = criteria or {}
        rubric_name = criteria.get("rubric", "correctness").lower()
        pass_threshold = float(criteria.get("pass_threshold", 0.7))
        rubric_description = RUBRICS.get(rubric_name, RUBRICS["correctness"])

        api_key = self._get_api_key()

        # If provider is mock or no API key is configured, provide safe deterministic fallback
        if self.provider == "mock" or not api_key:
            return self._mock_or_skip_evaluation(
                actual_output=actual_output,
                expected_output=expected_output,
                rubric_name=rubric_name,
                pass_threshold=pass_threshold,
                api_key_present=bool(api_key),
            )

        # Real provider execution (OpenAI compatible)
        return await self._call_provider(
            actual_output=actual_output,
            expected_output=expected_output,
            rubric_name=rubric_name,
            rubric_description=rubric_description,
            pass_threshold=pass_threshold,
            api_key=api_key,
        )

    def _mock_or_skip_evaluation(
        self,
        actual_output: Any,
        expected_output: Any,
        rubric_name: str,
        pass_threshold: float,
        api_key_present: bool,
    ) -> EvaluationResult:
        """Deterministic fallback when no paid LLM provider is active."""
        if not api_key_present and self.provider != "mock":
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=f"{self.version} ({self.model})",
                passed=False,
                outcome="error",
                score=0.0,
                explanation=(
                    f"LLM Judge skipped: no API key configured for provider '{self.provider}'. "
                    "Configure OPENAI_API_KEY in backend environment to enable live LLM evaluation."
                ),
                expected_value=f"Rubric: {rubric_name} (threshold >= {pass_threshold})",
                actual_value=safe_truncate(actual_output, 80),
            )

        # Deterministic mock evaluator for unit tests
        actual_str = str(actual_output).lower()
        expected_str = str(expected_output or "").lower()

        # Mock score based on heuristic match
        if expected_str and expected_str in actual_str:
            score = 1.0
            explanation = f"Mock LLM Judge: answer contains reference key terms for rubric '{rubric_name}'."
            evidence = expected_str
        elif actual_str and not actual_str.startswith("error"):
            score = 0.85
            explanation = f"Mock LLM Judge: answer is well-structured and polite for rubric '{rubric_name}'."
            evidence = actual_str[:60]
        else:
            score = 0.2
            explanation = f"Mock LLM Judge: output failed quality criteria for rubric '{rubric_name}'."
            evidence = "N/A"

        passed = score >= pass_threshold
        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=f"{self.version}-mock",
            passed=passed,
            outcome="pass" if passed else "fail",
            score=score,
            explanation=f"[{rubric_name.upper()}] {explanation} Evidence: '{evidence}'",
            expected_value=f"Rubric: {rubric_name} (threshold >= {pass_threshold})",
            actual_value=safe_truncate(actual_output, 100),
        )

    async def _call_provider(
        self,
        actual_output: Any,
        expected_output: Any,
        rubric_name: str,
        rubric_description: str,
        pass_threshold: float,
        api_key: str,
    ) -> EvaluationResult:
        """Call external LLM provider with timeout and bounded retries."""
        import httpx

        prompt = (
            f"You are an impartial AI evaluation judge. Evaluate the following AI agent output.\n\n"
            f"Evaluation Rubric ({rubric_name}): {rubric_description}\n\n"
            f"Reference / Expected Output:\n{expected_output or 'N/A'}\n\n"
            f"Actual Agent Output:\n{actual_output}\n\n"
            f"Provide your evaluation in strict JSON format with the following keys:\n"
            f'{{"score": <float between 0.0 and 1.0>, "explanation": "<concise reason>", "evidence": "<quoted segment from output>"}}'
        )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an expert AI evaluator. Always respond in valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        # Bounded retries: 2 attempts with 10s timeout
        last_error = ""
        for _ in range(2):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                if resp.status_code != 200:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    await asyncio.sleep(0.5)
                    continue

                data = resp.json()
                raw_content = data["choices"][0]["message"]["content"]
                parsed = json.loads(raw_content)

                score = float(parsed.get("score", 0.0))
                explanation = parsed.get("explanation", "No explanation provided.")
                evidence = parsed.get("evidence", "")

                passed = score >= pass_threshold
                return EvaluationResult(
                    evaluator_name=self.name,
                    evaluator_version=f"{self.version} ({self.model})",
                    passed=passed,
                    outcome="pass" if passed else "fail",
                    score=score,
                    explanation=f"[{rubric_name.upper()} score: {score:.2f}] {explanation} (Evidence: '{evidence}')",
                    expected_value=f"Rubric: {rubric_name} (threshold >= {pass_threshold})",
                    actual_value=safe_truncate(actual_output, 100),
                )
            except Exception as e:
                last_error = str(e)
                await asyncio.sleep(0.5)

        # Provider failed after retries
        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=f"{self.version} ({self.model})",
            passed=False,
            outcome="error",
            score=0.0,
            explanation=f"LLM Judge API call failed after retries: {last_error}",
            expected_value=f"Rubric: {rubric_name}",
            actual_value=safe_truncate(actual_output, 80),
        )
