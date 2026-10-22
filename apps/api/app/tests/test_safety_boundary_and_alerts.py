"""
TraceHarbor API — Tests for Safe Agent Boundary, Timeouts, and Safety Alert Rules
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.alerts.service import AlertEvaluationService
from app.evaluation.agent_registry import AgentExecutionResult, BaseAgentAdapter
from app.models.alert import AlertRule
from app.models.dataset import Dataset
from app.models.project import Project
from app.models.safety import SafetyCampaign
from app.safety.runner import execute_agent_safely


class HangingTimeoutAgent(BaseAgentAdapter):
    name = "hanging_agent"
    version = "1.0"
    description = "Test agent that hangs indefinitely to verify timeout enforcement"

    async def execute(self, prompt_input: Any, config: dict[str, Any] | None = None) -> AgentExecutionResult:
        await asyncio.sleep(5.0)
        return AgentExecutionResult(
            output="Never reached",
            duration_ms=5000,
            total_tokens=0,
            total_cost_usd=Decimal("0.0"),
        )


class CrashingExceptionAgent(BaseAgentAdapter):
    name = "crashing_agent"
    version = "1.0"
    description = "Test agent that raises an unexpected exception"

    async def execute(self, prompt_input: Any, config: dict[str, Any] | None = None) -> AgentExecutionResult:
        raise RuntimeError("Simulated internal model server crash")


@pytest.mark.asyncio
async def test_safe_execution_boundary_timeout():
    adapter = HangingTimeoutAgent()
    # Configure 0.1s timeout
    result = await execute_agent_safely(
        adapter=adapter,
        prompt_input="Hello",
        config={"case_timeout_seconds": 0.1},
    )
    assert result.status == "timeout"
    assert "timed out" in (result.error or "").lower()
    assert result.output is None


@pytest.mark.asyncio
async def test_safe_execution_boundary_exception():
    adapter = CrashingExceptionAgent()
    result = await execute_agent_safely(
        adapter=adapter,
        prompt_input="Hello",
    )
    assert result.status == "error"
    assert "simulated internal model server crash" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_safe_execution_boundary_max_input_length():
    adapter = HangingTimeoutAgent()
    huge_input = "A" * 15000  # Exceeds 10,000 char safety limit
    result = await execute_agent_safely(
        adapter=adapter,
        prompt_input=huge_input,
    )
    assert result.status == "error"
    assert "exceeds maximum allowed safety benchmark size" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_safety_alert_metrics_evaluation(db_session):
    session = db_session
    # Get test project
    from sqlalchemy import select
    project = (await session.execute(select(Project))).scalars().first()
    assert project is not None

    # Seed completed dataset and campaign
    import uuid
    dataset = Dataset(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Alert Test Dataset",
        dataset_type="safety",
    )
    session.add(dataset)

    campaign = SafetyCampaign(
        id=uuid.uuid4(),
        project_id=project.id,
        dataset_id=dataset.id,
        name="Alert Evaluation Campaign",
        status="completed",
        agent_name="support_agent",
        agent_version="0.5-vulnerable",
        total_tests=10,
        passed_tests=4,
        failed_tests=6,
        critical_failures=3,
        safety_pass_rate=Decimal("0.4000"),
        created_at=datetime.now(UTC),
    )
    session.add(campaign)
    await session.commit()

    # Evaluate safety_pass_rate metric: observed should be 0.4000
    observed_pass_rate = await AlertEvaluationService.compute_metric(
        project_id=project.id,
        metric="safety_pass_rate",
        window_minutes=60,
        db=session,
    )
    assert observed_pass_rate == 0.4000

    # Evaluate safety_critical_failures metric: observed should be 3.0
    observed_crit = await AlertEvaluationService.compute_metric(
        project_id=project.id,
        metric="safety_critical_failures",
        window_minutes=60,
        db=session,
    )
    assert observed_crit == 3.0

    # Create alert rule: alert when safety_critical_failures > 0
    rule = AlertRule(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Critical Safety Failure Alert",
        metric="safety_critical_failures",
        operator=">",
        threshold=0.0,
        window_minutes=60,
        channel="in_app",
        is_active=True,
    )
    session.add(rule)
    await session.commit()

    eval_res = await AlertEvaluationService.evaluate_single_rule(rule=rule, db=session)
    assert eval_res.triggered is True
    assert eval_res.observed_value == 3.0
