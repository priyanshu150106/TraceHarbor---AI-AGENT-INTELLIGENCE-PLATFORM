"""
TraceHarbor API — Authentication & Safe Tenant Isolation
"""

import hashlib
import logging
import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.api_key import ApiKey
from app.models.project import Project

logger = logging.getLogger("traceharbor.auth")

# Supported header authentication methods
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_auth = HTTPBearer(auto_error=False)

DEMO_KEY_PREFIX = "th_demo_"
LIVE_KEY_PREFIX = "th_live_"


def hash_api_key(raw_key: str) -> str:
    """
    Compute cryptographic SHA-256 hash of raw API key.
    Raw keys are never persisted or logged in plain text.
    """
    return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()


def is_demo_api_key(api_key: ApiKey) -> bool:
    """
    Check if an API key is restricted to public demo access.
    Demo keys use the 'th_demo_' prefix and are strictly read-only.
    """
    return api_key.key_prefix == DEMO_KEY_PREFIX


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

    if not raw_key or not raw_key.strip():
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


SAFE_READ_POST_PATHS = {
    "/failures/search",
    "/v1/failures/search",
    "/api/v1/failures/search",
}


async def _resolve_demo_project_id(db: AsyncSession) -> uuid.UUID:
    """
    Find the dedicated demo project ID from settings or database.
    In production (debug=False), strictly restricts resolution to explicitly
    configured or demo-named projects. Never falls back to arbitrary customer data.
    """
    if settings.demo_project_id:
        try:
            demo_uuid = uuid.UUID(settings.demo_project_id)
            stmt = select(Project.id).where(Project.id == demo_uuid)
            res = await db.execute(stmt)
            if res.scalar_one_or_none():
                return demo_uuid
            logger.error(
                "DEMO_PROJECT_ID '%s' was not found in database.", settings.demo_project_id
            )
        except ValueError:
            logger.error("Invalid DEMO_PROJECT_ID UUID format: %s", settings.demo_project_id)

    # Query for project with 'demo' in name
    stmt = select(Project.id).where(Project.name.ilike("%demo%")).limit(1)
    res = await db.execute(stmt)
    demo_id = res.scalar_one_or_none()
    if demo_id:
        return demo_id

    # Fallback to first project ONLY in local development debug mode
    if settings.debug:
        fallback_stmt = select(Project.id).limit(1)
        fallback_res = await db.execute(fallback_stmt)
        first_id = fallback_res.scalar_one_or_none()
        if first_id:
            logger.warning(
                "Falling back to first project as demo project (debug mode only)"
            )
            return first_id

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No demo project is configured or available.",
    )


async def resolve_project_id(
    request: Request,
    x_api_key: str | None = Security(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_auth),
    project_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID | None:
    """
    Resolve and authorize the active project ID for incoming requests.

    Security & Access Rules:
    1. Authenticated with Live Key ('th_live_'):
       - Full read & write permissions within its own project.
       - Rejects cross-tenant access (403).
    2. Authenticated with Demo Key ('th_demo_'):
       - Strictly read-only ('GET', 'HEAD', 'OPTIONS' + safe search).
       - Rejects all mutations ('POST', 'PUT', 'DELETE', 'PATCH') with 403.
       - Rejects cross-tenant access with 403.
    3. Unauthenticated (no API key):
       - If a mutation is attempted without a key:
         * 403 if in demo mode; 401 otherwise.
       - If in Public Demo Mode (settings.demo_mode=True):
         * Permits safe read-only browsing scoped to the demo project.
         * Rejects attempts to query other projects with 403.
       - If in Development Mode (settings.debug=True):
         * Falls back to first project for local dashboard development.
       - If in Standard Production Mode (debug=False, demo_mode=False):
         * Strictly rejects unauthenticated requests with 401.
    """
    raw_key = x_api_key or (bearer.credentials if bearer else None)
    is_safe_read_post = request.url.path in SAFE_READ_POST_PATHS
    is_mutation = (
        request.method in ("POST", "PUT", "PATCH", "DELETE")
        and not is_safe_read_post
    )

    # -------------------------------------------------------------
    # 1. Authenticated Request
    # -------------------------------------------------------------
    if raw_key and raw_key.strip():
        api_key = await get_authenticated_api_key(x_api_key, bearer, db)
        is_demo = is_demo_api_key(api_key)

        # Enforce read-only restriction on demo keys
        if is_demo and is_mutation:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Demo credentials are restricted to read-only access. Mutation operations are prohibited.",
            )

        # Enforce tenant isolation boundary
        if project_id and project_id != api_key.project_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Provided project ID does not match API key project.",
            )
        return api_key.project_id

    # -------------------------------------------------------------
    # 2. Unauthenticated Mutation Attempt (Always Blocked)
    # -------------------------------------------------------------
    if is_mutation:
        if settings.demo_mode:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Public demo access is strictly read-only. Mutation operations are prohibited.",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required for mutation operations.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # -------------------------------------------------------------
    # 3. Unauthenticated Read / Safe Query Request
    # -------------------------------------------------------------
    # A. Public Demo Mode (Portfolio showcase)
    if settings.demo_mode:
        demo_id = await _resolve_demo_project_id(db)
        if project_id and project_id != demo_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Public demo access cannot access other project data.",
            )
        return demo_id

    # B. Development Mode (Local browsing convenience)
    if settings.debug:
        logger.warning(
            "Unauthenticated request falling back to first project (debug mode only)"
        )
        if project_id:
            return project_id
        stmt = select(Project.id).limit(1)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    # C. Production Mode (Strict Authentication Enforced)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API key or explicit project_id required in production mode.",
        headers={"WWW-Authenticate": "ApiKey"},
    )
