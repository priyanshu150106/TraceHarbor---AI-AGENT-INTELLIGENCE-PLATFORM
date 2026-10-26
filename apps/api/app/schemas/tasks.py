"""
TraceHarbor API — Background Task Schemas
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskStatusResponse(BaseModel):
    task_id: str
    task_type: str
    project_id: uuid.UUID | None = None
    status: str = Field(..., description="queued, running, completed, failed, cancelled")
    progress: float = Field(0.0, ge=0.0, le=1.0)
    result: dict[str, Any] | None = None
    error: str | None = None
    retries: int = 0
    max_retries: int = 3
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskListResponse(BaseModel):
    tasks: list[TaskStatusResponse]
    total: int
