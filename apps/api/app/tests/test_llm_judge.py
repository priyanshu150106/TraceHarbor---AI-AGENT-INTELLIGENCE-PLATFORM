"""
TraceHarbor API — Unit Tests for LLM-as-Judge Evaluator
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.evaluation.llm_judge import LLMJudgeEvaluator


@pytest.mark.asyncio
async def test_llm_judge_mock_mode_passing():
    ev = LLMJudgeEvaluator(provider="mock")

    res = await ev.evaluate(
        actual_output="Customers can return items within 30 days of purchase for a full refund.",
        expected_output="Returns are accepted within 30 days.",
        criteria={"rubric": "correctness", "pass_threshold": 0.7},
    )
    assert res.passed is True
    assert res.outcome == "pass"
    assert res.score >= 0.7
    assert "Mock LLM Judge" in res.explanation


@pytest.mark.asyncio
async def test_llm_judge_mock_mode_failing():
    ev = LLMJudgeEvaluator(provider="mock")

    res = await ev.evaluate(
        actual_output="error: connection failed",
        expected_output="Returns are accepted within 30 days.",
        criteria={"rubric": "correctness", "pass_threshold": 0.7},
    )
    assert res.passed is False
    assert res.outcome == "fail"
    assert res.score < 0.7


@pytest.mark.asyncio
async def test_llm_judge_unconfigured_api_key():
    # Provider is openai, but api_key is None
    ev = LLMJudgeEvaluator(provider="openai")
    with patch.object(ev, "_get_api_key", return_value=None):
        res = await ev.evaluate(
            actual_output="Some agent output",
            expected_output="Expected text",
        )
        assert res.passed is False
        assert res.outcome == "error"
        assert "no API key configured" in res.explanation


@pytest.mark.asyncio
async def test_llm_judge_provider_call_success():
    ev = LLMJudgeEvaluator(provider="openai", model="gpt-4o-mini")

    mock_response_data = {
        "choices": [
            {
                "message": {
                    "content": '{"score": 0.95, "explanation": "The answer directly and accurately addresses the customer question.", "evidence": "within 30 days"}'
                }
            }
        ]
    }

    mock_client = AsyncMock()
    mock_post_resp = AsyncMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json = MagicMock(return_value=mock_response_data)
    mock_client.post.return_value = mock_post_resp
    mock_client.__aenter__.return_value = mock_client

    with (
        patch.object(ev, "_get_api_key", return_value="sk-fake-key-for-test"),
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        res = await ev.evaluate(
            actual_output="You have 30 days to return.",
            expected_output="30 days",
            criteria={"rubric": "correctness", "pass_threshold": 0.7},
        )

    assert res.passed is True
    assert res.score == 0.95
    assert "CORRECTNESS score: 0.95" in res.explanation
    assert "Evidence: 'within 30 days'" in res.explanation
