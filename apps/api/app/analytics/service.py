"""
TraceHarbor API — Analytics Service

Audited metric semantics and efficient database aggregation for operational telemetry,
latency percentiles, token usage, cost breakdowns, and evaluation benchmarks.
"""

import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experiment import Experiment
from app.models.run import Run
from app.models.span import Span
from app.schemas.analytics import (
    AgentsAnalyticsResponse,
    AgentUsageItem,
    AnalyticsTimeseriesResponse,
    CostBreakdownItem,
    CostBreakdownResponse,
    ModelsAnalyticsResponse,
    ModelUsageItem,
    TimeseriesPoint,
)
from app.schemas.runs import AnalyticsOverviewResponse, RunSummaryResponse


def parse_time_window(
    time_range: str = "7d",
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> tuple[datetime, datetime, str]:
    """
    Parse requested time window into UTC start/end datetimes and bucket interval.
    Supported ranges: '24h', '7d', '30d', 'all', 'custom'.
    """
    now = datetime.now(UTC)
    if end_time is None:
        end_time = now
    elif end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=UTC)

    time_range_clean = time_range.strip().lower()
    if time_range_clean == "24h":
        start_time = end_time - timedelta(hours=24)
        interval = "1h"
    elif time_range_clean == "30d":
        start_time = end_time - timedelta(days=30)
        interval = "1d"
    elif time_range_clean == "all":
        start_time = datetime(2020, 1, 1, tzinfo=UTC)
        interval = "1d"
    elif time_range_clean == "custom" and start_time is not None:
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=UTC)
        delta = end_time - start_time
        interval = "1h" if delta.total_seconds() <= 86400 * 2 else "1d"
    else:  # default 7d
        start_time = end_time - timedelta(days=7)
        interval = "1d"

    return start_time, end_time, interval


def calculate_percentile(values: list[float], percentile: float) -> float:
    """Compute percentile from sorted list of floats (0.0 to 1.0)."""
    if not values:
        return 0.0
    k = (len(values) - 1) * percentile
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(values[int(k)])
    d0 = float(values[int(f)]) * (c - k)
    d1 = float(values[int(c)]) * (k - f)
    return float(d0 + d1)


class AnalyticsService:
    """Service providing aggregated operational and evaluation metrics."""

    @staticmethod
    async def get_overview(
        project_id: uuid.UUID,
        db: AsyncSession,
        time_range: str = "7d",
        agent_name: str | None = None,
        agent_version: str | None = None,
    ) -> AnalyticsOverviewResponse:
        """
        Compute high-level operational overview metrics for the active project.
        """
        start_time, end_time, _ = parse_time_window(time_range)

        # Base filter conditions
        run_filters = [
            Run.project_id == project_id,
            Run.started_at >= start_time,
            Run.started_at <= end_time,
        ]
        if agent_name:
            run_filters.append(Run.name == agent_name)

        # Aggregate totals from runs table
        agg_stmt = select(
            func.count(Run.id).label("total_runs"),
            func.sum(Run.total_tokens).label("total_tokens"),
            func.sum(Run.total_cost_usd).label("total_cost"),
            func.avg(Run.duration_ms).label("avg_duration"),
        ).where(*run_filters)
        agg_res = await db.execute(agg_stmt)
        agg_row = agg_res.one()

        total_runs = agg_row.total_runs or 0
        if total_runs == 0:
            return AnalyticsOverviewResponse(time_range=time_range)

        total_tokens = agg_row.total_tokens or 0
        total_cost_usd = float(agg_row.total_cost or 0.0)
        avg_duration_ms = float(agg_row.avg_duration or 0.0)

        # Count runs reporting cost vs unmetered
        cost_count_stmt = select(
            func.count(Run.id).filter(Run.total_cost_usd > 0).label("metered"),
            func.count(Run.id).filter(
                (Run.total_cost_usd.is_(None)) | (Run.total_cost_usd == 0)
            ).label("unmetered"),
        ).where(*run_filters)
        cost_counts = (await db.execute(cost_count_stmt)).one()
        cost_reported_runs = cost_counts.metered or 0
        unmetered_runs = cost_counts.unmetered or 0

        # Status counts
        status_stmt = (
            select(Run.status, func.count(Run.id))
            .where(*run_filters)
            .group_by(Run.status)
        )
        status_res = await db.execute(status_stmt)
        status_map = {row[0]: row[1] for row in status_res.all()}

        successful_runs = status_map.get("completed", 0) + status_map.get("success", 0)
        failed_runs = status_map.get("error", 0)
        error_rate = round(failed_runs / total_runs, 4) if total_runs > 0 else 0.0

        # Compute p50 and p95 latencies
        dur_stmt = (
            select(Run.duration_ms)
            .where(*run_filters, Run.duration_ms.is_not(None))
            .order_by(Run.duration_ms.asc())
        )
        dur_res = await db.execute(dur_stmt)
        durations = [float(d) for d in dur_res.scalars().all() if d is not None]

        p50_duration_ms = round(calculate_percentile(durations, 0.50), 2)
        p95_duration_ms = round(calculate_percentile(durations, 0.95), 2)

        # Correlate evaluation pass rate from completed experiments
        exp_stmt = select(
            func.sum(Experiment.passed_cases).label("passed"),
            func.sum(Experiment.total_cases).label("total"),
        ).where(
            Experiment.project_id == project_id,
            Experiment.status == "completed",
            Experiment.created_at >= start_time,
            Experiment.created_at <= end_time,
        )
        exp_res = await db.execute(exp_stmt)
        exp_row = exp_res.one()

        eval_pass_rate = None
        if exp_row.total and exp_row.total > 0:
            eval_pass_rate = round(float(exp_row.passed or 0) / float(exp_row.total), 4)

        # Recent 5 runs
        recent_stmt = (
            select(Run)
            .where(*run_filters)
            .order_by(desc(Run.started_at))
            .limit(5)
        )
        recent_res = await db.execute(recent_stmt)
        recent_runs = [
            RunSummaryResponse(
                id=r.id,
                project_id=r.project_id,
                name=r.name,
                status=r.status,
                total_tokens=r.total_tokens,
                total_cost_usd=r.total_cost_usd,
                duration_ms=r.duration_ms,
                started_at=r.started_at,
                ended_at=r.ended_at,
                tags=r.tags or [],
                metadata=r.run_metadata or {},
            )
            for r in recent_res.scalars().all()
        ]

        return AnalyticsOverviewResponse(
            total_runs=total_runs,
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            error_rate=error_rate,
            p50_duration_ms=p50_duration_ms,
            avg_duration_ms=round(avg_duration_ms, 2),
            p95_duration_ms=p95_duration_ms,
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost_usd, 6),
            cost_reported_runs=cost_reported_runs,
            unmetered_runs=unmetered_runs,
            eval_pass_rate=eval_pass_rate,
            time_range=time_range,
            recent_runs=recent_runs,
        )

    @staticmethod
    async def get_timeseries(
        project_id: uuid.UUID,
        db: AsyncSession,
        time_range: str = "7d",
        agent_name: str | None = None,
    ) -> AnalyticsTimeseriesResponse:
        """
        Generate bucketed time-series telemetry points for continuous chart rendering.
        Guarantees that sparse or empty time intervals are populated with clean zeros.
        """
        start_time, end_time, interval = parse_time_window(time_range)

        # 1. Generate discrete bucket timestamps
        buckets: list[datetime] = []
        step = timedelta(hours=1) if interval == "1h" else timedelta(days=1)
        curr = start_time
        while curr <= end_time:
            buckets.append(curr)
            curr += step

        # 2. Query all runs within window
        run_filters = [
            Run.project_id == project_id,
            Run.started_at >= start_time,
            Run.started_at <= end_time,
        ]
        if agent_name:
            run_filters.append(Run.name == agent_name)

        runs_stmt = (
            select(
                Run.started_at,
                Run.status,
                Run.duration_ms,
                Run.total_tokens,
                Run.total_cost_usd,
            )
            .where(*run_filters)
            .order_by(Run.started_at.asc())
        )
        runs_res = await db.execute(runs_stmt)
        runs_data = runs_res.all()

        # 3. Bucket runs into time slices
        bucket_data: dict[datetime, list[Any]] = {b: [] for b in buckets}
        for r in runs_data:
            r_time = r.started_at if r.started_at.tzinfo else r.started_at.replace(tzinfo=UTC)
            # Find closest bucket start <= r_time
            best_bucket = buckets[0]
            for b in buckets:
                if b <= r_time:
                    best_bucket = b
                else:
                    break
            bucket_data[best_bucket].append(r)

        # 4. Compute metrics per bucket
        points: list[TimeseriesPoint] = []
        for b in buckets:
            items = bucket_data.get(b, [])
            total = len(items)
            if total == 0:
                points.append(
                    TimeseriesPoint(
                        timestamp=b,
                        total_runs=0,
                        successful_runs=0,
                        failed_runs=0,
                        error_rate=0.0,
                        p50_duration_ms=0.0,
                        p95_duration_ms=0.0,
                        total_tokens=0,
                        total_cost_usd=0.0,
                        eval_pass_rate=None,
                    )
                )
                continue

            success = sum(1 for it in items if it.status in ("completed", "success"))
            failed = sum(1 for it in items if it.status == "error")
            err_rate = round(failed / total, 4) if total > 0 else 0.0
            durations = sorted(
                float(it.duration_ms) for it in items if it.duration_ms is not None
            )
            p50 = round(calculate_percentile(durations, 0.50), 2)
            p95 = round(calculate_percentile(durations, 0.95), 2)
            tokens = sum(it.total_tokens or 0 for it in items)
            cost = sum(float(it.total_cost_usd or 0.0) for it in items)

            points.append(
                TimeseriesPoint(
                    timestamp=b,
                    total_runs=total,
                    successful_runs=success,
                    failed_runs=failed,
                    error_rate=err_rate,
                    p50_duration_ms=p50,
                    p95_duration_ms=p95,
                    total_tokens=tokens,
                    total_cost_usd=round(cost, 6),
                    eval_pass_rate=None,
                )
            )

        return AnalyticsTimeseriesResponse(
            time_range=time_range,
            interval=interval,
            points=points,
            total_points=len(points),
        )

    @staticmethod
    async def get_models(
        project_id: uuid.UUID,
        db: AsyncSession,
        time_range: str = "7d",
    ) -> ModelsAnalyticsResponse:
        """
        Aggregate usage and performance metrics broken down by LLM model.
        """
        start_time, end_time, _ = parse_time_window(time_range)

        stmt = (
            select(
                Span.model,
                func.count(Span.id).label("call_count"),
                func.sum(Span.prompt_tokens).label("prompt_tokens"),
                func.sum(Span.completion_tokens).label("completion_tokens"),
                func.sum(Span.total_tokens).label("total_tokens"),
                func.sum(Span.cost_usd).label("cost_usd"),
                func.avg(Span.duration_ms).label("avg_duration"),
            )
            .join(Run, Span.run_id == Run.id)
            .where(
                Run.project_id == project_id,
                Span.model.is_not(None),
                Span.model != "",
                Run.started_at >= start_time,
                Run.started_at <= end_time,
            )
            .group_by(Span.model)
            .order_by(desc("call_count"))
        )
        res = await db.execute(stmt)
        rows = res.all()

        items = [
            ModelUsageItem(
                model=row.model,
                call_count=row.call_count or 0,
                prompt_tokens=row.prompt_tokens or 0,
                completion_tokens=row.completion_tokens or 0,
                total_tokens=row.total_tokens or 0,
                total_cost_usd=round(float(row.cost_usd or 0.0), 6),
                avg_latency_ms=round(float(row.avg_duration or 0.0), 2),
            )
            for row in rows
        ]

        return ModelsAnalyticsResponse(items=items, total_models=len(items))

    @staticmethod
    async def get_agents(
        project_id: uuid.UUID,
        db: AsyncSession,
        time_range: str = "7d",
    ) -> AgentsAnalyticsResponse:
        """
        Compare performance, error rates, costs, and eval pass rates across agents.
        """
        start_time, end_time, _ = parse_time_window(time_range)

        # 1. Fetch runs grouped by agent name
        runs_stmt = (
            select(Run)
            .where(
                Run.project_id == project_id,
                Run.started_at >= start_time,
                Run.started_at <= end_time,
            )
            .order_by(Run.name)
        )
        runs_res = await db.execute(runs_stmt)
        runs = runs_res.scalars().all()

        # Group by (agent_name, agent_version)
        grouped: dict[tuple[str, str], list[Run]] = {}
        for r in runs:
            # Extract version from tags if present or fallback to '1.0'
            version = "1.0"
            if r.tags:
                for t in r.tags:
                    if t.startswith("v") or "." in t:
                        version = t.lstrip("v")
                        break
            elif r.run_metadata and "version" in r.run_metadata:
                version = str(r.run_metadata["version"])

            key = (r.name, version)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(r)

        # 2. Fetch experiment pass rates by agent version
        exp_stmt = select(
            Experiment.agent_name,
            Experiment.agent_version,
            func.sum(Experiment.passed_cases).label("passed"),
            func.sum(Experiment.total_cases).label("total"),
        ).where(
            Experiment.project_id == project_id,
            Experiment.status == "completed",
        ).group_by(Experiment.agent_name, Experiment.agent_version)
        exp_res = await db.execute(exp_stmt)
        eval_map: dict[tuple[str, str], float] = {}
        for er in exp_res.all():
            if er.total and er.total > 0:
                eval_map[(er.agent_name, er.agent_version)] = round(
                    float(er.passed or 0) / float(er.total), 4
                )

        items: list[AgentUsageItem] = []
        for (agent_name, version), agent_runs in grouped.items():
            total = len(agent_runs)
            successful = sum(1 for r in agent_runs if r.status in ("completed", "success"))
            failed = sum(1 for r in agent_runs if r.status == "error")
            err_rate = round(failed / total, 4) if total > 0 else 0.0

            durations = sorted(
                float(r.duration_ms) for r in agent_runs if r.duration_ms is not None
            )
            avg_dur = round(sum(durations) / len(durations), 2) if durations else 0.0
            p95_dur = round(calculate_percentile(durations, 0.95), 2)
            tokens = sum(r.total_tokens or 0 for r in agent_runs)
            cost = sum(float(r.total_cost_usd or 0.0) for r in agent_runs)

            eval_rate = eval_map.get((agent_name, version))

            items.append(
                AgentUsageItem(
                    agent_name=agent_name,
                    agent_version=version,
                    total_runs=total,
                    successful_runs=successful,
                    failed_runs=failed,
                    error_rate=err_rate,
                    avg_duration_ms=avg_dur,
                    p95_duration_ms=p95_dur,
                    total_tokens=tokens,
                    total_cost_usd=round(cost, 6),
                    eval_pass_rate=eval_rate,
                )
            )

        items.sort(key=lambda x: x.total_runs, reverse=True)
        return AgentsAnalyticsResponse(items=items, total_agents=len(items))

    @staticmethod
    async def get_cost_breakdown(
        project_id: uuid.UUID,
        db: AsyncSession,
        time_range: str = "7d",
    ) -> CostBreakdownResponse:
        """
        Calculate cost attribution by date, agent, and LLM model.
        """
        start_time, end_time, _ = parse_time_window(time_range)

        # 1. Total cost and reported counts
        runs_stmt = select(
            func.sum(Run.total_cost_usd).label("total_cost"),
            func.count(Run.id).filter(Run.total_cost_usd > 0).label("metered"),
            func.count(Run.id).filter(
                (Run.total_cost_usd.is_(None)) | (Run.total_cost_usd == 0)
            ).label("unmetered"),
        ).where(
            Run.project_id == project_id,
            Run.started_at >= start_time,
            Run.started_at <= end_time,
        )
        cost_row = (await db.execute(runs_stmt)).one()
        total_cost_usd = round(float(cost_row.total_cost or 0.0), 6)
        metered = cost_row.metered or 0
        unmetered = cost_row.unmetered or 0

        # 2. Cost by Agent
        agent_stmt = (
            select(Run.name, func.sum(Run.total_cost_usd).label("cost"))
            .where(
                Run.project_id == project_id,
                Run.started_at >= start_time,
                Run.started_at <= end_time,
            )
            .group_by(Run.name)
        )
        agent_res = await db.execute(agent_stmt)
        by_agent = {
            row[0]: round(float(row[1] or 0.0), 6)
            for row in agent_res.all()
            if row[0] is not None
        }

        # 3. Cost by Model (from spans)
        model_stmt = (
            select(Span.model, func.sum(Span.cost_usd).label("cost"))
            .join(Run, Span.run_id == Run.id)
            .where(
                Run.project_id == project_id,
                Span.model.is_not(None),
                Span.model != "",
                Run.started_at >= start_time,
                Run.started_at <= end_time,
            )
            .group_by(Span.model)
        )
        model_res = await db.execute(model_stmt)
        by_model = {
            row[0]: round(float(row[1] or 0.0), 6)
            for row in model_res.all()
            if row[0] is not None
        }

        # 4. Daily breakdown
        daily_stmt = (
            select(
                Run.started_at,
                Run.name,
                Run.total_cost_usd,
                Run.total_tokens,
            )
            .where(
                Run.project_id == project_id,
                Run.started_at >= start_time,
                Run.started_at <= end_time,
            )
            .order_by(Run.started_at.desc())
            .limit(100)
        )
        daily_res = await db.execute(daily_stmt)
        daily_items: list[CostBreakdownItem] = [
            CostBreakdownItem(
                date=r.started_at.strftime("%Y-%m-%d"),
                agent_name=r.name,
                model="gpt-4o-mini",
                cost_usd=round(float(r.total_cost_usd or 0.0), 6),
                token_count=r.total_tokens or 0,
            )
            for r in daily_res.all()
            if r.total_cost_usd and float(r.total_cost_usd) > 0
        ]

        return CostBreakdownResponse(
            total_cost_usd=total_cost_usd,
            cost_reported_runs=metered,
            unmetered_runs=unmetered,
            by_agent=by_agent,
            by_model=by_model,
            daily_breakdown=daily_items,
        )
