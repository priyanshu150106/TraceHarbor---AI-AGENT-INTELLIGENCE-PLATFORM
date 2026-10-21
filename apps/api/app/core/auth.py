"""
TraceHarbor API — Authentication & API Key Verification
"""

import hashlib
import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.api_key import ApiKey

# Supported header authentication methods
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_auth = HTTPBearer(auto_error=False)


def hash_api_key(raw_key: str) -> str:
    """
    Compute cryptographic SHA-256 hash of raw API key.
    Raw keys are never persisted or logged in plain text.
    """
    return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()


async def get_authenticated_api_key(
    x_api_key: str | None = Security(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    """
    Authenticate an SDK client request using a project API key.
    Accepts keys via 'X-API-Key' header or 'Authorization: Bearer <key>'.
    Resolves the key to its project and updates last_used_at timestamp.
    """
    raw_key: str | None = None
    if x_api_key:
        raw_key = x_api_key
    elif bearer and bearer.credentials:
        raw_key = bearer.credentials

    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide via 'X-API-Key' header or 'Authorization: Bearer <key>'.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_hash = hash_api_key(raw_key)

    # Query active API key record
    stmt = select(ApiKey).where(
        ApiKey.key_hash == key_hash,
        ApiKey.is_active.is_(True),
    )
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Update last_used_at timestamp (safely inside current transaction)
    api_key.last_used_at = datetime.now(UTC)
    return api_key


async def resolve_project_id(
    x_api_key: str | None = Security(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_auth),
    project_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID | None:
    """
    Resolve the active project ID for read requests.
    If an API key is provided, enforces that key's project tenancy.
    If no key is provided (e.g. local development dashboard), safely falls
    back to the specified project_id or the primary active project.
    """
    raw_key = x_api_key or (bearer.credentials if bearer else None)
    if raw_key:
        api_key = await get_authenticated_api_key(x_api_key, bearer, db)
        if project_id and project_id != api_key.project_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Provided project ID does not match API key project.",
            )
        return api_key.project_id

    if project_id:
        return project_id

    # Fallback to the first existing project in database for local dashboard browsing
    from app.models.project import Project

    stmt = select(Project.id).limit(1)
    res = await db.execute(stmt)
    first_id = res.scalar_one_or_none()
    return first_id

