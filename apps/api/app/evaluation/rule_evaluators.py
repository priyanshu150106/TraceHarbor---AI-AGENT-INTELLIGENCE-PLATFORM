"""
TraceHarbor API — Deterministic Rule-Based Evaluators

All evaluators operate without third-party LLM API keys.
They produce normalized numeric scores, explicit pass/fail/error classifications,
and detailed, human-readable explanations.
"""

import json
import re
from typing import Any

import jsonschema

from app.evaluation.base import BaseEvaluator, EvaluationResult, safe_truncate


def _normalize_text(val: Any) -> str:
    """Helper to convert value to string, extracting answer field if dict."""
    if val is None:
        return ""
    if isinstance(val, dict):
        # Extract common answer keys if present
        for key in ("answer", "result", "output", "response", "text"):
            if key in val and val[key] is not None:
                return str(val[key]).strip()
        try:
            return json.dumps(val, default=str)
        except Exception:
            return str(val).strip()
    return str(val).strip()


class ExactMatchEvaluator(BaseEvaluator):
    """
    Evaluates whether actual output matches expected output exactly (whitespace-trimmed).
    Supports strings, numbers, and deep dictionary/list equivalence.
    """

    name: str = "exact_match"
    version: str = "1.0"
    description: str = "Strict equality check against expected output"

    async def evaluate(
        self,
        actual_output: Any,
        expected_output: Any = None,
        criteria: dict[str, Any] | None = None,
        run_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        if expected_output is None:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="error",
                score=0.0,
                explanation="Evaluator error: expected_output was not provided for exact_match.",
                expected_value=None,
                actual_value=actual_output,
            )

        # Deep dict/list check
        if isinstance(expected_output, dict | list) and isinstance(actual_output, dict | list):
            matched = actual_output == expected_output
        else:
            norm_actual = _normalize_text(actual_output)
            norm_expected = _normalize_text(expected_output)
            matched = norm_actual == norm_expected

        score = 1.0 if matched else 0.0
        explanation = (
            "Actual output matches expected output exactly."
            if matched
            else f"Output mismatch: expected '{safe_truncate(expected_output, 80)}' but got '{safe_truncate(actual_output, 80)}'."
        )

        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=self.version,
            passed=matched,
            outcome="pass" if matched else "fail",
            score=score,
            explanation=explanation,
            expected_value=expected_output,
            actual_value=actual_output,
        )


class CaseInsensitiveExactMatchEvaluator(BaseEvaluator):
    """
    Evaluates whether actual output matches expected output ignoring casing and whitespace.
    """

    name: str = "case_insensitive_exact_match"
    version: str = "1.0"
    description: str = "Case-insensitive equality check against expected output"

    async def evaluate(
        self,
        actual_output: Any,
        expected_output: Any = None,
        criteria: dict[str, Any] | None = None,
        run_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        if expected_output is None:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="error",
                score=0.0,
                explanation="Evaluator error: expected_output was not provided for case_insensitive_exact_match.",
                expected_value=None,
                actual_value=actual_output,
            )

        norm_actual = _normalize_text(actual_output).lower()
        norm_expected = _normalize_text(expected_output).lower()
        matched = norm_actual == norm_expected

        score = 1.0 if matched else 0.0
        explanation = (
            "Actual output matches expected output (case-insensitive)."
            if matched
            else f"Case-insensitive mismatch: expected '{safe_truncate(expected_output, 80)}' but got '{safe_truncate(actual_output, 80)}'."
        )

        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=self.version,
            passed=matched,
            outcome="pass" if matched else "fail",
            score=score,
            explanation=explanation,
            expected_value=expected_output,
            actual_value=actual_output,
        )


class RequiredKeywordsEvaluator(BaseEvaluator):
    """
    Checks that all required keywords or phrases are present in the actual output.
    Computes a fractional score equal to matched_keywords / total_keywords.
    """

    name: str = "required_keywords"
    version: str = "1.0"
    description: str = "Verifies presence of required keywords or phrases in output"

    async def evaluate(
        self,
        actual_output: Any,
        expected_output: Any = None,
        criteria: dict[str, Any] | None = None,
        run_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        criteria = criteria or {}
        raw_keywords = criteria.get("required_keywords") or criteria.get("keywords")

        # Fallback to expected_output if it's a list
        if not raw_keywords and isinstance(expected_output, list):
            raw_keywords = expected_output
        elif not raw_keywords and isinstance(expected_output, str) and expected_output:
            raw_keywords = [expected_output]

        if not raw_keywords:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="error",
                score=0.0,
                explanation="Evaluator error: no required_keywords specified in criteria or expected_output.",
                expected_value=None,
                actual_value=actual_output,
            )

        if isinstance(raw_keywords, str):
            keywords = [k.strip() for k in raw_keywords.split(",") if k.strip()]
        elif isinstance(raw_keywords, list):
            keywords = [str(k).strip() for k in raw_keywords if str(k).strip()]
        else:
            keywords = []

        if not keywords:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="error",
                score=0.0,
                explanation="Evaluator error: required_keywords list is empty.",
                expected_value=raw_keywords,
                actual_value=actual_output,
            )

        text = _normalize_text(actual_output).lower()
        case_sensitive = criteria.get("case_sensitive", False)
        if case_sensitive:
            text = _normalize_text(actual_output)

        matched_list: list[str] = []
        missing_list: list[str] = []

        for kw in keywords:
            search_target = kw if case_sensitive else kw.lower()
            if search_target in text:
                matched_list.append(kw)
            else:
                missing_list.append(kw)

        total = len(keywords)
        matched_count = len(matched_list)
        score = matched_count / total if total > 0 else 0.0
        passed = matched_count == total

        if passed:
            explanation = f"All {total} required keywords matched: {', '.join(matched_list)}."
        else:
            explanation = (
                f"Matched {matched_count}/{total} keywords. "
                f"Missing: {', '.join(missing_list)}."
            )

        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=self.version,
            passed=passed,
            outcome="pass" if passed else "fail",
            score=score,
            explanation=explanation,
            expected_value=keywords,
            actual_value=actual_output,
        )


class RegexMatchEvaluator(BaseEvaluator):
    """
    Evaluates actual output against a regular expression pattern.
    Enforces regex safety bounds to prevent ReDoS / excessive execution.
    """

    name: str = "regex_match"
    version: str = "1.0"
    description: str = "Validates output format using safe regular expression matching"

    MAX_PATTERN_LENGTH = 500

    async def evaluate(
        self,
        actual_output: Any,
        expected_output: Any = None,
        criteria: dict[str, Any] | None = None,
        run_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        criteria = criteria or {}
        pattern = (
            criteria.get("pattern")
            or criteria.get("regex_pattern")
            or (expected_output if isinstance(expected_output, str) else None)
        )

        if not pattern:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="error",
                score=0.0,
                explanation="Evaluator error: regex pattern was not specified.",
                expected_value=None,
                actual_value=actual_output,
            )

        if len(pattern) > self.MAX_PATTERN_LENGTH:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="error",
                score=0.0,
                explanation=f"Evaluator error: regex pattern exceeds maximum safe length ({len(pattern)} > {self.MAX_PATTERN_LENGTH}).",
                expected_value=pattern,
                actual_value=actual_output,
            )

        # Check for dangerous catastrophic backtracking patterns
        if "(.*)*" in pattern or "(.+)+" in pattern or "([a-zA-Z]+)*" in pattern:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="error",
                score=0.0,
                explanation="Evaluator error: rejected potentially unsafe regex pattern with nested quantifiers (ReDoS risk).",
                expected_value=pattern,
                actual_value=actual_output,
            )

        try:
            compiled = re.compile(pattern, re.IGNORECASE if criteria.get("ignore_case", True) else 0)
        except re.error as e:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="error",
                score=0.0,
                explanation=f"Evaluator error: invalid regex syntax: {e}",
                expected_value=pattern,
                actual_value=actual_output,
            )

        text = _normalize_text(actual_output)
        match = compiled.search(text)
        matched = bool(match)

        explanation = (
            f"Pattern r'{pattern}' successfully matched output."
            if matched
            else f"Pattern r'{pattern}' did not match output: '{safe_truncate(text, 80)}'."
        )

        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=self.version,
            passed=matched,
            outcome="pass" if matched else "fail",
            score=1.0 if matched else 0.0,
            explanation=explanation,
            expected_value=pattern,
            actual_value=actual_output,
        )


class JsonValidEvaluator(BaseEvaluator):
    """
    Validates whether the agent output is structurally valid JSON.
    """

    name: str = "json_valid"
    version: str = "1.0"
    description: str = "Checks whether output can be parsed as valid JSON"

    async def evaluate(
        self,
        actual_output: Any,
        expected_output: Any = None,
        criteria: dict[str, Any] | None = None,
        run_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        if isinstance(actual_output, dict | list):
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=True,
                outcome="pass",
                score=1.0,
                explanation="Output is already structured JSON (dict/list).",
                expected_value="valid JSON",
                actual_value=actual_output,
            )

        if not isinstance(actual_output, str):
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="fail",
                score=0.0,
                explanation=f"Output is of type {type(actual_output).__name__}, not valid JSON string.",
                expected_value="valid JSON",
                actual_value=actual_output,
            )

        text = actual_output.strip()
        # Handle markdown ```json code blocks if present
        if text.startswith("```json") and text.endswith("```"):
            text = text[7:-3].strip()
        elif text.startswith("```") and text.endswith("```"):
            text = text[3:-3].strip()

        try:
            json.loads(text)
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=True,
                outcome="pass",
                score=1.0,
                explanation="Output parsed successfully as valid JSON.",
                expected_value="valid JSON",
                actual_value=actual_output,
            )
        except json.JSONDecodeError as e:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="fail",
                score=0.0,
                explanation=f"Malformed JSON syntax at line {e.lineno}, col {e.colno}: {e.msg}.",
                expected_value="valid JSON",
                actual_value=actual_output,
            )


class JsonSchemaEvaluator(BaseEvaluator):
    """
    Validates agent output against a provided JSON Schema specification using the jsonschema library.
    """

    name: str = "json_schema"
    version: str = "1.0"
    description: str = "Validates structured JSON output against a JSON Schema"

    async def evaluate(
        self,
        actual_output: Any,
        expected_output: Any = None,
        criteria: dict[str, Any] | None = None,
        run_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        criteria = criteria or {}
        schema = criteria.get("json_schema") or criteria.get("schema")

        if not schema or not isinstance(schema, dict):
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="error",
                score=0.0,
                explanation="Evaluator error: criteria.json_schema must be a valid dictionary specification.",
                expected_value=None,
                actual_value=actual_output,
            )

        # Parse actual_output if string
        data_to_validate = actual_output
        if isinstance(actual_output, str):
            text = actual_output.strip()
            if text.startswith("```json") and text.endswith("```"):
                text = text[7:-3].strip()
            elif text.startswith("```") and text.endswith("```"):
                text = text[3:-3].strip()
            try:
                data_to_validate = json.loads(text)
            except json.JSONDecodeError as e:
                return EvaluationResult(
                    evaluator_name=self.name,
                    evaluator_version=self.version,
                    passed=False,
                    outcome="fail",
                    score=0.0,
                    explanation=f"Cannot validate schema: output is not valid JSON ({e.msg}).",
                    expected_value=schema,
                    actual_value=actual_output,
                )

        try:
            jsonschema.validate(instance=data_to_validate, schema=schema)
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=True,
                outcome="pass",
                score=1.0,
                explanation="Output conforms fully to JSON Schema.",
                expected_value=schema,
                actual_value=actual_output,
            )
        except jsonschema.exceptions.SchemaError as e:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="error",
                score=0.0,
                explanation=f"Evaluator error: provided JSON Schema is invalid: {e.message}",
                expected_value=schema,
                actual_value=actual_output,
            )
        except jsonschema.exceptions.ValidationError as e:
            path_str = "/".join(str(p) for p in e.path) or "root"
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="fail",
                score=0.0,
                explanation=f"Schema validation failed at '{path_str}': {e.message}.",
                expected_value=schema,
                actual_value=actual_output,
            )


class RequiredToolCallEvaluator(BaseEvaluator):
    """
    Validates that one or more specific tools were executed during the agent run.
    Inspects run_context spans or output metadata.
    """

    name: str = "required_tool_call"
    version: str = "1.0"
    description: str = "Checks whether expected tool span was invoked during execution"

    async def evaluate(
        self,
        actual_output: Any,
        expected_output: Any = None,
        criteria: dict[str, Any] | None = None,
        run_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        criteria = criteria or {}
        required = criteria.get("required_tool") or criteria.get("required_tools")

        if not required:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="error",
                score=0.0,
                explanation="Evaluator error: criteria.required_tool was not specified.",
                expected_value=None,
                actual_value=actual_output,
            )

        if isinstance(required, str):
            required_tools = [required.strip()]
        else:
            required_tools = [str(t).strip() for t in required if str(t).strip()]

        run_context = run_context or {}
        spans = run_context.get("spans") or []

        # Collect tool names called
        called_tools: set[str] = set()
        for span in spans:
            span_type = span.get("span_type") if isinstance(span, dict) else getattr(span, "span_type", None)
            name = span.get("name") if isinstance(span, dict) else getattr(span, "name", None)
            if span_type == "tool" and name:
                called_tools.add(name)

        # Also check if tool calls are present in actual_output or run_context
        if "tool_calls" in run_context and isinstance(run_context["tool_calls"], list):
            for tc in run_context["tool_calls"]:
                called_tools.add(str(tc))

        if isinstance(actual_output, dict) and "tool_calls" in actual_output:
            for tc in actual_output["tool_calls"]:
                called_tools.add(str(tc))

        matched_tools = [t for t in required_tools if t in called_tools]
        missing_tools = [t for t in required_tools if t not in called_tools]

        total = len(required_tools)
        matched_count = len(matched_tools)
        score = matched_count / total if total > 0 else 0.0
        passed = matched_count == total

        if passed:
            explanation = f"All required tools executed: {', '.join(matched_tools)}."
        else:
            explanation = (
                f"Missing required tool calls: {', '.join(missing_tools)}. "
                f"Tools actually executed: {', '.join(called_tools) if called_tools else 'None'}."
            )

        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=self.version,
            passed=passed,
            outcome="pass" if passed else "fail",
            score=score,
            explanation=explanation,
            expected_value=required_tools,
            actual_value=list(called_tools),
        )


class LatencyThresholdEvaluator(BaseEvaluator):
    """
    Checks whether run execution latency was within acceptable thresholds (e.g., < 2000 ms).
    """

    name: str = "latency_threshold"
    version: str = "1.0"
    description: str = "Validates that execution duration does not exceed threshold"

    async def evaluate(
        self,
        actual_output: Any,
        expected_output: Any = None,
        criteria: dict[str, Any] | None = None,
        run_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        criteria = criteria or {}
        max_latency_ms = criteria.get("max_latency_ms")

        if max_latency_ms is None:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="error",
                score=0.0,
                explanation="Evaluator error: criteria.max_latency_ms threshold was not specified.",
                expected_value=None,
                actual_value=actual_output,
            )

        run_context = run_context or {}
        duration_ms = run_context.get("duration_ms")

        if duration_ms is None:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="error",
                score=0.0,
                explanation="Evaluator error: execution duration_ms was not recorded in run_context.",
                expected_value=f"<= {max_latency_ms} ms",
                actual_value=None,
            )

        passed = duration_ms <= max_latency_ms
        score = 1.0 if passed else max(0.0, round(1.0 - (duration_ms - max_latency_ms) / max_latency_ms, 2))

        explanation = (
            f"Execution completed in {duration_ms} ms (threshold <= {max_latency_ms} ms)."
            if passed
            else f"Latency threshold exceeded: execution took {duration_ms} ms (threshold <= {max_latency_ms} ms)."
        )

        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=self.version,
            passed=passed,
            outcome="pass" if passed else "fail",
            score=score,
            explanation=explanation,
            expected_value=f"<= {max_latency_ms} ms",
            actual_value=f"{duration_ms} ms",
        )


class TokenCostThresholdEvaluator(BaseEvaluator):
    """
    Validates that token consumption or financial cost does not exceed budget thresholds.
    """

    name: str = "token_cost_threshold"
    version: str = "1.0"
    description: str = "Checks whether token count or USD cost stays within budget"

    async def evaluate(
        self,
        actual_output: Any,
        expected_output: Any = None,
        criteria: dict[str, Any] | None = None,
        run_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        criteria = criteria or {}
        max_tokens = criteria.get("max_tokens")
        max_cost_usd = criteria.get("max_cost_usd")

        if max_tokens is None and max_cost_usd is None:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="error",
                score=0.0,
                explanation="Evaluator error: neither max_tokens nor max_cost_usd specified in criteria.",
                expected_value=None,
                actual_value=actual_output,
            )

        run_context = run_context or {}
        actual_tokens = run_context.get("total_tokens", 0)
        actual_cost = float(run_context.get("total_cost_usd") or run_context.get("cost_usd") or 0.0)

        passed = True
        reasons: list[str] = []

        if max_tokens is not None:
            if actual_tokens > max_tokens:
                passed = False
                reasons.append(f"Tokens {actual_tokens} exceeded limit {max_tokens}")
            else:
                reasons.append(f"Tokens {actual_tokens} <= {max_tokens}")

        if max_cost_usd is not None:
            if actual_cost > float(max_cost_usd):
                passed = False
                reasons.append(f"Cost ${actual_cost:.5f} exceeded limit ${float(max_cost_usd):.5f}")
            else:
                reasons.append(f"Cost ${actual_cost:.5f} <= ${float(max_cost_usd):.5f}")

        explanation = "; ".join(reasons) + "."

        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=self.version,
            passed=passed,
            outcome="pass" if passed else "fail",
            score=1.0 if passed else 0.0,
            explanation=explanation,
            expected_value={"max_tokens": max_tokens, "max_cost_usd": max_cost_usd},
            actual_value={"total_tokens": actual_tokens, "total_cost_usd": actual_cost},
        )


class OutputPresenceEvaluator(BaseEvaluator):
    """
    Checks that the agent produced a non-empty output and satisfies optional structural bounds.
    """

    name: str = "output_presence"
    version: str = "1.0"
    description: str = "Verifies that output is present, non-empty, and satisfies length criteria"

    async def evaluate(
        self,
        actual_output: Any,
        expected_output: Any = None,
        criteria: dict[str, Any] | None = None,
        run_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        if actual_output is None:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="fail",
                score=0.0,
                explanation="Output presence check failed: agent output is null/None.",
                expected_value="non-null output",
                actual_value=None,
            )

        text = _normalize_text(actual_output)
        if not text:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="fail",
                score=0.0,
                explanation="Output presence check failed: output is empty string.",
                expected_value="non-empty text",
                actual_value="",
            )

        criteria = criteria or {}
        min_length = criteria.get("min_length")
        max_length = criteria.get("max_length")

        if min_length is not None and len(text) < min_length:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="fail",
                score=0.0,
                explanation=f"Output length ({len(text)} chars) is below required minimum ({min_length} chars).",
                expected_value=f">= {min_length} chars",
                actual_value=f"{len(text)} chars",
            )

        if max_length is not None and len(text) > max_length:
            return EvaluationResult(
                evaluator_name=self.name,
                evaluator_version=self.version,
                passed=False,
                outcome="fail",
                score=0.0,
                explanation=f"Output length ({len(text)} chars) exceeds maximum allowed ({max_length} chars).",
                expected_value=f"<= {max_length} chars",
                actual_value=f"{len(text)} chars",
            )

        # Check required keys if dict
        required_keys = criteria.get("required_keys")
        if required_keys and isinstance(actual_output, dict):
            missing_keys = [k for k in required_keys if k not in actual_output]
            if missing_keys:
                return EvaluationResult(
                    evaluator_name=self.name,
                    evaluator_version=self.version,
                    passed=False,
                    outcome="fail",
                    score=0.0,
                    explanation=f"Output dictionary missing required keys: {', '.join(missing_keys)}.",
                    expected_value=required_keys,
                    actual_value=list(actual_output.keys()),
                )

        return EvaluationResult(
            evaluator_name=self.name,
            evaluator_version=self.version,
            passed=True,
            outcome="pass",
            score=1.0,
            explanation=f"Output is present and valid ({len(text)} characters).",
            expected_value="valid output",
            actual_value=safe_truncate(actual_output, 80),
        )
