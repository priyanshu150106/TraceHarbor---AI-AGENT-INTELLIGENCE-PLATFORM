"""
TraceHarbor API — Safety Campaign Execution Runner & Safe Agent Boundary

Executes safety red-teaming benchmarks against approved agent adapters within
a strictly isolated execution boundary: per-case timeouts, input/output size limits,
synthetic tool mocks, and non-crashing exception handling.
"""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.evaluation.agent_registry import AgentExecutionResult, BaseAgentAdapter, agent_registry
from app.evaluation.base import EvaluationResult
from app.evaluation.registry import evaluator_registry
from app.models.run import Run
from app.models.safety import SafetyCampaign, SafetyTestResult
from app.models.span import Span
from app.models.test_case import TestCase
from app.safety.redaction import redact_sensitive_content

logger = logging.getLogger(__name__)

DEFAULT_CASE_TIMEOUT_SECONDS = 10
MAX_INPUT_LENGTH = 10000
MAX_OUTPUT_LENGTH = 50000


@asynccontextmanager
async def _get_session_scope():
    """Provides an AsyncSession that works in production and with test dependency overrides."""
    from app.core.database import async_session_factory, get_db
    from app.main import app

    if get_db in app.dependency_overrides:
        gen = app.dependency_overrides[get_db]()
        session = await anext(gen)
        try:
            yield session
        finally:
            with suppress(StopAsyncIteration, GeneratorExit):
                await anext(gen)
    else:
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


async def execute_agent_safely(
    adapter: BaseAgentAdapter,
    prompt_input: Any,
    config: dict[str, Any] | None = None,
) -> AgentExecutionResult:
    """
    Execute an approved agent adapter inside a strictly bounded, non-crashing wrapper.
    Enforces per-case timeouts, input-length validation, and output bounds.
    """
    config = config or {}
    timeout_sec = config.get("case_timeout_seconds", DEFAULT_CASE_TIMEOUT_SECONDS)

    # 1. Input length limit check
    input_str = str(prompt_input)
    if len(input_str) > MAX_INPUT_LENGTH:
        return AgentExecutionResult(
            output=None,
            duration_ms=0,
            total_tokens=0,
            total_cost_usd=Decimal("0.0"),
            error=f"Input exceeds maximum allowed safety benchmark size of {MAX_INPUT_LENGTH} characters.",
            status="error",
        )

    # 2. Bounded execution with timeout
    try:
        res = await asyncio.wait_for(
            adapter.execute(prompt_input=prompt_input, config=config),
            timeout=timeout_sec,
        )

        # 3. Output size limit enforcement
        output_str = str(res.output)
        if len(output_str) > MAX_OUTPUT_LENGTH:
            res.output = output_str[:MAX_OUTPUT_LENGTH] + "... [output truncated by safety boundary]"

        return res

    except TimeoutError:
        logger.warning(f"Agent '{adapter.name}' timed out after {timeout_sec}s during safety test.")
        return AgentExecutionResult(
            output=None,
            duration_ms=int(timeout_sec * 1000),
            total_tokens=0,
            total_cost_usd=Decimal("0.0"),
            error=f"Execution timed out after {timeout_sec} seconds.",
            status="timeout",
        )
    except Exception as e:
        logger.exception(f"Unhandled exception in agent '{adapter.name}': {e}")
        return AgentExecutionResult(
            output=None,
            duration_ms=0,
            total_tokens=0,
            total_cost_usd=Decimal("0.0"),
            error=f"Agent runtime exception: {e}",
            status="error",
        )


def _determine_evaluators(
    category: str,
    criteria: dict[str, Any],
    config: dict[str, Any],
) -> list[str]:
    """Resolve which deterministic safety evaluators should execute for a test case."""
    evaluators_to_run: list[str] = []

    # 1. Explicit evaluation method configured on test case
    if "evaluation_method" in criteria:
        method = criteria["evaluation_method"]
        if isinstance(method, list):
            evaluators_to_run.extend([str(m) for m in method])
        elif isinstance(method, str):
            evaluators_to_run.append(method)

    # 2. Inferred from threat category
    cat_lower = category.lower().replace("-", "_")
    if ("sensitive_data" in cat_lower or "data_exfiltration" in cat_lower) and "secret_leakage" not in evaluators_to_run:
        evaluators_to_run.append("secret_leakage")
    elif ("jailbreak" in cat_lower or "refusal" in cat_lower) and "required_refusal" not in evaluators_to_run:
        evaluators_to_run.append("required_refusal")
    elif ("prompt_injection" in cat_lower or "instruction_hierarchy" in cat_lower) and "prompt_injection_resistance" not in evaluators_to_run:
        evaluators_to_run.append("prompt_injection_resistance")
    elif ("unsafe_tool" in cat_lower or "tool" in cat_lower) and "tool_policy_enforcement" not in evaluators_to_run:
        evaluators_to_run.append("tool_policy_enforcement")
    elif "policy" in cat_lower and "policy_compliance" not in evaluators_to_run:
        evaluators_to_run.append("policy_compliance")

    # 3. Additional criteria-based checks
    if ("canary_values" in criteria or "synthetic_secrets" in criteria) and "secret_leakage" not in evaluators_to_run:
        evaluators_to_run.append("secret_leakage")
    if ("forbidden_patterns" in criteria or "check_system_commands" in criteria) and "forbidden_pattern" not in evaluators_to_run:
        evaluators_to_run.append("forbidden_pattern")
    if ("allowed_tools" in criteria or "disallowed_tools" in criteria or "forbidden_tools" in criteria) and "tool_policy_enforcement" not in evaluators_to_run:
        evaluators_to_run.append("tool_policy_enforcement")
    if "policy_rules" in criteria and "policy_compliance" not in evaluators_to_run:
        evaluators_to_run.append("policy_compliance")
    if "injection_indicators" in criteria and "prompt_injection_resistance" not in evaluators_to_run:
        evaluators_to_run.append("prompt_injection_resistance")
    if "refusal_patterns" in criteria and "required_refusal" not in evaluators_to_run:
        evaluators_to_run.append("required_refusal")

    # 4. Optional LLM safety judge if explicitly enabled in campaign config
    if config.get("enable_llm_judge", False) and "optional_llm_safety_judge" not in evaluators_to_run:
        evaluators_to_run.append("optional_llm_safety_judge")

    # Fallback default if still empty
    if not evaluators_to_run:
        evaluators_to_run.append("prompt_injection_resistance")

    return evaluators_to_run


async def evaluate_safety_case(
    test_case: TestCase,
    actual_output: Any,
    run_context: dict[str, Any] | None = None,
    campaign_config: dict[str, Any] | None = None,
) -> tuple[bool, str, list[dict[str, Any]], dict[str, Any] | None]:
    """
    Run appropriate deterministic safety evaluators against agent response and spans.
    Returns: (passed: bool, status: str, evaluator_results: list[dict], combined_evidence: dict | None)
    """
    campaign_config = campaign_config or {}
    criteria = test_case.criteria or {}
    metadata = test_case.test_metadata or {}
    category = str(metadata.get("category", criteria.get("category", "prompt_injection")))

    evaluators_to_run = _determine_evaluators(category, criteria, campaign_config)

    all_passed = True
    any_error = False
    details: list[dict[str, Any]] = []
    evidences: list[Any] = []

    for ev_name in evaluators_to_run:
        evaluator = evaluator_registry.get(ev_name)
        if not evaluator:
            res = EvaluationResult(
                evaluator_name=ev_name,
                evaluator_version="1.0",
                passed=False,
                outcome="error",
                score=0.0,
                explanation=f"Safety evaluator '{ev_name}' is not registered.",
            )
        else:
            try:
                res = await evaluator.evaluate(
                    actual_output=actual_output,
                    expected_output=test_case.expected_output,
                    criteria=criteria,
                    run_context=run_context,
                )
            except Exception as e:
                logger.exception(f"Unhandled exception in safety evaluator '{ev_name}': {e}")
                res = EvaluationResult(
                    evaluator_name=ev_name,
                    evaluator_version=evaluator.version,
                    passed=False,
                    outcome="error",
                    score=0.0,
                    explanation=f"Internal evaluator exception: {e}",
                )

        details.append(res.to_dict())
        if res.evidence:
            evidences.append({res.evaluator_name: res.evidence})

        if res.outcome == "error":
            any_error = True
            all_passed = False
        elif not res.passed:
            all_passed = False

    overall_status = "error" if any_error else ("pass" if all_passed else "fail")

    combined_evidence = None
    if evidences:
        combined_evidence = redact_sensitive_content(
            evidences if len(evidences) > 1 else evidences[0]
        )

    return all_passed, overall_status, details, combined_evidence


async def run_safety_campaign_task(
    campaign_id: uuid.UUID,
    session_factory: Any = None,
) -> None:
    """
    Execute a Safety Campaign asynchronously.
    Executes each safety test case, records trace spans, evaluates outcomes,
    and updates campaign metrics without leaving the campaign in an orphaned state.
    """
    async with _get_session_scope() as session:
        stmt = select(SafetyCampaign).where(SafetyCampaign.id == campaign_id)
        res = await session.execute(stmt)
        campaign = res.scalar_one_or_none()

        if not campaign:
            logger.error(f"Safety Campaign {campaign_id} not found for background execution.")
            return

        campaign.status = "running"
        campaign.started_at = datetime.now(UTC)
        await session.commit()

        # 1. Resolve agent adapter
        adapter = agent_registry.get(campaign.agent_name, campaign.agent_version)
        if not adapter:
            campaign.status = "error"
            campaign.ended_at = datetime.now(UTC)
            campaign.summary = {
                "error": (
                    f"Agent '{campaign.agent_name}' version '{campaign.agent_version}' "
                    "is not in the approved agent registry."
                )
            }
            await session.commit()
            return

        # 2. Fetch dataset test cases
        cases_stmt = (
            select(TestCase)
            .where(TestCase.dataset_id == campaign.dataset_id)
            .order_by(TestCase.created_at.asc())
        )
        cases_res = await session.execute(cases_stmt)
        test_cases = cases_res.scalars().all()

        campaign.total_tests = len(test_cases)
        await session.commit()

        passed_count = 0
        failed_count = 0
        errored_count = 0
        critical_count = 0

        # Aggregation tracking
        category_map: dict[str, dict[str, int]] = {}
        severity_map: dict[str, dict[str, int]] = {
            "critical": {"total": 0, "passed": 0, "failed": 0},
            "high": {"total": 0, "passed": 0, "failed": 0},
            "medium": {"total": 0, "passed": 0, "failed": 0},
            "low": {"total": 0, "passed": 0, "failed": 0},
        }

        try:
            for tc in test_cases:
                meta = tc.test_metadata or {}
                criteria = tc.criteria or {}

                stable_case_id = str(meta.get("test_case_id", meta.get("id", f"SEC-{str(tc.id)[:8]}")))
                category = str(meta.get("category", criteria.get("category", "prompt_injection")))
                severity = str(meta.get("severity", criteria.get("severity", "medium"))).lower()
                if severity not in severity_map:
                    severity = "medium"

                expected_safe_behavior = (
                    meta.get("expected_safe_behavior")
                    or (str(tc.expected_output) if tc.expected_output else "Refusal or safe compliance")
                )

                # Initialize category in map
                if category not in category_map:
                    category_map[category] = {"total": 0, "passed": 0, "failed": 0}

                category_map[category]["total"] += 1
                severity_map[severity]["total"] += 1

                # 1. Execute agent adapter inside safe boundary
                agent_res = await execute_agent_safely(
                    adapter=adapter,
                    prompt_input=tc.input,
                    config=campaign.config,
                )

                # 2. Record trace Run and Spans for observability
                run_id = uuid.uuid4()
                now_utc = datetime.now(UTC)
                run_record = Run(
                    id=run_id,
                    project_id=campaign.project_id,
                    name=f"safety:{campaign.name}:{stable_case_id}",
                    status="completed" if not agent_res.error else "error",
                    input={"prompt": tc.input},
                    output=agent_res.output if isinstance(agent_res.output, dict) else {"result": agent_res.output},
                    error=agent_res.error,
                    duration_ms=agent_res.duration_ms,
                    total_tokens=agent_res.total_tokens,
                    total_cost_usd=agent_res.total_cost_usd,
                    started_at=now_utc,
                    ended_at=now_utc,
                )
                session.add(run_record)

                for span_data in agent_res.spans:
                    span_record = Span(
                        id=uuid.uuid4(),
                        run_id=run_id,
                        name=span_data.get("name", "tool_call"),
                        span_type=span_data.get("span_type", "tool"),
                        status=span_data.get("status", "completed"),
                        input=span_data.get("input"),
                        output=span_data.get("output"),
                        model=span_data.get("model"),
                        prompt_tokens=span_data.get("prompt_tokens", 0),
                        completion_tokens=span_data.get("completion_tokens", 0),
                        total_tokens=span_data.get("total_tokens", 0),
                        cost_usd=Decimal(str(span_data.get("cost_usd", 0.0))),
                        duration_ms=span_data.get("duration_ms", 1),
                        started_at=now_utc,
                        ended_at=now_utc,
                    )
                    session.add(span_record)

                # 3. Evaluate safety outcome
                run_context = {
                    "spans": agent_res.spans,
                    "duration_ms": agent_res.duration_ms,
                    "total_tokens": agent_res.total_tokens,
                }

                if agent_res.status in ("error", "timeout"):
                    case_passed = False
                    case_status = "error"
                    eval_details = [
                        {
                            "evaluator_name": "agent_execution_boundary",
                            "passed": False,
                            "outcome": "error",
                            "score": 0.0,
                            "severity": severity,
                            "explanation": agent_res.error or "Agent execution failed",
                        }
                    ]
                    evidence = {"error": agent_res.error}
                else:
                    case_passed, case_status, eval_details, evidence = await evaluate_safety_case(
                        test_case=tc,
                        actual_output=agent_res.output,
                        run_context=run_context,
                        campaign_config=campaign.config,
                    )

                # Update counters
                if case_status == "pass":
                    passed_count += 1
                    category_map[category]["passed"] += 1
                    severity_map[severity]["passed"] += 1
                elif case_status == "fail":
                    failed_count += 1
                    category_map[category]["failed"] += 1
                    severity_map[severity]["failed"] += 1
                    if severity == "critical":
                        critical_count += 1
                else:
                    errored_count += 1
                    category_map[category]["failed"] += 1
                    severity_map[severity]["failed"] += 1

                # 4. Insert SafetyTestResult
                test_result = SafetyTestResult(
                    id=uuid.uuid4(),
                    campaign_id=campaign.id,
                    test_case_id=tc.id,
                    run_id=run_id,
                    stable_case_id=stable_case_id,
                    category=category,
                    severity=severity,
                    adversarial_input=tc.input,
                    agent_output=agent_res.output,
                    expected_safe_behavior=expected_safe_behavior,
                    passed=case_passed,
                    status=case_status,
                    error=agent_res.error,
                    duration_ms=agent_res.duration_ms,
                    evaluator_results=eval_details,
                    evidence=evidence,
                )
                session.add(test_result)
                await session.flush()

        except Exception as e:
            logger.exception(f"Fatal error during safety campaign {campaign_id}: {e}")
            campaign.status = "error"
            campaign.summary = {"fatal_error": str(e)}
            campaign.ended_at = datetime.now(UTC)
            await session.commit()
            return

        # 5. Finalize campaign aggregates
        total_executed = passed_count + failed_count + errored_count
        pass_rate = (
            round(passed_count / total_executed, 4)
            if total_executed > 0
            else 0.0
        )

        # Compute category pass rates
        category_scores: dict[str, dict[str, Any]] = {}
        for cat, counts in category_map.items():
            tot = counts["total"]
            pas = counts["passed"]
            category_scores[cat] = {
                "total": tot,
                "passed": pas,
                "failed": counts["failed"],
                "pass_rate": round(pas / tot, 4) if tot > 0 else 0.0,
            }

        campaign.total_tests = total_executed
        campaign.passed_tests = passed_count
        campaign.failed_tests = failed_count
        campaign.errored_tests = errored_count
        campaign.critical_failures = critical_count
        campaign.safety_pass_rate = Decimal(str(pass_rate))
        campaign.category_scores = category_scores
        campaign.severity_summary = severity_map
        campaign.status = "completed"
        campaign.ended_at = datetime.now(UTC)
        campaign.summary = {
            "total_tests": total_executed,
            "passed_tests": passed_count,
            "failed_tests": failed_count,
            "errored_tests": errored_count,
            "critical_failures": critical_count,
            "safety_pass_rate": pass_rate,
            "category_scores": category_scores,
            "severity_summary": severity_map,
        }

        await session.commit()
        logger.info(
            f"Safety Campaign {campaign_id} completed: {passed_count}/{total_executed} passed ({pass_rate * 100:.1f}%), {critical_count} critical failures."
        )
