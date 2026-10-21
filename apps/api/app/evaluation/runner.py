"""
TraceHarbor API — Experiment Execution Runner & Case Evaluator
"""

import logging
import uuid
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.evaluation.agent_registry import agent_registry
from app.evaluation.base import EvaluationResult
from app.evaluation.registry import evaluator_registry
from app.models.experiment import Experiment
from app.models.experiment_result import ExperimentResult
from app.models.run import Run
from app.models.span import Span
from app.models.test_case import TestCase

logger = logging.getLogger(__name__)


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


async def evaluate_case(
    test_case: TestCase,
    actual_output: Any,
    run_context: dict[str, Any] | None = None,
    experiment_config: dict[str, Any] | None = None,
) -> tuple[bool, str, dict[str, float], list[dict[str, Any]]]:
    """
    Run appropriate evaluators for a test case based on criteria and experiment config.
    Returns: (passed: bool, status: str, scores: dict[str, float], details: list[dict])
    """
    experiment_config = experiment_config or {}
    criteria = test_case.criteria or {}
    details: list[dict[str, Any]] = []
    scores: dict[str, float] = {}

    # Determine which evaluators to trigger
    evaluators_to_run: list[str] = []

    # 1. Configured on experiment level
    if "evaluators" in experiment_config and isinstance(experiment_config["evaluators"], list):
        evaluators_to_run.extend(experiment_config["evaluators"])

    # 2. Inferred from test case criteria
    if ("required_keywords" in criteria or "keywords" in criteria) and "required_keywords" not in evaluators_to_run:
        evaluators_to_run.append("required_keywords")
    if ("pattern" in criteria or "regex_pattern" in criteria) and "regex_match" not in evaluators_to_run:
        evaluators_to_run.append("regex_match")
    if ("json_schema" in criteria or "schema" in criteria) and "json_schema" not in evaluators_to_run:
        evaluators_to_run.append("json_schema")
    if ("required_tool" in criteria or "required_tools" in criteria) and "required_tool_call" not in evaluators_to_run:
        evaluators_to_run.append("required_tool_call")
    if "max_latency_ms" in criteria and "latency_threshold" not in evaluators_to_run:
        evaluators_to_run.append("latency_threshold")
    if ("max_tokens" in criteria or "max_cost_usd" in criteria) and "token_cost_threshold" not in evaluators_to_run:
        evaluators_to_run.append("token_cost_threshold")
    if ("rubric" in criteria or "llm_judge" in criteria) and "llm_judge" not in evaluators_to_run:
        evaluators_to_run.append("llm_judge")

    # 3. Default fallback evaluators if none matched
    if not evaluators_to_run:
        evaluators_to_run.append("output_presence")
        if test_case.expected_output is not None:
            evaluators_to_run.append("exact_match")

    all_passed = True
    any_error = False

    for ev_name in evaluators_to_run:
        evaluator = evaluator_registry.get(ev_name)
        if not evaluator:
            res = EvaluationResult(
                evaluator_name=ev_name,
                evaluator_version="1.0",
                passed=False,
                outcome="error",
                score=0.0,
                explanation=f"Evaluator '{ev_name}' is not registered in the system.",
                expected_value=None,
                actual_value=actual_output,
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
                logger.exception(f"Unhandled exception in evaluator {ev_name}: {e}")
                res = EvaluationResult(
                    evaluator_name=ev_name,
                    evaluator_version=evaluator.version,
                    passed=False,
                    outcome="error",
                    score=0.0,
                    explanation=f"Internal evaluator exception: {e}",
                    expected_value=None,
                    actual_value=actual_output,
                )

        details.append(res.to_dict())
        scores[res.evaluator_name] = res.score
        if res.outcome == "error":
            any_error = True
            all_passed = False
        elif not res.passed:
            all_passed = False

    overall_status = "error" if any_error else ("pass" if all_passed else "fail")
    return all_passed, overall_status, scores, details


async def run_experiment_task(
    experiment_id: uuid.UUID,
    session_factory: Any = None,
) -> None:
    """
    Execute an experiment asynchronously.
    Updates DB records throughout the run and computes aggregate metrics upon completion.
    """
    async with _get_session_scope() as session:
        # Load experiment with dataset and test cases
        stmt = select(Experiment).where(Experiment.id == experiment_id)
        res = await session.execute(stmt)
        experiment = res.scalar_one_or_none()

        if not experiment:
            logger.error(f"Experiment {experiment_id} not found for background execution.")
            return

        # Mark as running
        experiment.status = "running"
        experiment.started_at = datetime.now(UTC)
        await session.commit()

        # Resolve agent adapter
        adapter = agent_registry.get(experiment.agent_name, experiment.agent_version)
        if not adapter:
            experiment.status = "error"
            experiment.ended_at = datetime.now(UTC)
            experiment.summary = {
                "error": (
                    f"Agent '{experiment.agent_name}' version '{experiment.agent_version}' "
                    "is not in the approved agent registry."
                )
            }
            await session.commit()
            return

        # Fetch dataset test cases
        cases_stmt = (
            select(TestCase)
            .where(TestCase.dataset_id == experiment.dataset_id)
            .order_by(TestCase.created_at.asc())
        )
        cases_res = await session.execute(cases_stmt)
        test_cases = cases_res.scalars().all()

        experiment.total_cases = len(test_cases)
        await session.commit()

        passed_count = 0
        failed_count = 0
        errored_count = 0
        total_duration = 0
        total_tokens = 0
        total_cost = Decimal("0.0")

        try:
            for test_case in test_cases:
                # 1. Execute agent adapter
                agent_res = await adapter.execute(
                    prompt_input=test_case.input,
                    config=experiment.config,
                )

                total_duration += agent_res.duration_ms
                total_tokens += agent_res.total_tokens
                total_cost += agent_res.total_cost_usd

                # 2. Create trace Run & Spans for TraceHarbor observability
                run_id = uuid.uuid4()
                now_utc = datetime.now(UTC)
                run_record = Run(
                    id=run_id,
                    project_id=experiment.project_id,
                    name=f"eval:{experiment.name}:{test_case.id}",
                    status="completed" if not agent_res.error else "error",
                    input={"prompt": test_case.input},
                    output=agent_res.output if isinstance(agent_res.output, dict) else {"result": agent_res.output},
                    error=agent_res.error,
                    tags=["eval", f"exp:{experiment.id}", experiment.agent_name, experiment.agent_version],
                    run_metadata={"experiment_id": str(experiment.id), "test_case_id": str(test_case.id)},
                    total_tokens=agent_res.total_tokens,
                    total_cost_usd=agent_res.total_cost_usd,
                    duration_ms=agent_res.duration_ms,
                    started_at=now_utc,
                    ended_at=now_utc,
                )
                session.add(run_record)

                # Persist spans
                for sp in agent_res.spans:
                    span_id = uuid.uuid4()
                    span_record = Span(
                        id=span_id,
                        run_id=run_id,
                        parent_span_id=None,
                        name=sp.get("name", "tool"),
                        span_type=sp.get("span_type", "tool"),
                        status=sp.get("status", "completed"),
                        input=sp.get("input"),
                        output=sp.get("output"),
                        model=sp.get("model"),
                        prompt_tokens=sp.get("prompt_tokens", 0),
                        completion_tokens=sp.get("completion_tokens", 0),
                        total_tokens=sp.get("total_tokens", 0),
                        cost_usd=Decimal(str(sp.get("cost_usd", 0.0))),
                        duration_ms=sp.get("duration_ms"),
                        started_at=now_utc,
                        ended_at=now_utc,
                    )
                    session.add(span_record)

                # 3. Evaluate output
                run_context = {
                    "duration_ms": agent_res.duration_ms,
                    "total_tokens": agent_res.total_tokens,
                    "total_cost_usd": float(agent_res.total_cost_usd),
                    "spans": agent_res.spans,
                }

                passed, case_status, scores, eval_details = await evaluate_case(
                    test_case=test_case,
                    actual_output=agent_res.output,
                    run_context=run_context,
                    experiment_config=experiment.config,
                )

                if case_status == "pass":
                    passed_count += 1
                elif case_status == "error":
                    errored_count += 1
                else:
                    failed_count += 1

                # 4. Save ExperimentResult
                result_row = ExperimentResult(
                    id=uuid.uuid4(),
                    experiment_id=experiment.id,
                    test_case_id=test_case.id,
                    run_id=run_id,
                    actual_output=agent_res.output if isinstance(agent_res.output, dict | list | str | int | float) else str(agent_res.output),
                    scores=scores,
                    passed=passed,
                    status=case_status,
                    error=agent_res.error,
                    duration_ms=agent_res.duration_ms,
                    evaluation_details=eval_details,
                )
                session.add(result_row)

            # 5. Finalize experiment
            total = len(test_cases)
            final_score = Decimal(str(round(passed_count / total, 4))) if total > 0 else Decimal("0.0000")

            experiment.passed_cases = passed_count
            experiment.failed_cases = failed_count
            experiment.errored_cases = errored_count
            experiment.score = final_score
            experiment.status = "completed"
            experiment.ended_at = datetime.now(UTC)

            experiment.summary = {
                "total_cases": total,
                "passed_cases": passed_count,
                "failed_cases": failed_count,
                "errored_cases": errored_count,
                "pass_rate": float(final_score),
                "score": float(final_score),
                "avg_duration_ms": int(total_duration / total) if total > 0 else 0,
                "total_tokens": total_tokens,
                "total_cost_usd": float(total_cost),
            }

            await session.commit()
            logger.info(
                f"Experiment {experiment.id} completed. Total: {total}, Passed: {passed_count}, Score: {final_score}"
            )

        except Exception as e:
            logger.exception(f"Fatal error executing experiment {experiment_id}: {e}")
            await session.rollback()
            # In a clean transaction, mark experiment as error
            async with _get_session_scope() as err_session:
                stmt = select(Experiment).where(Experiment.id == experiment_id)
                res = await err_session.execute(stmt)
                exp = res.scalar_one_or_none()
                if exp:
                    exp.status = "error"
                    exp.ended_at = datetime.now(UTC)
                    exp.summary = {"error": f"Execution failed: {str(e)}"}
                    await err_session.commit()
