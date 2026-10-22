"""
TraceHarbor API — Safety Campaign Version Comparison & Regression Analysis

Compares two safety campaign executions (Baseline vs Candidate) across
adversarial threat categories, tracking newly introduced vulnerabilities (regressions),
resolved safety issues, and category-level pass rate deltas.
"""

from typing import Any

from app.models.safety import SafetyCampaign, SafetyTestResult
from app.models.test_case import TestCase


def _format_result_summary(res: SafetyTestResult | None) -> dict[str, Any] | None:
    if not res:
        return None
    return {
        "id": str(res.id),
        "status": res.status,
        "passed": res.passed,
        "category": res.category,
        "severity": res.severity,
        "duration_ms": res.duration_ms,
        "error": res.error,
        "evidence": res.evidence,
        "evaluator_results": res.evaluator_results,
    }


def compare_safety_campaigns(
    baseline: SafetyCampaign,
    candidate: SafetyCampaign,
    results_a: list[SafetyTestResult],
    results_b: list[SafetyTestResult],
    test_cases_map: dict[str, TestCase],
) -> dict[str, Any]:
    """
    Perform stable alignment and regression comparison between baseline and candidate campaigns.
    Key classifications:
    - newly_introduced_failure: Passed in baseline, Failed in candidate (Regression)
    - resolved_failure: Failed in baseline, Passed in candidate (Improvement / Fix)
    - unchanged_failure: Failed in both (Persistent vulnerability)
    - unchanged_pass: Passed in both (Consistently safe)
    - error: Execution or evaluation error in either
    - missing: Present in one campaign but missing in the other
    """
    map_a: dict[str, SafetyTestResult] = {r.stable_case_id: r for r in results_a}
    map_b: dict[str, SafetyTestResult] = {r.stable_case_id: r for r in results_b}

    all_case_ids = sorted(list(set(map_a.keys()) | set(map_b.keys())))

    newly_introduced_failures: list[dict[str, Any]] = []
    resolved_failures: list[dict[str, Any]] = []
    unchanged_failures: list[dict[str, Any]] = []
    unchanged_passes: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    missing_cases: list[dict[str, Any]] = []
    all_compared: list[dict[str, Any]] = []

    # Category tracking for deltas
    categories = set()

    for cid in all_case_ids:
        tc = test_cases_map.get(cid)
        res_a = map_a.get(cid)
        res_b = map_b.get(cid)

        category = (res_b.category if res_b else (res_a.category if res_a else "unknown"))
        severity = (res_b.severity if res_b else (res_a.severity if res_a else "medium"))
        categories.add(category)

        input_data = tc.input if tc else (res_b.adversarial_input if res_b else (res_a.adversarial_input if res_a else None))
        expected_safe_behavior = (
            res_b.expected_safe_behavior if res_b else (res_a.expected_safe_behavior if res_a else None)
        )

        if not res_a or not res_b:
            item = {
                "stable_case_id": cid,
                "category": category,
                "severity": severity,
                "adversarial_input": input_data,
                "expected_safe_behavior": expected_safe_behavior,
                "comparison_status": "missing",
                "missing_in": "baseline" if not res_a else "candidate",
                "baseline": _format_result_summary(res_a),
                "candidate": _format_result_summary(res_b),
            }
            missing_cases.append(item)
            all_compared.append(item)
            continue

        status_a = res_a.status
        status_b = res_b.status
        passed_a = res_a.passed is True
        passed_b = res_b.passed is True

        if status_a == "error" or status_b == "error":
            comp_status = "error"
        elif passed_a and not passed_b:
            comp_status = "newly_introduced_failure"
        elif not passed_a and passed_b:
            comp_status = "resolved_failure"
        elif not passed_a and not passed_b:
            comp_status = "unchanged_failure"
        else:
            comp_status = "unchanged_pass"

        item = {
            "stable_case_id": cid,
            "category": category,
            "severity": severity,
            "adversarial_input": input_data,
            "expected_safe_behavior": expected_safe_behavior,
            "comparison_status": comp_status,
            "baseline": _format_result_summary(res_a),
            "candidate": _format_result_summary(res_b),
        }

        if comp_status == "newly_introduced_failure":
            newly_introduced_failures.append(item)
        elif comp_status == "resolved_failure":
            resolved_failures.append(item)
        elif comp_status == "unchanged_failure":
            unchanged_failures.append(item)
        elif comp_status == "unchanged_pass":
            unchanged_passes.append(item)
        elif comp_status == "error":
            errors.append(item)

        all_compared.append(item)

    # Calculate overall metric deltas
    rate_a = (
        round(float(baseline.passed_tests) / float(baseline.total_tests), 4)
        if baseline.total_tests > 0
        else 0.0
    )
    rate_b = (
        round(float(candidate.passed_tests) / float(candidate.total_tests), 4)
        if candidate.total_tests > 0
        else 0.0
    )
    delta_pass_rate = round(rate_b - rate_a, 4)

    delta_critical_failures = candidate.critical_failures - baseline.critical_failures

    # Category deltas
    cat_scores_a = baseline.category_scores or {}
    cat_scores_b = candidate.category_scores or {}
    category_comparison: list[dict[str, Any]] = []

    for cat in sorted(list(categories)):
        info_a = cat_scores_a.get(cat, {})
        info_b = cat_scores_b.get(cat, {})
        c_rate_a = info_a.get("pass_rate", 0.0)
        c_rate_b = info_b.get("pass_rate", 0.0)
        category_comparison.append(
            {
                "category": cat,
                "baseline_pass_rate": c_rate_a,
                "candidate_pass_rate": c_rate_b,
                "delta_pass_rate": round(c_rate_b - c_rate_a, 4),
                "baseline_failed": info_a.get("failed", 0),
                "candidate_failed": info_b.get("failed", 0),
            }
        )

    return {
        "baseline_campaign": {
            "id": str(baseline.id),
            "name": baseline.name,
            "agent_name": baseline.agent_name,
            "agent_version": baseline.agent_version,
            "total_tests": baseline.total_tests,
            "passed_tests": baseline.passed_tests,
            "failed_tests": baseline.failed_tests,
            "critical_failures": baseline.critical_failures,
            "safety_pass_rate": rate_a,
        },
        "candidate_campaign": {
            "id": str(candidate.id),
            "name": candidate.name,
            "agent_name": candidate.agent_name,
            "agent_version": candidate.agent_version,
            "total_tests": candidate.total_tests,
            "passed_tests": candidate.passed_tests,
            "failed_tests": candidate.failed_tests,
            "critical_failures": candidate.critical_failures,
            "safety_pass_rate": rate_b,
        },
        "summary": {
            "delta_pass_rate": delta_pass_rate,
            "delta_critical_failures": delta_critical_failures,
            "newly_introduced_failures_count": len(newly_introduced_failures),
            "resolved_failures_count": len(resolved_failures),
            "unchanged_failures_count": len(unchanged_failures),
            "unchanged_passes_count": len(unchanged_passes),
            "errors_count": len(errors),
            "missing_cases_count": len(missing_cases),
            "total_aligned_cases": len(all_compared),
        },
        "category_comparison": category_comparison,
        "newly_introduced_failures": newly_introduced_failures,
        "resolved_failures": resolved_failures,
        "unchanged_failures": unchanged_failures,
        "unchanged_passes": unchanged_passes,
        "errors": errors,
        "all_cases": all_compared,
    }
