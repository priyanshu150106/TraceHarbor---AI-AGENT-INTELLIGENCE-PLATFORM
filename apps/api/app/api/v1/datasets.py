"""
TraceHarbor API — Datasets & TestCases Endpoints
"""

import math
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import resolve_project_id
from app.core.database import get_db
from app.evaluation.dataset_parser import parse_and_validate_dataset_content
from app.models.dataset import Dataset
from app.models.experiment import Experiment
from app.models.project import Project
from app.models.test_case import TestCase
from app.schemas.datasets import (
    DatasetCreateRequest,
    DatasetDetailResponse,
    DatasetListResponse,
    DatasetSummaryResponse,
    DatasetUploadResponse,
    TestCaseCreate,
    TestCaseResponse,
)

router = APIRouter(tags=["Datasets"])


async def _verify_dataset_access(
    dataset_id: uuid.UUID,
    project_id: uuid.UUID | None,
    db: AsyncSession,
) -> Dataset:
    """Verify that dataset exists and belongs to the authorized project."""
    stmt = select(Dataset).where(Dataset.id == dataset_id)
    res = await db.execute(stmt)
    dataset = res.scalar_one_or_none()

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )

    if project_id and dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dataset belongs to a different project.",
        )

    return dataset


@router.post(
    "/datasets",
    response_model=DatasetSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Dataset",
)
async def create_dataset(
    payload: DatasetCreateRequest,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> DatasetSummaryResponse:
    """Create a new named dataset within an authorized project."""
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID is required to create a dataset.",
        )

    # Verify project exists
    p_stmt = select(Project).where(Project.id == project_id)
    p_res = await db.execute(p_stmt)
    if not p_res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    dataset = Dataset(
        id=uuid.uuid4(),
        project_id=project_id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(dataset)

    # Add initial cases if provided
    for c in payload.cases:
        test_case = TestCase(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            input=c.input,
            expected_output=c.expected_output,
            criteria=c.criteria,
            test_metadata=c.metadata,
            tags=c.tags,
        )
        db.add(test_case)

    await db.commit()
    await db.refresh(dataset)

    return DatasetSummaryResponse(
        id=dataset.id,
        project_id=dataset.project_id,
        name=dataset.name,
        description=dataset.description,
        test_cases_count=len(payload.cases),
        experiments_count=0,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
    )


@router.get(
    "/datasets",
    response_model=DatasetListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Datasets",
)
async def list_datasets(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search by name"),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> DatasetListResponse:
    """List all datasets belonging to the authorized project with counts."""
    if not project_id:
        return DatasetListResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)

    conditions = [Dataset.project_id == project_id]
    if search:
        conditions.append(Dataset.name.ilike(f"%{search.strip()}%"))

    # Count total datasets
    count_stmt = select(func.count(Dataset.id)).where(*conditions)
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    # Query page
    stmt = (
        select(Dataset)
        .where(*conditions)
        .order_by(Dataset.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    res = await db.execute(stmt)
    datasets = res.scalars().all()

    items: list[DatasetSummaryResponse] = []
    for d in datasets:
        # Case count
        case_cnt_stmt = select(func.count(TestCase.id)).where(TestCase.dataset_id == d.id)
        case_cnt = (await db.execute(case_cnt_stmt)).scalar_one()

        # Experiment count
        exp_cnt_stmt = select(func.count(Experiment.id)).where(Experiment.dataset_id == d.id)
        exp_cnt = (await db.execute(exp_cnt_stmt)).scalar_one()

        items.append(
            DatasetSummaryResponse(
                id=d.id,
                project_id=d.project_id,
                name=d.name,
                description=d.description,
                test_cases_count=case_cnt,
                experiments_count=exp_cnt,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return DatasetListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/datasets/{dataset_id}",
    response_model=DatasetDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Dataset Detail",
)
async def get_dataset(
    dataset_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number of cases"),
    page_size: int = Query(50, ge=1, le=200, description="Cases per page"),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> DatasetDetailResponse:
    """Retrieve a dataset and its paginated test cases."""
    dataset = await _verify_dataset_access(dataset_id, project_id, db)

    # Count cases
    count_stmt = select(func.count(TestCase.id)).where(TestCase.dataset_id == dataset.id)
    total_cases = (await db.execute(count_stmt)).scalar_one()

    # Query paginated cases
    cases_stmt = (
        select(TestCase)
        .where(TestCase.dataset_id == dataset.id)
        .order_by(TestCase.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    cases_res = await db.execute(cases_stmt)
    cases = cases_res.scalars().all()

    case_items = [
        TestCaseResponse(
            id=c.id,
            dataset_id=c.dataset_id,
            input=c.input,
            expected_output=c.expected_output,
            criteria=c.criteria,
            metadata=c.test_metadata or {},
            tags=c.tags or [],
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in cases
    ]

    return DatasetDetailResponse(
        id=dataset.id,
        project_id=dataset.project_id,
        name=dataset.name,
        description=dataset.description,
        test_cases_count=total_cases,
        test_cases=case_items,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
    )


@router.post(
    "/datasets/{dataset_id}/cases",
    response_model=list[TestCaseResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Test Cases to Dataset",
)
async def add_test_cases(
    dataset_id: uuid.UUID,
    payload: list[TestCaseCreate] | TestCaseCreate = Body(...),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> list[TestCaseResponse]:
    """Add one or more test cases to an existing dataset within an authorized project."""
    dataset = await _verify_dataset_access(dataset_id, project_id, db)

    cases_to_add = payload if isinstance(payload, list) else [payload]

    # Enforce case count limit
    curr_count_stmt = select(func.count(TestCase.id)).where(TestCase.dataset_id == dataset.id)
    curr_count = (await db.execute(curr_count_stmt)).scalar_one()

    if curr_count + len(cases_to_add) > 500:
        raise HTTPException(
            status_code=422,
            detail=f"Adding {len(cases_to_add)} cases would exceed max limit of 500 cases.",
        )

    created_cases: list[TestCaseResponse] = []
    now_utc = datetime.now(UTC)
    for c in cases_to_add:
        tc = TestCase(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            input=c.input,
            expected_output=c.expected_output,
            criteria=c.criteria,
            test_metadata=c.metadata,
            tags=c.tags,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db.add(tc)
        created_cases.append(
            TestCaseResponse(
                id=tc.id,
                dataset_id=tc.dataset_id,
                input=tc.input,
                expected_output=tc.expected_output,
                criteria=tc.criteria,
                metadata=tc.test_metadata or {},
                tags=tc.tags or [],
                created_at=now_utc,
                updated_at=now_utc,
            )
        )

    await db.commit()
    return created_cases


@router.post(
    "/datasets/upload",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload & Create Dataset from CSV/JSON",
)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str | None = Form(None),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> DatasetUploadResponse:
    """Create a new dataset and import cases from a CSV or JSON file in one transaction."""
    if not project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project ID required.")

    # Read and parse file
    content = await file.read()
    filename = file.filename or "dataset.json"
    parsed_cases = parse_and_validate_dataset_content(content, filename)

    dataset = Dataset(
        id=uuid.uuid4(),
        project_id=project_id,
        name=name.strip(),
        description=description.strip() if description else None,
    )
    db.add(dataset)

    for c in parsed_cases:
        tc = TestCase(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            input=c["input"],
            expected_output=c.get("expected_output"),
            criteria=c.get("criteria"),
            test_metadata=c.get("metadata", {}),
            tags=c.get("tags", []),
        )
        db.add(tc)

    await db.commit()

    return DatasetUploadResponse(
        id=dataset.id,
        name=dataset.name,
        cases_imported=len(parsed_cases),
        message=f"Dataset '{dataset.name}' created with {len(parsed_cases)} test cases from {filename}.",
    )


@router.post(
    "/datasets/{dataset_id}/import",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Import Cases from CSV/JSON into Existing Dataset",
)
async def import_into_dataset(
    dataset_id: uuid.UUID,
    file: UploadFile = File(...),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> DatasetUploadResponse:
    """Import additional test cases from a CSV or JSON file into an existing dataset."""
    dataset = await _verify_dataset_access(dataset_id, project_id, db)

    content = await file.read()
    filename = file.filename or "dataset.json"
    parsed_cases = parse_and_validate_dataset_content(content, filename)

    # Check total case count limit
    curr_count_stmt = select(func.count(TestCase.id)).where(TestCase.dataset_id == dataset.id)
    curr_count = (await db.execute(curr_count_stmt)).scalar_one()

    if curr_count + len(parsed_cases) > 500:
        raise HTTPException(
            status_code=422,
            detail=f"Importing {len(parsed_cases)} cases would exceed limit of 500 cases.",
        )

    for c in parsed_cases:
        tc = TestCase(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            input=c["input"],
            expected_output=c.get("expected_output"),
            criteria=c.get("criteria"),
            test_metadata=c.get("metadata", {}),
            tags=c.get("tags", []),
        )
        db.add(tc)

    await db.commit()

    return DatasetUploadResponse(
        id=dataset.id,
        name=dataset.name,
        cases_imported=len(parsed_cases),
        message=f"Imported {len(parsed_cases)} cases into '{dataset.name}'.",
    )


@router.delete(
    "/datasets/{dataset_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Dataset",
)
async def delete_dataset(
    dataset_id: uuid.UUID,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete a dataset and all associated test cases and experiments."""
    dataset = await _verify_dataset_access(dataset_id, project_id, db)

    await db.delete(dataset)
    await db.commit()

    return {
        "status": "deleted",
        "id": str(dataset_id),
        "message": f"Dataset '{dataset.name}' and all associated test cases deleted successfully.",
    }
