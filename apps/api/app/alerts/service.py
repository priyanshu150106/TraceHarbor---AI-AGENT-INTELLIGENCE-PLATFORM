"""
TraceHarbor API — Alert Evaluation Service

Evaluates configured alert rules against live telemetry, enforces cooldown windows,
deduplicates alert records, and dispatches notifications.
"""

import math
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.notifications import NotificationService
from app.analytics.service import calculate_percentile
from app.models.alert import AlertHistory, AlertRule
from app.models.experiment import Experiment
from app.models.run import Run
from app.schemas.alerts import AlertEvaluationResult


def check_threshold_condition(observed: float, operator: str, threshold: float) -> bool:
    """Evaluate comparison operator between observed metric and threshold."""
    op = operator.strip()
    if op == ">":
        return observed > threshold
    elif op == ">=":
        return observed >= threshold
    elif op == "<":
        return observed < threshold
    elif op == "<=":
        return observed <= threshold
    elif op == "==":
        return math.isclose(observed, threshold, abs_tol=1e-5)
    return False


class AlertEvaluationService:
    """Service evaluating alert rules against telemetry and persisting fired alerts."""

    @staticmethod
    async def compute_metric(
        project_id: uuid.UUID,
        metric: str,
        window_minutes: int,
        db: AsyncSession,
    ) -> float:
        """Calculate the numerical value of a monitored metric over the look-back window."""
        now = datetime.now(UTC)
        window_start = now - timedelta(minutes=window_minutes)

        if metric == "error_rate":
            stmt = select(
                func.count(Run.id).label("total"),
                func.count(Run.id).filter(Run.status == "error").label("failed"),
            ).where(
                Run.project_id == project_id,
                Run.started_at >= window_start,
                Run.started_at <= now,
            )
            res = (await db.execute(stmt)).one()
            total = res.total or 0
            failed = res.failed or 0
            return round(failed / total, 4) if total > 0 else 0.0

        elif metric == "p95_latency":
            stmt = (
                select(Run.duration_ms)
                .where(
                    Run.project_id == project_id,
                    Run.started_at >= window_start,
                    Run.started_at <= now,
                    Run.duration_ms.is_not(None),
                )
                .order_by(Run.duration_ms.asc())
            )
            durations = [float(d) for d in (await db.execute(stmt)).scalars().all() if d is not None]
            return round(calculate_percentile(durations, 0.95), 2)

        elif metric == "cost_usd":
            stmt = select(func.sum(Run.total_cost_usd)).where(
                Run.project_id == project_id,
                Run.started_at >= window_start,
                Run.started_at <= now,
            )
            total_cost = (await db.execute(stmt)).scalar_one_or_none()
            return round(float(total_cost or 0.0), 6)

        elif metric == "eval_pass_rate":
            stmt = select(
                func.sum(Experiment.passed_cases).label("passed"),
                func.sum(Experiment.total_cases).label("total"),
            ).where(
                Experiment.project_id == project_id,
                Experiment.status == "completed",
                Experiment.created_at >= window_start,
                Experiment.created_at <= now,
            )
            res = (await db.execute(stmt)).one()
            if res.total and res.total > 0:
                return round(float(res.passed or 0) / float(res.total), 4)
            return 1.0  # Default to 100% when no experiments were run to avoid false alarms

        elif metric == "regression_count":
            # Count failed cases in experiments run within window that recorded regressions
            stmt = select(func.sum(Experiment.failed_cases)).where(
                Experiment.project_id == project_id,
                Experiment.status == "completed",
                Experiment.created_at >= window_start,
                Experiment.created_at <= now,
            )
            failed_cases = (await db.execute(stmt)).scalar_one_or_none()
            return float(failed_cases or 0)

        return 0.0

    @staticmethod
    async def evaluate_single_rule(
        rule: AlertRule,
        db: AsyncSession,
        mock_dispatch: bool = False,
    ) -> AlertEvaluationResult:
        """
        Evaluate a single rule, enforce cooldown deduplication, and dispatch notifications if triggered.
        """
        now = datetime.now(UTC)
        observed = await AlertEvaluationService.compute_metric(
            project_id=rule.project_id,
            metric=rule.metric,
            window_minutes=rule.window_minutes,
            db=db,
        )

        condition_breached = check_threshold_condition(observed, rule.operator, rule.threshold)

        # If condition is not met
        if not condition_breached:
            return AlertEvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                metric=rule.metric,
                observed_value=observed,
                threshold=rule.threshold,
                operator=rule.operator,
                triggered=False,
                cooldown_active=False,
                message=f"Metric '{rule.metric}' observed value {observed} did not breach threshold {rule.operator} {rule.threshold}.",
            )

        # Condition is breached! Check cooldown window
        if rule.last_triggered_at:
            last_trig = rule.last_triggered_at
            if last_trig.tzinfo is None:
                last_trig = last_trig.replace(tzinfo=UTC)
            cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
            if (now - last_trig) < cooldown_delta:
                # Cooldown active — suppress repeat noise
                remaining_mins = int((cooldown_delta - (now - last_trig)).total_seconds() / 60)
                return AlertEvaluationResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    metric=rule.metric,
                    observed_value=observed,
                    threshold=rule.threshold,
                    operator=rule.operator,
                    triggered=True,
                    cooldown_active=True,
                    message=f"Condition breached ({observed} {rule.operator} {rule.threshold}), but suppressed by active cooldown ({remaining_mins}m remaining).",
                )

        # Trigger fired! Record to AlertHistory
        explanation = (
            f"Alert '{rule.name}' triggered: {rule.metric} observed {observed} "
            f"breached threshold {rule.operator} {rule.threshold} over last {rule.window_minutes} minutes."
        )

        notification_status = "delivered"
        notification_error = None

        if rule.channel == "webhook" and rule.webhook_url:
            payload = {
                "event": "alert_triggered",
                "alert_name": rule.name,
                "metric": rule.metric,
                "observed_value": observed,
                "threshold": rule.threshold,
                "operator": rule.operator,
                "window_minutes": rule.window_minutes,
                "fired_at": now.isoformat(),
                "project_id": str(rule.project_id),
            }
            notification_status, notification_error = await NotificationService.dispatch_webhook(
                webhook_url=rule.webhook_url,
                payload=payload,
                webhook_secret=rule.webhook_secret,
                mock_mode=mock_dispatch,
            )

        history_entry = AlertHistory(
            id=uuid.uuid4(),
            rule_id=rule.id,
            project_id=rule.project_id,
            metric=rule.metric,
            metric_value=observed,
            threshold=rule.threshold,
            operator=rule.operator,
            message=explanation,
            status="triggered",
            notification_status=notification_status,
            notification_error=notification_error,
            acknowledged=False,
            fired_at=now,
            created_at=now,
        )
        db.add(history_entry)

        # Update last_triggered_at
        rule.last_triggered_at = now
        await db.commit()

        return AlertEvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            metric=rule.metric,
            observed_value=observed,
            threshold=rule.threshold,
            operator=rule.operator,
            triggered=True,
            cooldown_active=False,
            notification_status=notification_status,
            message=explanation,
        )

    @staticmethod
    async def evaluate_all_rules(
        project_id: uuid.UUID,
        db: AsyncSession,
        mock_dispatch: bool = False,
    ) -> list[AlertEvaluationResult]:
        """Evaluate all active rules for the given project."""
        stmt = select(AlertRule).where(
            AlertRule.project_id == project_id,
            AlertRule.is_active.is_(True),
        )
        res = await db.execute(stmt)
        rules = res.scalars().all()

        results: list[AlertEvaluationResult] = []
        for rule in rules:
            out = await AlertEvaluationService.evaluate_single_rule(
                rule=rule,
                db=db,
                mock_dispatch=mock_dispatch,
            )
            results.append(out)

        return results
