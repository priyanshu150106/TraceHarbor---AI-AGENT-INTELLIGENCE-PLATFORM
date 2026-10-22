"""
TraceHarbor API — Safety & Red-Teaming Endpoints

Provides REST endpoints for safety benchmarks, datasets, campaign execution,
per-case inspection with redacted evidence, and version regression comparison.
"""

import math
import uuid
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import resolve_project_id
from app.core.database import get_db
from app.evaluation.agent_registry import agent_registry
from app.models.dataset import Dataset
from app.models.project import Project
from app.models.safety import SafetyCampaign, SafetyTestResult
from app.models.test_case import TestCase
from app.safety.comparison import compare_safety_campaigns
from app.safety.dataset_parser import parse_and_validate_safety_dataset_content
from app.safety.runner import run_safety_campaign_task
from app.schemas.safety import (
    SafetyCampaignCreateRequest,
    SafetyCampaignDetailResponse,
    SafetyCampaignListResponse,
    SafetyCampaignSummaryResponse,
    SafetyDatasetCreateRequest,
    SafetyOverviewResponse,
    SafetyTestCaseCreate,
    SafetyTestResultResponse,
)

router = APIRouter(tags=["Safety & Red-Teaming"])


@router.get(
    "/safety/overview",
    response_model=SafetyOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Safety Dashboard Overview",
)
async def get_safety_overview(
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> SafetyOverviewResponse:
    """Retrieve top-level safety metrics, category pass rates, and recent campaigns."""
    if not project_id:
        return SafetyOverviewResponse(
            total_campaigns=0,
            overall_safety_pass_rate=None,
            total_critical_failures=0,
            recent_campaigns=[],
            category_breakdown={},
            severity_breakdown={},
        )

    # 1. Fetch campaigns for this project
    c_stmt = (
        select(SafetyCampaign, Dataset.name.label("dataset_name"))
        .join(Dataset, SafetyCampaign.dataset_id == Dataset.id)
        .where(SafetyCampaign.project_id == project_id)
        .order_by(desc(SafetyCampaign.created_at))
    )
    c_res = await db.execute(c_stmt)
    rows = c_res.all()

    total_campaigns = len(rows)
    completed_campaigns = [c for c, _ in rows if c.status == "completed"]

    total_tests = sum(c.total_tests for c in completed_campaigns)
    passed_tests = sum(c.passed_tests for c in completed_campaigns)
    critical_failures = sum(c.critical_failures for c in completed_campaigns)

    overall_pass_rate = (
        round(passed_tests / total_tests, 4)
        if total_tests > 0
        else None
    )

    # Aggregate category & severity breakdown across completed campaigns
    category_totals: dict[str, dict[str, Any]] = {}
    severity_totals: dict[str, dict[str, int]] = {
        "critical": {"total": 0, "failed": 0},
        "high": {"total": 0, "failed": 0},
        "medium": {"total": 0, "failed": 0},
        "low": {"total": 0, "failed": 0},
    }

    for c in completed_campaigns:
        cat_scores = c.category_scores or {}
        for cat, val in cat_scores.items():
            if cat not in category_totals:
                category_totals[cat] = {"total": 0, "passed": 0, "failed": 0}
            category_totals[cat]["total"] += val.get("total", 0)
            category_totals[cat]["passed"] += val.get("passed", 0)
            category_totals[cat]["failed"] += val.get("failed", 0)

        sev_summary = c.severity_summary or {}
        for sev, val in sev_summary.items():
            if sev in severity_totals:
                severity_totals[sev]["total"] += val.get("total", 0)
                severity_totals[sev]["failed"] += val.get("failed", 0)

    # Compute pass rates for categories
    for val in category_totals.values():
        tot = val["total"]
        pas = val["passed"]
        val["pass_rate"] = round(pas / tot, 4) if tot > 0 else 0.0

    recent_campaigns: list[SafetyCampaignSummaryResponse] = []
    for c, d_name in rows[:5]:
        recent_campaigns.append(
            SafetyCampaignSummaryResponse(
                id=c.id,
                project_id=c.project_id,
                dataset_id=c.dataset_id,
                dataset_name=d_name,
                name=c.name,
                description=c.description,
                status=c.status,
                agent_name=c.agent_name,
                agent_version=c.agent_version,
                total_tests=c.total_tests,
                passed_tests=c.passed_tests,
                failed_tests=c.failed_tests,
                errored_tests=c.errored_tests,
                critical_failures=c.critical_failures,
                safety_pass_rate=float(c.safety_pass_rate) if c.safety_pass_rate is not None else None,
                started_at=c.started_at,
                ended_at=c.ended_at,
                created_at=c.created_at,
            )
        )

    return SafetyOverviewResponse(
        total_campaigns=total_campaigns,
        overall_safety_pass_rate=overall_pass_rate,
        total_critical_failures=critical_failures,
        recent_campaigns=recent_campaigns,
        category_breakdown=category_totals,
        severity_breakdown=severity_totals,
    )


@router.get(
    "/safety/agents",
    status_code=status.HTTP_200_OK,
    summary="List Approved Safety Test Target Agents",
)
async def list_approved_agents() -> list[dict[str, Any]]:
    """Return the approved agent directory for safety campaign execution."""
    return agent_registry.list_approved_agents()


@router.get(
    "/safety/datasets",
    status_code=status.HTTP_200_OK,
    summary="List Safety Datasets",
)
async def list_safety_datasets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List safety datasets with test case counts and pagination."""
    if not project_id:
        return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    # Count test cases per dataset
    cases_count_subq = (
        select(TestCase.dataset_id, func.count(TestCase.id).label("case_count"))
        .group_by(TestCase.dataset_id)
        .subquery()
    )

    query = (
        select(Dataset, func.coalesce(cases_count_subq.c.case_count, 0).label("case_count"))
        .outerjoin(cases_count_subq, Dataset.id == cases_count_subq.c.dataset_id)
        .where(Dataset.project_id == project_id)
    )

    if search:
        query = query.where(Dataset.name.ilike(f"%{search.strip()}%"))

    # Total count
    count_stmt = select(func.count(Dataset.id)).where(Dataset.project_id == project_id)
    if search:
        count_stmt = count_stmt.where(Dataset.name.ilike(f"%{search.strip()}%"))
    total = (await db.execute(count_stmt)).scalar() or 0

    # Paginated results
    offset = (page - 1) * page_size
    stmt = query.order_by(desc(Dataset.created_at)).offset(offset).limit(page_size)
    rows = (await db.execute(stmt)).all()

    items = [
        {
            "id": str(d.id),
            "project_id": str(d.project_id),
            "name": d.name,
            "description": d.description,
            "dataset_type": d.dataset_type,
            "case_count": count,
            "created_at": d.created_at.isoformat(),
            "updated_at": d.updated_at.isoformat(),
        }
        for d, count in rows
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.post(
    "/safety/datasets",
    status_code=status.HTTP_201_CREATED,
    summary="Create Safety Dataset",
)
async def create_safety_dataset(
    payload: SafetyDatasetCreateRequest,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new safety dataset with typed adversarial test cases."""
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID is required to create a safety dataset.",
        )

    p_stmt = select(Project).where(Project.id == project_id)
    if not (await db.execute(p_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    dataset = Dataset(
        id=uuid.uuid4(),
        project_id=project_id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        dataset_type="safety",
    )
    db.add(dataset)

    # Add test cases if provided in payload
    for tc in payload.test_cases:
        criteria = {
            "category": tc.category,
            "severity": tc.severity,
            "expected_safe_behavior": tc.expected_safe_behavior,
        }
        if tc.evaluation_method:
            criteria["evaluation_method"] = tc.evaluation_method
        if tc.tool_restrictions:
            criteria.update(tc.tool_restrictions)
        if tc.metadata:
            criteria.update(tc.metadata)

        test_case_record = TestCase(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            input=tc.adversarial_input,
            expected_output=tc.expected_safe_behavior,
            criteria=criteria,
            test_metadata={
                "test_case_id": tc.test_case_id,
                "category": tc.category,
                "severity": tc.severity,
                "description": tc.description,
                "expected_safe_behavior": tc.expected_safe_behavior,
                **(tc.metadata or {}),
            },
            tags=tc.tags or [tc.category, tc.severity],
        )
        db.add(test_case_record)

    await db.commit()
    await db.refresh(dataset)

    return {
        "id": str(dataset.id),
        "project_id": str(dataset.project_id),
        "name": dataset.name,
        "description": dataset.description,
        "dataset_type": dataset.dataset_type,
        "case_count": len(payload.test_cases),
        "created_at": dataset.created_at.isoformat(),
    }


@router.post(
    "/safety/datasets/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload Safety Dataset File (JSON or CSV)",
)
async def upload_safety_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str | None = Form(None),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload and strictly validate a safety red-teaming dataset from CSV or JSON."""
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID is required to upload a dataset.",
        )

    raw_bytes = await file.read()
    filename = file.filename or "safety_dataset.json"

    # Validate content & schema
    validated_cases = parse_and_validate_safety_dataset_content(raw_bytes, filename)

    dataset = Dataset(
        id=uuid.uuid4(),
        project_id=project_id,
        name=name.strip(),
        description=description.strip() if description else f"Imported from {filename}",
        dataset_type="safety",
    )
    db.add(dataset)

    for item in validated_cases:
        tc = SafetyTestCaseCreate(**item)
        criteria = {
            "category": tc.category,
            "severity": tc.severity,
            "expected_safe_behavior": tc.expected_safe_behavior,
        }
        if tc.evaluation_method:
            criteria["evaluation_method"] = tc.evaluation_method
        if tc.tool_restrictions:
            criteria.update(tc.tool_restrictions)
        if tc.metadata:
            criteria.update(tc.metadata)

        record = TestCase(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            input=tc.adversarial_input,
            expected_output=tc.expected_safe_behavior,
            criteria=criteria,
            test_metadata={
                "test_case_id": tc.test_case_id,
                "category": tc.category,
                "severity": tc.severity,
                "description": tc.description,
                "expected_safe_behavior": tc.expected_safe_behavior,
                **(tc.metadata or {}),
            },
            tags=tc.tags or [tc.category, tc.severity],
        )
        db.add(record)

    await db.commit()
    await db.refresh(dataset)

    return {
        "id": str(dataset.id),
        "name": dataset.name,
        "cases_imported": len(validated_cases),
        "dataset_type": dataset.dataset_type,
        "message": f"Successfully imported {len(validated_cases)} safety test cases from {filename}.",
    }


@router.get(
    "/safety/datasets/{dataset_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Safety Dataset Details",
)
async def get_safety_dataset(
    dataset_id: uuid.UUID,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve details and case count for a specific safety dataset."""
    stmt = select(Dataset).where(Dataset.id == dataset_id)
    dataset = (await db.execute(stmt)).scalar_one_or_none()

    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    if project_id and dataset.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-project access forbidden.")

    # Count cases
    count_stmt = select(func.count(TestCase.id)).where(TestCase.dataset_id == dataset_id)
    case_count = (await db.execute(count_stmt)).scalar() or 0

    return {
        "id": str(dataset.id),
        "project_id": str(dataset.project_id),
        "name": dataset.name,
        "description": dataset.description,
        "dataset_type": dataset.dataset_type,
        "case_count": case_count,
        "created_at": dataset.created_at.isoformat(),
        "updated_at": dataset.updated_at.isoformat(),
    }


@router.get(
    "/safety/datasets/{dataset_id}/cases",
    status_code=status.HTTP_200_OK,
    summary="Get Safety Dataset Test Cases",
)
async def get_safety_dataset_cases(
    dataset_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve paginated adversarial test cases for a safety dataset."""
    stmt = select(Dataset).where(Dataset.id == dataset_id)
    dataset = (await db.execute(stmt)).scalar_one_or_none()

    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    if project_id and dataset.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-project access forbidden.")

    count_stmt = select(func.count(TestCase.id)).where(TestCase.dataset_id == dataset_id)
    total = (await db.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    cases_stmt = (
        select(TestCase)
        .where(TestCase.dataset_id == dataset_id)
        .order_by(TestCase.created_at.asc())
        .offset(offset)
        .limit(page_size)
    )
    cases = (await db.execute(cases_stmt)).scalars().all()

    items = [
        {
            "id": str(c.id),
            "test_case_id": (c.test_metadata or {}).get("test_case_id", f"CASE-{str(c.id)[:8]}"),
            "category": (c.test_metadata or {}).get("category", "prompt_injection"),
            "severity": (c.test_metadata or {}).get("severity", "medium"),
            "description": (c.test_metadata or {}).get("description", ""),
            "adversarial_input": c.input,
            "expected_safe_behavior": c.expected_output,
            "criteria": c.criteria,
            "tags": c.tags or [],
            "created_at": c.created_at.isoformat(),
        }
        for c in cases
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.post(
    "/safety/campaigns",
    response_model=SafetyCampaignSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create & Launch Safety Campaign",
)
async def create_safety_campaign(
    payload: SafetyCampaignCreateRequest,
    background_tasks: BackgroundTasks,
    run_sync: bool = Query(False, description="Run campaign synchronously before returning (useful for automated testing)"),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> SafetyCampaignSummaryResponse:
    """Launch a safety benchmark campaign against an approved agent adapter."""
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID is required to launch a safety campaign.",
        )

    # 1. Validate Dataset ownership
    d_stmt = select(Dataset).where(Dataset.id == payload.dataset_id)
    dataset = (await db.execute(d_stmt)).scalar_one_or_none()

    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safety dataset not found.")
    if dataset.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Target dataset belongs to a different project.")

    # 2. Validate agent adapter
    adapter = agent_registry.get(payload.agent_name, payload.agent_version)
    if not adapter:
        approved = [f"{a['agent_name']} (v{a['agent_version']})" for a in agent_registry.list_approved_agents()]
        raise HTTPException(
            status_code=422,
            detail=f"Agent '{payload.agent_name}' version '{payload.agent_version}' is not approved. Approved: {', '.join(approved)}.",
        )

    campaign = SafetyCampaign(
        id=uuid.uuid4(),
        project_id=project_id,
        dataset_id=payload.dataset_id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        status="pending",
        agent_name=payload.agent_name.strip(),
        agent_version=payload.agent_version.strip(),
        config=payload.config or {},
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    # 3. Execution dispatch
    if run_sync:
        await run_safety_campaign_task(campaign.id)
        await db.refresh(campaign)
    else:
        background_tasks.add_task(run_safety_campaign_task, campaign.id)

    return SafetyCampaignSummaryResponse(
        id=campaign.id,
        project_id=campaign.project_id,
        dataset_id=campaign.dataset_id,
        dataset_name=dataset.name,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        agent_name=campaign.agent_name,
        agent_version=campaign.agent_version,
        total_tests=campaign.total_tests,
        passed_tests=campaign.passed_tests,
        failed_tests=campaign.failed_tests,
        errored_tests=campaign.errored_tests,
        critical_failures=campaign.critical_failures,
        safety_pass_rate=float(campaign.safety_pass_rate) if campaign.safety_pass_rate is not None else None,
        started_at=campaign.started_at,
        ended_at=campaign.ended_at,
        created_at=campaign.created_at,
    )


@router.get(
    "/safety/campaigns",
    response_model=SafetyCampaignListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Safety Campaigns",
)
async def list_safety_campaigns(
    status_filter: str | None = Query(None, alias="status"),
    agent_name: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> SafetyCampaignListResponse:
    """List safety campaigns with filtering and pagination."""
    if not project_id:
        return SafetyCampaignListResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)

    query = (
        select(SafetyCampaign, Dataset.name.label("dataset_name"))
        .join(Dataset, SafetyCampaign.dataset_id == Dataset.id)
        .where(SafetyCampaign.project_id == project_id)
    )

    if status_filter and status_filter.lower() != "all":
        query = query.where(SafetyCampaign.status == status_filter.lower())
    if agent_name:
        query = query.where(SafetyCampaign.agent_name == agent_name.strip())
    if search:
        query = query.where(SafetyCampaign.name.ilike(f"%{search.strip()}%"))

    count_stmt = select(func.count(SafetyCampaign.id)).where(SafetyCampaign.project_id == project_id)
    if status_filter and status_filter.lower() != "all":
        count_stmt = count_stmt.where(SafetyCampaign.status == status_filter.lower())
    if agent_name:
        count_stmt = count_stmt.where(SafetyCampaign.agent_name == agent_name.strip())
    if search:
        count_stmt = count_stmt.where(SafetyCampaign.name.ilike(f"%{search.strip()}%"))

    total = (await db.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    stmt = query.order_by(desc(SafetyCampaign.created_at)).offset(offset).limit(page_size)
    rows = (await db.execute(stmt)).all()

    items = [
        SafetyCampaignSummaryResponse(
            id=c.id,
            project_id=c.project_id,
            dataset_id=c.dataset_id,
            dataset_name=d_name,
            name=c.name,
            description=c.description,
            status=c.status,
            agent_name=c.agent_name,
            agent_version=c.agent_version,
            total_tests=c.total_tests,
            passed_tests=c.passed_tests,
            failed_tests=c.failed_tests,
            errored_tests=c.errored_tests,
            critical_failures=c.critical_failures,
            safety_pass_rate=float(c.safety_pass_rate) if c.safety_pass_rate is not None else None,
            started_at=c.started_at,
            ended_at=c.ended_at,
            created_at=c.created_at,
        )
        for c, d_name in rows
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return SafetyCampaignListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/safety/campaigns/{campaign_id}",
    response_model=SafetyCampaignDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Safety Campaign Details & Test Results",
)
async def get_safety_campaign(
    campaign_id: uuid.UUID,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> SafetyCampaignDetailResponse:
    """Retrieve full details of a safety campaign, including category scores, severity distribution, and all per-case results."""
    stmt = (
        select(SafetyCampaign, Dataset.name.label("dataset_name"))
        .join(Dataset, SafetyCampaign.dataset_id == Dataset.id)
        .where(SafetyCampaign.id == campaign_id)
    )
    row = (await db.execute(stmt)).first()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Safety campaign '{campaign_id}' not found.")

    campaign, dataset_name = row
    if project_id and campaign.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Safety campaign belongs to a different project.")

    # Fetch results
    r_stmt = (
        select(SafetyTestResult)
        .where(SafetyTestResult.campaign_id == campaign_id)
        .order_by(SafetyTestResult.created_at.asc())
    )
    results = (await db.execute(r_stmt)).scalars().all()

    result_items = [
        SafetyTestResultResponse(
            id=r.id,
            campaign_id=r.campaign_id,
            test_case_id=r.test_case_id,
            run_id=r.run_id,
            stable_case_id=r.stable_case_id,
            category=r.category,
            severity=r.severity,
            adversarial_input=r.adversarial_input,
            agent_output=r.agent_output,
            expected_safe_behavior=r.expected_safe_behavior,
            passed=r.passed,
            status=r.status,
            error=r.error,
            duration_ms=r.duration_ms,
            evaluator_results=r.evaluator_results or [],
            evidence=r.evidence,
            created_at=r.created_at,
        )
        for r in results
    ]

    return SafetyCampaignDetailResponse(
        id=campaign.id,
        project_id=campaign.project_id,
        dataset_id=campaign.dataset_id,
        dataset_name=dataset_name,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        agent_name=campaign.agent_name,
        agent_version=campaign.agent_version,
        config=campaign.config or {},
        summary=campaign.summary,
        total_tests=campaign.total_tests,
        passed_tests=campaign.passed_tests,
        failed_tests=campaign.failed_tests,
        errored_tests=campaign.errored_tests,
        critical_failures=campaign.critical_failures,
        safety_pass_rate=float(campaign.safety_pass_rate) if campaign.safety_pass_rate is not None else None,
        category_scores=campaign.category_scores or {},
        severity_summary=campaign.severity_summary or {},
        started_at=campaign.started_at,
        ended_at=campaign.ended_at,
        created_at=campaign.created_at,
        results=result_items,
    )


@router.get(
    "/safety/compare",
    status_code=status.HTTP_200_OK,
    summary="Compare Two Safety Campaigns for Regressions",
)
async def compare_safety_campaign_runs(
    a: uuid.UUID = Query(..., description="Baseline safety campaign ID"),
    b: uuid.UUID = Query(..., description="Candidate safety campaign ID"),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Compare baseline safety campaign (A) against candidate safety campaign (B) to detect newly introduced safety regressions."""
    stmt_a = select(SafetyCampaign).where(SafetyCampaign.id == a)
    camp_a = (await db.execute(stmt_a)).scalar_one_or_none()

    stmt_b = select(SafetyCampaign).where(SafetyCampaign.id == b)
    camp_b = (await db.execute(stmt_b)).scalar_one_or_none()

    if not camp_a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Baseline campaign '{a}' not found.")
    if not camp_b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate campaign '{b}' not found.")

    if project_id:
        if camp_a.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Baseline campaign belongs to a different project.")
        if camp_b.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Candidate campaign belongs to a different project.")

    if camp_a.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Baseline campaign '{a}' is not completed (current status: '{camp_a.status}').",
        )
    if camp_b.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Candidate campaign '{b}' is not completed (current status: '{camp_b.status}').",
        )

    # Fetch results for both
    res_a_stmt = select(SafetyTestResult).where(SafetyTestResult.campaign_id == a)
    results_a = (await db.execute(res_a_stmt)).scalars().all()

    res_b_stmt = select(SafetyTestResult).where(SafetyTestResult.campaign_id == b)
    results_b = (await db.execute(res_b_stmt)).scalars().all()

    # Map test cases
    case_ids = {r.test_case_id for r in results_a} | {r.test_case_id for r in results_b}
    cases_stmt = select(TestCase).where(TestCase.id.in_(case_ids))
    cases = (await db.execute(cases_stmt)).scalars().all()
    test_cases_map = {
        (c.test_metadata or {}).get("test_case_id", str(c.id)): c
        for c in cases
    }

    comparison = compare_safety_campaigns(
        baseline=camp_a,
        candidate=camp_b,
        results_a=results_a,
        results_b=results_b,
        test_cases_map=test_cases_map,
    )

    return comparison
