"""
TraceHarbor API — Background Task Management Endpoints

Endpoints for monitoring, inspecting, and cancelling asynchronous tasks
(e.g., semantic clustering, bulk embedding, sync jobs).
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import resolve_project_id
from app.core.tasks import task_manager
from app.schemas.tasks import TaskListResponse, TaskStatusResponse

router = APIRouter(prefix="/tasks", tags=["Background Tasks"])


@router.get(
    "",
    response_model=TaskListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Background Tasks",
)
async def list_tasks(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    project_id: uuid.UUID | None = Depends(resolve_project_id),
) -> TaskListResponse:
    """List recent background tasks filtered by project tenancy and optional status."""
    tasks = task_manager.list_tasks(
        project_id=project_id,
        status_filter=status_filter,
        limit=limit,
    )
    return TaskListResponse(
        tasks=[TaskStatusResponse.model_validate(t.to_dict()) for t in tasks],
        total=len(tasks),
    )


@router.get(
    "/{task_id}",
    response_model=TaskStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Background Task Status",
)
async def get_task_status(
    task_id: str,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
) -> TaskStatusResponse:
    """Retrieve status, progress, and results for a background task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )

    # Tenant isolation check: ensure task belongs to requesting project if project_id is enforced
    if project_id and task.project_id and task.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )

    return TaskStatusResponse.model_validate(task.to_dict())


@router.post(
    "/{task_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel Background Task",
)
async def cancel_task(
    task_id: str,
    project_id: uuid.UUID | None = Depends(resolve_project_id),
) -> dict[str, Any]:
    """Attempt to cancel an in-progress or queued background task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )

    if project_id and task.project_id and task.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )

    cancelled = await task_manager.cancel(task_id)
    return {
        "task_id": task_id,
        "cancelled": cancelled,
        "status": task.status,
    }
