"""
TraceHarbor API — Unit Tests for Rule-Based Evaluators
"""

import pytest

from app.evaluation.base import safe_truncate
from app.evaluation.registry import evaluator_registry
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


@pytest.mark.asyncio
async def test_exact_match_evaluator():
    ev = ExactMatchEvaluator()

    # Match string
    res = await ev.evaluate("Hello World", "Hello World")
    assert res.passed is True
    assert res.outcome == "pass"
    assert res.score == 1.0

    # Whitespace trimmed match
    res = await ev.evaluate("  Hello World  ", "Hello World")
    assert res.passed is True

    # Case mismatch fail
    res = await ev.evaluate("hello world", "Hello World")
    assert res.passed is False
    assert res.outcome == "fail"
    assert res.score == 0.0

    # Dict deep match
    res = await ev.evaluate({"a": 1, "b": [2, 3]}, {"a": 1, "b": [2, 3]})
    assert res.passed is True

    # Dict mismatch
    res = await ev.evaluate({"a": 1}, {"a": 2})
    assert res.passed is False

    # Missing expected output -> error
    res = await ev.evaluate("Hello", None)
    assert res.passed is False
    assert res.outcome == "error"
    assert "not provided" in res.explanation


@pytest.mark.asyncio
async def test_case_insensitive_exact_match_evaluator():
    ev = CaseInsensitiveExactMatchEvaluator()

    res = await ev.evaluate("HELLO WORLD", "hello world")
    assert res.passed is True
    assert res.outcome == "pass"
    assert res.score == 1.0

    res = await ev.evaluate("Hello", "Goodbye")
    assert res.passed is False
    assert res.outcome == "fail"
    assert res.score == 0.0

    # Missing expected output -> error
    res = await ev.evaluate("Hello", None)
    assert res.outcome == "error"


@pytest.mark.asyncio
async def test_required_keywords_evaluator():
    ev = RequiredKeywordsEvaluator()

    # All keywords present
    res = await ev.evaluate(
        actual_output="Customers can return items within 30 days for a full refund.",
        criteria={"required_keywords": ["30 days", "refund"]},
    )
    assert res.passed is True
    assert res.score == 1.0
    assert "All 2 required keywords matched" in res.explanation

    # Partial match
    res = await ev.evaluate(
        actual_output="Returns within 30 days only.",
        criteria={"required_keywords": ["30 days", "refund"]},
    )
    assert res.passed is False
    assert res.outcome == "fail"
    assert res.score == 0.5
    assert "Missing: refund" in res.explanation

    # Comma-separated string format
    res = await ev.evaluate(
        actual_output="Standard shipping is 3-5 days.",
        criteria={"required_keywords": "shipping, 3-5 days"},
    )
    assert res.passed is True

    # Empty keywords -> error
    res = await ev.evaluate("Some text", criteria={})
    assert res.outcome == "error"


@pytest.mark.asyncio
async def test_regex_match_evaluator():
    ev = RegexMatchEvaluator()

    # Valid regex match
    res = await ev.evaluate(
        actual_output="Order ID: TH-98214 confirmed.",
        criteria={"pattern": r"TH-\d{5}"},
    )
    assert res.passed is True
    assert res.score == 1.0

    # Regex mismatch
    res = await ev.evaluate(
        actual_output="Order ID: INVALID confirmed.",
        criteria={"pattern": r"TH-\d{5}"},
    )
    assert res.passed is False
    assert res.score == 0.0

    # Invalid regex syntax -> error
    res = await ev.evaluate(
        actual_output="Test text",
        criteria={"pattern": r"[a-z("},
    )
    assert res.passed is False
    assert res.outcome == "error"
    assert "invalid regex syntax" in res.explanation

    # ReDoS safety: pattern length limit exceeded
    long_pattern = "a" * 501
    res = await ev.evaluate("Text", criteria={"pattern": long_pattern})
    assert res.outcome == "error"
    assert "maximum safe length" in res.explanation

    # ReDoS safety: nested quantifiers rejected
    res = await ev.evaluate("Text", criteria={"pattern": r"(.*)*"})
    assert res.outcome == "error"
    assert "unsafe regex pattern" in res.explanation


@pytest.mark.asyncio
async def test_json_valid_evaluator():
    ev = JsonValidEvaluator()

    # Valid stringified JSON
    res = await ev.evaluate('{"status": "ok", "count": 42}')
    assert res.passed is True
    assert res.score == 1.0

    # Markdown wrapped JSON
    res = await ev.evaluate('```json\n{"status": "ok"}\n```')
    assert res.passed is True

    # Pre-parsed dict
    res = await ev.evaluate({"status": "ok"})
    assert res.passed is True

    # Malformed JSON
    res = await ev.evaluate('{"status": "unclosed"')
    assert res.passed is False
    assert res.outcome == "fail"
    assert "Malformed JSON" in res.explanation


@pytest.mark.asyncio
async def test_json_schema_evaluator():
    ev = JsonSchemaEvaluator()

    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0},
        },
        "required": ["name", "age"],
    }

    # Conforming output
    res = await ev.evaluate(
        actual_output={"name": "Alice", "age": 30},
        criteria={"json_schema": schema},
    )
    assert res.passed is True
    assert res.score == 1.0

    # Validation failure: missing required field
    res = await ev.evaluate(
        actual_output={"name": "Bob"},
        criteria={"json_schema": schema},
    )
    assert res.passed is False
    assert res.outcome == "fail"
    assert "Schema validation failed" in res.explanation

    # Validation failure: wrong type
    res = await ev.evaluate(
        actual_output={"name": "Charlie", "age": "thirty"},
        criteria={"json_schema": schema},
    )
    assert res.passed is False
    assert res.outcome == "fail"

    # Invalid schema definition -> error
    res = await ev.evaluate(
        actual_output={"name": "Dave"},
        criteria={"json_schema": {"type": "unknown_type"}},
    )
    assert res.outcome == "error"
    assert "invalid" in res.explanation.lower()


@pytest.mark.asyncio
async def test_required_tool_call_evaluator():
    ev = RequiredToolCallEvaluator()

    run_context = {
        "spans": [
            {"name": "knowledge_base_search", "span_type": "tool"},
            {"name": "llm_synthesis", "span_type": "llm"},
        ]
    }

    # Tool present
    res = await ev.evaluate(
        actual_output="Policy answer",
        criteria={"required_tool": "knowledge_base_search"},
        run_context=run_context,
    )
    assert res.passed is True
    assert res.score == 1.0

    # Tool missing
    res = await ev.evaluate(
        actual_output="Policy answer",
        criteria={"required_tool": "sql_executor"},
        run_context=run_context,
    )
    assert res.passed is False
    assert res.outcome == "fail"
    assert "Missing required tool calls: sql_executor" in res.explanation

    # Missing criteria -> error
    res = await ev.evaluate("Answer", criteria={}, run_context=run_context)
    assert res.outcome == "error"


@pytest.mark.asyncio
async def test_latency_threshold_evaluator():
    ev = LatencyThresholdEvaluator()

    # Latency within bounds
    res = await ev.evaluate(
        actual_output="Fast output",
        criteria={"max_latency_ms": 2000},
        run_context={"duration_ms": 150},
    )
    assert res.passed is True
    assert res.score == 1.0

    # Latency exceeded
    res = await ev.evaluate(
        actual_output="Slow output",
        criteria={"max_latency_ms": 500},
        run_context={"duration_ms": 1200},
    )
    assert res.passed is False
    assert res.score == 0.0
    assert "threshold exceeded" in res.explanation.lower()

    # Missing run duration in context -> error
    res = await ev.evaluate(
        actual_output="Output",
        criteria={"max_latency_ms": 500},
        run_context={},
    )
    assert res.outcome == "error"


@pytest.mark.asyncio
async def test_token_cost_threshold_evaluator():
    ev = TokenCostThresholdEvaluator()

    run_context = {"total_tokens": 150, "total_cost_usd": 0.00045}

    # Within bounds
    res = await ev.evaluate(
        actual_output="Output",
        criteria={"max_tokens": 500, "max_cost_usd": 0.005},
        run_context=run_context,
    )
    assert res.passed is True
    assert res.score == 1.0

    # Exceeded tokens
    res = await ev.evaluate(
        actual_output="Output",
        criteria={"max_tokens": 100},
        run_context=run_context,
    )
    assert res.passed is False
    assert "exceeded" in res.explanation.lower()


@pytest.mark.asyncio
async def test_output_presence_evaluator():
    ev = OutputPresenceEvaluator()

    # Normal text
    res = await ev.evaluate("Valid output text")
    assert res.passed is True

    # None output -> fail
    res = await ev.evaluate(None)
    assert res.passed is False
    assert res.outcome == "fail"

    # Empty string -> fail
    res = await ev.evaluate("   ")
    assert res.passed is False

    # Min length check
    res = await ev.evaluate("Short", criteria={"min_length": 10})
    assert res.passed is False

    # Max length check
    res = await ev.evaluate("This is too long for the limit", criteria={"max_length": 10})
    assert res.passed is False

    # Required dict keys
    res = await ev.evaluate({"status": "ok"}, criteria={"required_keys": ["status", "answer"]})
    assert res.passed is False
    assert "missing required keys: answer" in res.explanation.lower()


def test_safe_truncate():
    assert safe_truncate(None) is None
    assert safe_truncate(123) == 123
    assert safe_truncate(True) is True

    short_str = "hello"
    assert safe_truncate(short_str, max_len=10) == "hello"

    long_str = "a" * 100
    truncated = safe_truncate(long_str, max_len=20)
    assert len(truncated) < 100
    assert "... [truncated 80 chars]" in truncated


def test_evaluator_registry():
    ev_names = [e["name"] for e in evaluator_registry.list_evaluators()]
    assert "exact_match" in ev_names
    assert "required_keywords" in ev_names
    assert "regex_match" in ev_names
    assert "json_valid" in ev_names
    assert "json_schema" in ev_names
    assert "required_tool_call" in ev_names
    assert "latency_threshold" in ev_names
    assert "token_cost_threshold" in ev_names
    assert "output_presence" in ev_names
    assert "llm_judge" in ev_names
