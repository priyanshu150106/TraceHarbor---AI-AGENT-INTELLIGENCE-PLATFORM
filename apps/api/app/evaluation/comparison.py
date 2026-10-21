"""
TraceHarbor API — Experiment Version Comparison & Regression Detection Logic
"""

import uuid
from typing import Any

from app.models.experiment import Experiment
from app.models.experiment_result import ExperimentResult
from app.models.test_case import TestCase


def compare_experiments(
    experiment_a: Experiment,
    experiment_b: Experiment,
    results_a: list[ExperimentResult],
    results_b: list[ExperimentResult],
    test_cases_map: dict[uuid.UUID, TestCase],
) -> dict[str, Any]:
    """
    Compare baseline experiment (A) with candidate experiment (B).
    Accurately aligns test cases by immutable test_case_id.

    Regression Definition:
    A regression occurs when a test case passed in Experiment A (baseline)
    and failed in Experiment B (candidate). Evaluator and agent runtime errors
    are strictly isolated from genuine regression failures.
    """
    map_a: dict[uuid.UUID, ExperimentResult] = {r.test_case_id: r for r in results_a}
    map_b: dict[uuid.UUID, ExperimentResult] = {r.test_case_id: r for r in results_b}

    all_case_ids = set(map_a.keys()) | set(map_b.keys())

    regressions: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []
    evaluator_errors: list[dict[str, Any]] = []
    missing_cases: list[dict[str, Any]] = []
    all_compared: list[dict[str, Any]] = []

    for case_id in all_case_ids:
        tc = test_cases_map.get(case_id)
        input_data = tc.input if tc else None
        expected_output = tc.expected_output if tc else None

        res_a = map_a.get(case_id)
        res_b = map_b.get(case_id)

        if not res_a or not res_b:
            item = {
                "test_case_id": str(case_id),
                "input": input_data,
                "expected_output": expected_output,
                "category": "missing",
                "missing_in": "baseline" if not res_a else "candidate",
                "a": _format_result(res_a),
                "b": _format_result(res_b),
            }
            missing_cases.append(item)
            all_compared.append(item)
            continue

        # Both results exist
        status_a = res_a.status  # pass, fail, error
        status_b = res_b.status
        passed_a = res_a.passed is True
        passed_b = res_b.passed is True

        if status_a == "error" or status_b == "error":
            category = "error"
        elif passed_a and not passed_b:
            category = "regression"
        elif not passed_a and passed_b:
            category = "improvement"
        else:
            category = "unchanged"

        item = {
            "test_case_id": str(case_id),
            "input": input_data,
            "expected_output": expected_output,
            "category": category,
            "a": _format_result(res_a),
            "b": _format_result(res_b),
        }

        if category == "regression":
            regressions.append(item)
        elif category == "improvement":
            improvements.append(item)
        elif category == "error":
            evaluator_errors.append(item)
        else:
            unchanged.append(item)

        all_compared.append(item)

    # Compute deltas
    rate_a = (
        round(experiment_a.passed_cases / experiment_a.total_cases, 4)
        if experiment_a.total_cases > 0
        else 0.0
    )
    rate_b = (
        round(experiment_b.passed_cases / experiment_b.total_cases, 4)
        if experiment_b.total_cases > 0
        else 0.0
    )
    pass_rate_delta = round(rate_b - rate_a, 4)

    score_a = float(experiment_a.score or 0.0)
    score_b = float(experiment_b.score or 0.0)
    score_delta = round(score_b - score_a, 4)

    return {
        "experiment_a": {
            "id": str(experiment_a.id),
            "name": experiment_a.name,
            "agent_name": experiment_a.agent_name,
            "agent_version": experiment_a.agent_version,
            "total_cases": experiment_a.total_cases,
            "passed_cases": experiment_a.passed_cases,
            "failed_cases": experiment_a.failed_cases,
            "errored_cases": experiment_a.errored_cases,
            "pass_rate": rate_a,
            "score": score_a,
            "status": experiment_a.status,
        },
        "experiment_b": {
            "id": str(experiment_b.id),
            "name": experiment_b.name,
            "agent_name": experiment_b.agent_name,
            "agent_version": experiment_b.agent_version,
            "total_cases": experiment_b.total_cases,
            "passed_cases": experiment_b.passed_cases,
            "failed_cases": experiment_b.failed_cases,
            "errored_cases": experiment_b.errored_cases,
            "pass_rate": rate_b,
            "score": score_b,
            "status": experiment_b.status,
        },
        "summary": {
            "total_compared": len(all_case_ids),
            "regressions_count": len(regressions),
            "improvements_count": len(improvements),
            "unchanged_count": len(unchanged),
            "errors_count": len(evaluator_errors),
            "missing_count": len(missing_cases),
            "pass_rate_delta": pass_rate_delta,
            "score_delta": score_delta,
        },
        "regressions": regressions,
        "improvements": improvements,
        "unchanged": unchanged,
        "errors": evaluator_errors,
        "missing": missing_cases,
        "all_cases": all_compared,
    }


def _format_result(res: ExperimentResult | None) -> dict[str, Any] | None:
    if not res:
        return None
    return {
        "id": str(res.id),
        "run_id": str(res.run_id) if res.run_id else None,
        "passed": res.passed,
        "status": res.status,
        "scores": res.scores or {},
        "actual_output": res.actual_output,
        "duration_ms": res.duration_ms,
        "error": res.error,
        "evaluation_details": res.evaluation_details or [],
    }
