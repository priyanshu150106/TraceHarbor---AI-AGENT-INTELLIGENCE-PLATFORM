"""
TraceHarbor API — Projects Read Endpoints
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
    db: AsyncSession = Depends(get_db),
) -> list[ProjectResponse]:
    """
    Retrieve all projects along with their total recorded run counts.
    Safe for dashboard consumption; never exposes API key hashes or credentials.
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
        .group_by(Project.id, Project.name, Project.description, Project.created_at)
        .order_by(Project.created_at.desc())
    )
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
