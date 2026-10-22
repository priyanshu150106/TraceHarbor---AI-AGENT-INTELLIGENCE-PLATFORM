"""
TraceHarbor API — Alert Rule Management & Fired Alert History Endpoints
"""

import math
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.notifications import SSRFValidationError, validate_webhook_url
from app.alerts.service import AlertEvaluationService
from app.core.auth import resolve_project_id
from app.core.database import get_db
from app.models.alert import AlertHistory, AlertRule
from app.schemas.alerts import (
    AlertEvaluationBatchResponse,
    AlertEvaluationResult,
    AlertHistoryListResponse,
    AlertHistoryResponse,
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
)

router = APIRouter(tags=["Alerts"])


async def _get_project_rule(
    rule_id: uuid.UUID,
    project_id: uuid.UUID,
    db: AsyncSession,
) -> AlertRule:
    """Retrieve rule guaranteeing project-level ownership."""
    stmt = select(AlertRule).where(
        AlertRule.id == rule_id,
        AlertRule.project_id == project_id,
    )
    rule = (await db.execute(stmt)).scalar_one_or_none()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule '{rule_id}' not found in authorized project.",
        )
    return rule


@router.post(
    "/alerts/rules",
    response_model=AlertRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Alert Rule",
)
async def create_alert_rule(
    payload: AlertRuleCreate,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> AlertRuleResponse:
    """Create a new threshold monitoring alert rule."""
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID is required to create alert rules.",
        )

    # If webhook channel, validate URL against SSRF
    if payload.channel == "webhook":
        if not payload.webhook_url:
            raise HTTPException(
                status_code=422,
                detail="Webhook URL is required when channel is 'webhook'.",
            )
        try:
            validate_webhook_url(payload.webhook_url)
        except SSRFValidationError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid webhook URL: {str(e)}",
            ) from e

    now = datetime.now(UTC)
    rule = AlertRule(
        id=uuid.uuid4(),
        project_id=project_id,
        name=payload.name.strip(),
        metric=payload.metric,
        operator=payload.operator,
        threshold=payload.threshold,
        window_minutes=payload.window_minutes,
        is_active=True,
        channel=payload.channel,
        webhook_url=payload.webhook_url.strip() if payload.webhook_url else None,
        webhook_secret=payload.webhook_secret.strip() if payload.webhook_secret else None,
        cooldown_minutes=payload.cooldown_minutes,
        created_at=now,
        updated_at=now,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return AlertRuleResponse(
        id=rule.id,
        project_id=rule.project_id,
        name=rule.name,
        metric=rule.metric,
        operator=rule.operator,
        threshold=rule.threshold,
        window_minutes=rule.window_minutes,
        is_active=rule.is_active,
        channel=rule.channel,
        webhook_url=rule.webhook_url,
        has_webhook_secret=bool(rule.webhook_secret),
        cooldown_minutes=rule.cooldown_minutes,
        last_triggered_at=rule.last_triggered_at,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.get(
    "/alerts/rules",
    response_model=list[AlertRuleResponse],
    status_code=status.HTTP_200_OK,
    summary="List Alert Rules",
)
async def list_alert_rules(
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> list[AlertRuleResponse]:
    """List all alert rules configured for the active project."""
    if not project_id:
        return []

    stmt = (
        select(AlertRule)
        .where(AlertRule.project_id == project_id)
        .order_by(desc(AlertRule.created_at))
    )
    res = await db.execute(stmt)
    rules = res.scalars().all()

    return [
        AlertRuleResponse(
            id=r.id,
            project_id=r.project_id,
            name=r.name,
            metric=r.metric,
            operator=r.operator,
            threshold=r.threshold,
            window_minutes=r.window_minutes,
            is_active=r.is_active,
            channel=r.channel,
            webhook_url=r.webhook_url,
            has_webhook_secret=bool(r.webhook_secret),
            cooldown_minutes=r.cooldown_minutes,
            last_triggered_at=r.last_triggered_at,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rules
    ]


@router.patch(
    "/alerts/rules/{rule_id}",
    response_model=AlertRuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Alert Rule",
)
async def update_alert_rule(
    rule_id: uuid.UUID,
    payload: AlertRuleUpdate,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> AlertRuleResponse:
    """Modify an existing alert rule with strict project isolation."""
    if not project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project ID required.")

    rule = await _get_project_rule(rule_id, project_id, db)

    if payload.name is not None:
        rule.name = payload.name.strip()
    if payload.metric is not None:
        rule.metric = payload.metric
    if payload.operator is not None:
        rule.operator = payload.operator
    if payload.threshold is not None:
        rule.threshold = payload.threshold
    if payload.window_minutes is not None:
        rule.window_minutes = payload.window_minutes
    if payload.is_active is not None:
        rule.is_active = payload.is_active
    if payload.channel is not None:
        rule.channel = payload.channel
    if payload.webhook_url is not None:
        url_clean = payload.webhook_url.strip() if payload.webhook_url else None
        if url_clean and rule.channel == "webhook":
            try:
                validate_webhook_url(url_clean)
            except SSRFValidationError as e:
                raise HTTPException(status_code=422, detail=f"Invalid webhook URL: {str(e)}") from e
        rule.webhook_url = url_clean
    if payload.webhook_secret is not None:
        rule.webhook_secret = payload.webhook_secret.strip() if payload.webhook_secret else None
    if payload.cooldown_minutes is not None:
        rule.cooldown_minutes = payload.cooldown_minutes

    rule.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(rule)

    return AlertRuleResponse(
        id=rule.id,
        project_id=rule.project_id,
        name=rule.name,
        metric=rule.metric,
        operator=rule.operator,
        threshold=rule.threshold,
        window_minutes=rule.window_minutes,
        is_active=rule.is_active,
        channel=rule.channel,
        webhook_url=rule.webhook_url,
        has_webhook_secret=bool(rule.webhook_secret),
        cooldown_minutes=rule.cooldown_minutes,
        last_triggered_at=rule.last_triggered_at,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.delete(
    "/alerts/rules/{rule_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Alert Rule",
)
async def delete_alert_rule(
    rule_id: uuid.UUID,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Permanently delete an alert rule and its associated history."""
    if not project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project ID required.")

    rule = await _get_project_rule(rule_id, project_id, db)
    await db.delete(rule)
    await db.commit()

    return {"status": "deleted", "message": f"Alert rule '{rule.name}' deleted."}


@router.get(
    "/alerts/history",
    response_model=AlertHistoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Fired Alert History",
)
async def get_alert_history(
    rule_id: Annotated[uuid.UUID | None, Query(description="Filter by specific rule")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> AlertHistoryListResponse:
    """Retrieve paginated audit history of triggered alerts."""
    if not project_id:
        return AlertHistoryListResponse(items=[], total=0, page=page, page_size=page_size, total_pages=1)

    filters = [AlertHistory.project_id == project_id]
    if rule_id:
        filters.append(AlertHistory.rule_id == rule_id)

    # Count total
    count_stmt = select(func.count(AlertHistory.id)).where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    # Query page
    stmt = (
        select(AlertHistory, AlertRule.name.label("rule_name"))
        .join(AlertRule, AlertHistory.rule_id == AlertRule.id)
        .where(*filters)
        .order_by(desc(AlertHistory.fired_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).all()

    items = [
        AlertHistoryResponse(
            id=hist.id,
            rule_id=hist.rule_id,
            rule_name=rule_name,
            project_id=hist.project_id,
            metric=hist.metric,
            metric_value=hist.metric_value,
            threshold=hist.threshold,
            operator=hist.operator,
            message=hist.message,
            status=hist.status,
            notification_status=hist.notification_status,
            notification_error=hist.notification_error,
            acknowledged=hist.acknowledged,
            fired_at=hist.fired_at,
            created_at=hist.created_at,
        )
        for hist, rule_name in rows
    ]

    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    return AlertHistoryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/alerts/evaluate",
    response_model=AlertEvaluationBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate All Active Alert Rules",
)
async def evaluate_active_rules(
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> AlertEvaluationBatchResponse:
    """
    Evaluate all active alert rules for the project against current recorded telemetry.
    Fires alerts for breached conditions that are not within an active cooldown.
    """
    if not project_id:
        return AlertEvaluationBatchResponse(rules_evaluated=0, alerts_triggered=0, cooldown_suppressed=0)

    results = await AlertEvaluationService.evaluate_all_rules(
        project_id=project_id,
        db=db,
        mock_dispatch=False,
    )

    triggered_count = sum(1 for r in results if r.triggered and not r.cooldown_active)
    cooldown_count = sum(1 for r in results if r.cooldown_active)

    return AlertEvaluationBatchResponse(
        rules_evaluated=len(results),
        alerts_triggered=triggered_count,
        cooldown_suppressed=cooldown_count,
        results=results,
    )


@router.post(
    "/alerts/test/{rule_id}",
    response_model=AlertEvaluationResult,
    status_code=status.HTTP_200_OK,
    summary="Test Alert Rule Against Current Telemetry",
)
async def test_alert_rule(
    rule_id: uuid.UUID,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> AlertEvaluationResult:
    """Test evaluate a single rule without updating cooldown or persisting fired alert."""
    if not project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project ID required.")

    rule = await _get_project_rule(rule_id, project_id, db)
    observed = await AlertEvaluationService.compute_metric(
        project_id=rule.project_id,
        metric=rule.metric,
        window_minutes=rule.window_minutes,
        db=db,
    )
    breached = (
        observed > rule.threshold if rule.operator == ">"
        else observed >= rule.threshold if rule.operator == ">="
        else observed < rule.threshold if rule.operator == "<"
        else observed <= rule.threshold if rule.operator == "<="
        else math.isclose(observed, rule.threshold)
    )

    return AlertEvaluationResult(
        rule_id=rule.id,
        rule_name=rule.name,
        metric=rule.metric,
        observed_value=observed,
        threshold=rule.threshold,
        operator=rule.operator,
        triggered=breached,
        cooldown_active=False,
        message=(
            f"Test evaluation: observed {observed} vs threshold {rule.operator} {rule.threshold}. "
            f"Condition is {'BREACHED' if breached else 'OK'}."
        ),
    )
