"""
TraceHarbor API — Experiments & Version Comparison Endpoints
"""

import math
import uuid
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import resolve_project_id
from app.core.database import get_db
from app.evaluation.agent_registry import agent_registry
from app.evaluation.comparison import compare_experiments
from app.evaluation.runner import run_experiment_task
from app.models.dataset import Dataset
from app.models.experiment import Experiment
from app.models.experiment_result import ExperimentResult
from app.models.test_case import TestCase
from app.schemas.experiments import (
    ExperimentCreateRequest,
    ExperimentDetailResponse,
    ExperimentListResponse,
    ExperimentResultResponse,
    ExperimentSummaryResponse,
)

router = APIRouter(tags=["Experiments"])




@router.get(
    "/experiments/agents",
    status_code=status.HTTP_200_OK,
    summary="List Approved Demo Agents",
)
async def list_approved_agents() -> list[dict[str, Any]]:
    """Return the approved agent directory for experiment target selection."""
    return agent_registry.list_approved_agents()


@router.post(
    "/experiments",
    response_model=ExperimentSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create & Start Experiment",
)
async def create_experiment(
    payload: ExperimentCreateRequest,
    background_tasks: BackgroundTasks,
    run_sync: bool = Query(False, description="Run synchronously before returning (useful for automated testing)"),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> ExperimentSummaryResponse:
    """
    Launch an evaluation experiment against a dataset using an approved agent version.
    Validates agent registry, dataset existence, and tenant ownership.
    """
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID is required to start an experiment.",
        )

    # 1. Validate Dataset ownership
    d_stmt = select(Dataset).where(Dataset.id == payload.dataset_id)
    d_res = await db.execute(d_stmt)
    dataset = d_res.scalar_one_or_none()

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{payload.dataset_id}' not found.",
        )

    if dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Target dataset belongs to a different project.",
        )

    # 2. Validate Agent Registry
    adapter = agent_registry.get(payload.agent_name, payload.agent_version)
    if not adapter:
        approved = [
            f"{a['agent_name']} (v{a['agent_version']})"
            for a in agent_registry.list_approved_agents()
        ]
        raise HTTPException(
            status_code=422,
            detail=(
                f"Agent '{payload.agent_name}' version '{payload.agent_version}' is not in the approved agent registry. "
                f"Approved agents: {', '.join(approved)}."
            ),
        )

    # Count dataset cases
    case_cnt_stmt = select(func.count(TestCase.id)).where(TestCase.dataset_id == dataset.id)
    case_cnt = (await db.execute(case_cnt_stmt)).scalar_one()

    if case_cnt == 0:
        raise HTTPException(
            status_code=422,
            detail="Cannot run experiment: target dataset has no test cases.",
        )

    experiment = Experiment(
        id=uuid.uuid4(),
        project_id=project_id,
        dataset_id=dataset.id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        status="pending",
        agent_name=payload.agent_name.strip(),
        agent_version=payload.agent_version.strip(),
        config=payload.config or {},
        total_cases=case_cnt,
    )
    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)

    if run_sync:
        # Run synchronously (ideal for pytest and integration verification)
        await run_experiment_task(experiment.id)
        await db.refresh(experiment)
    else:
        # Run in background
        background_tasks.add_task(run_experiment_task, experiment.id)

    pass_rate = (
        round(experiment.passed_cases / experiment.total_cases, 4)
        if experiment.total_cases > 0
        else None
    )

    return ExperimentSummaryResponse(
        id=experiment.id,
        project_id=experiment.project_id,
        dataset_id=experiment.dataset_id,
        dataset_name=dataset.name,
        name=experiment.name,
        description=experiment.description,
        status=experiment.status,
        agent_name=experiment.agent_name,
        agent_version=experiment.agent_version,
        total_cases=experiment.total_cases,
        passed_cases=experiment.passed_cases,
        failed_cases=experiment.failed_cases,
        errored_cases=experiment.errored_cases,
        score=float(experiment.score) if experiment.score is not None else None,
        pass_rate=pass_rate,
        started_at=experiment.started_at,
        ended_at=experiment.ended_at,
        created_at=experiment.created_at,
    )


@router.get(
    "/experiments",
    response_model=ExperimentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Experiments",
)
async def list_experiments(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status (pending, running, completed, error)"),
    dataset_id: uuid.UUID | None = Query(None, description="Filter by dataset ID"),
    search: str | None = Query(None, description="Search by experiment name"),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> ExperimentListResponse:
    """Retrieve paginated list of experiments for authorized project."""
    if not project_id:
        return ExperimentListResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)

    conditions = [Experiment.project_id == project_id]
    if status_filter:
        conditions.append(Experiment.status == status_filter)
    if dataset_id:
        conditions.append(Experiment.dataset_id == dataset_id)
    if search:
        conditions.append(Experiment.name.ilike(f"%{search.strip()}%"))

    # Total count
    count_stmt = select(func.count(Experiment.id)).where(*conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    # Query items with joined Dataset
    stmt = (
        select(Experiment, Dataset.name.label("dataset_name"))
        .join(Dataset, Experiment.dataset_id == Dataset.id)
        .where(*conditions)
        .order_by(desc(Experiment.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    res = await db.execute(stmt)
    rows = res.all()

    items: list[ExperimentSummaryResponse] = []
    for exp, d_name in rows:
        pass_rate = (
            round(exp.passed_cases / exp.total_cases, 4)
            if exp.total_cases > 0
            else None
        )
        items.append(
            ExperimentSummaryResponse(
                id=exp.id,
                project_id=exp.project_id,
                dataset_id=exp.dataset_id,
                dataset_name=d_name,
                name=exp.name,
                description=exp.description,
                status=exp.status,
                agent_name=exp.agent_name,
                agent_version=exp.agent_version,
                total_cases=exp.total_cases,
                passed_cases=exp.passed_cases,
                failed_cases=exp.failed_cases,
                errored_cases=exp.errored_cases,
                score=float(exp.score) if exp.score is not None else None,
                pass_rate=pass_rate,
                started_at=exp.started_at,
                ended_at=exp.ended_at,
                created_at=exp.created_at,
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return ExperimentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/experiments/compare",
    status_code=status.HTTP_200_OK,
    summary="Compare Two Experiments for Regressions",
)
async def compare_experiment_runs(
    a: uuid.UUID = Query(..., description="Baseline experiment ID"),
    b: uuid.UUID = Query(..., description="Candidate experiment ID"),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Compare baseline experiment (A) with candidate experiment (B).
    Calculates per-case regressions, improvements, unchanged results, and score deltas.
    """
    # 1. Fetch both experiments
    stmt_a = select(Experiment).where(Experiment.id == a)
    exp_a = (await db.execute(stmt_a)).scalar_one_or_none()

    stmt_b = select(Experiment).where(Experiment.id == b)
    exp_b = (await db.execute(stmt_b)).scalar_one_or_none()

    if not exp_a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Baseline experiment '{a}' not found.")
    if not exp_b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate experiment '{b}' not found.")

    # 2. Enforce tenant isolation
    if project_id:
        if exp_a.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Baseline experiment belongs to a different project.",
            )
        if exp_b.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Candidate experiment belongs to a different project.",
            )

    # 3. Check completion status
    if exp_a.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Baseline experiment '{a}' is not completed (current status: '{exp_a.status}').",
        )
    if exp_b.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Candidate experiment '{b}' is not completed (current status: '{exp_b.status}').",
        )

    # 4. Fetch per-case results
    res_a_stmt = select(ExperimentResult).where(ExperimentResult.experiment_id == a)
    results_a = (await db.execute(res_a_stmt)).scalars().all()

    res_b_stmt = select(ExperimentResult).where(ExperimentResult.experiment_id == b)
    results_b = (await db.execute(res_b_stmt)).scalars().all()

    # 5. Fetch associated test cases
    case_ids = {r.test_case_id for r in results_a} | {r.test_case_id for r in results_b}
    cases_stmt = select(TestCase).where(TestCase.id.in_(case_ids))
    cases = (await db.execute(cases_stmt)).scalars().all()
    test_cases_map = {c.id: c for c in cases}

    # 6. Execute comparison algorithm
    comparison = compare_experiments(
        experiment_a=exp_a,
        experiment_b=exp_b,
        results_a=results_a,
        results_b=results_b,
        test_cases_map=test_cases_map,
    )

    return comparison


@router.get(
    "/experiments/{experiment_id}",
    response_model=ExperimentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Experiment Details & Results",
)
async def get_experiment(
    experiment_id: uuid.UUID,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> ExperimentDetailResponse:
    """Retrieve full details of an experiment, including summary metrics and all per-case results."""
    stmt = (
        select(Experiment, Dataset.name.label("dataset_name"))
        .join(Dataset, Experiment.dataset_id == Dataset.id)
        .where(Experiment.id == experiment_id)
    )
    res = await db.execute(stmt)
    row = res.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{experiment_id}' not found.",
        )

    exp, dataset_name = row

    if project_id and exp.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Experiment belongs to a different project.",
        )

    # Fetch results joined with TestCase input/expected_output
    results_stmt = (
        select(ExperimentResult, TestCase.input.label("test_input"), TestCase.expected_output.label("expected_output"))
        .join(TestCase, ExperimentResult.test_case_id == TestCase.id)
        .where(ExperimentResult.experiment_id == experiment_id)
        .order_by(ExperimentResult.created_at.asc())
    )
    results_res = await db.execute(results_stmt)
    results_rows = results_res.all()

    result_items: list[ExperimentResultResponse] = []
    for r, t_input, t_expected in results_rows:
        result_items.append(
            ExperimentResultResponse(
                id=r.id,
                experiment_id=r.experiment_id,
                test_case_id=r.test_case_id,
                run_id=r.run_id,
                test_input=t_input,
                expected_output=t_expected,
                actual_output=r.actual_output,
                scores=r.scores or {},
                passed=r.passed,
                status=r.status,
                error=r.error,
                duration_ms=r.duration_ms,
                evaluation_details=r.evaluation_details or [],
                created_at=r.created_at,
            )
        )

    pass_rate = (
        round(exp.passed_cases / exp.total_cases, 4)
        if exp.total_cases > 0
        else None
    )

    return ExperimentDetailResponse(
        id=exp.id,
        project_id=exp.project_id,
        dataset_id=exp.dataset_id,
        dataset_name=dataset_name,
        name=exp.name,
        description=exp.description,
        status=exp.status,
        agent_name=exp.agent_name,
        agent_version=exp.agent_version,
        config=exp.config or {},
        summary=exp.summary,
        total_cases=exp.total_cases,
        passed_cases=exp.passed_cases,
        failed_cases=exp.failed_cases,
        errored_cases=exp.errored_cases,
        score=float(exp.score) if exp.score is not None else None,
        pass_rate=pass_rate,
        started_at=exp.started_at,
        ended_at=exp.ended_at,
        created_at=exp.created_at,
        results=result_items,
    )
