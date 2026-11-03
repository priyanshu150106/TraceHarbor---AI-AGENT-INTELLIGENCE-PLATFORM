"""
TraceHarbor API — Projects Read Endpoints
"""

import uuid

from fastapi import APIRouter, Depends, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    _resolve_demo_project_id,
    api_key_header,
    bearer_auth,
    get_authenticated_api_key,
)
from app.core.config import settings
from app.core.database import get_db
from app.models.project import Project
from app.models.run import Run
from app.schemas.runs import ProjectResponse

router = APIRouter(tags=["Projects"])


@router.get(
    "/projects",
    response_model=list[ProjectResponse],
    status_code=status.HTTP_200_OK,
    summary="List Projects",
    response_description="List of active projects with execution run counts",
)
async def list_projects(
    request: Request,
    x_api_key: str | None = Security(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_auth),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectResponse]:
    """
    Retrieve active projects with execution run counts.

    Tenant Security:
    - In Public Demo Mode (settings.demo_mode=True):
      Returns ONLY the synthetic demo project to prevent cross-tenant discovery.
    - When authenticated with an API key:
      Returns the project associated with that API key.
    - In development / standard catalog mode (when demo_mode=False):
      Returns registered projects for workspace project selection.
      (NOTE: A multi-tenant enterprise deployment requires User-level JWT auth
      to scope projects to an authenticated user; see docs/API_ACCESS_AUDIT.md).
    """
    stmt = (
        select(
            Project.id,
            Project.name,
            Project.description,
            Project.created_at,
            func.count(Run.id).label("runs_count"),
        )
        .outerjoin(Run, Run.project_id == Project.id)
    )

    if settings.demo_mode:
        demo_id = await _resolve_demo_project_id(db)
        stmt = stmt.where(Project.id == demo_id)
    else:
        raw_key = x_api_key or (bearer.credentials if bearer else None)
        if raw_key and raw_key.strip():
            api_key = await get_authenticated_api_key(x_api_key, bearer, db)
            stmt = stmt.where(Project.id == api_key.project_id)

    stmt = stmt.group_by(
        Project.id, Project.name, Project.description, Project.created_at
    ).order_by(Project.created_at.desc())

    res = await db.execute(stmt)
    rows = res.all()

    return [
        ProjectResponse(
            id=row[0],
            name=row[1],
            description=row[2],
            created_at=row[3],
            runs_count=row[4],
        )
        for row in rows
    ]
