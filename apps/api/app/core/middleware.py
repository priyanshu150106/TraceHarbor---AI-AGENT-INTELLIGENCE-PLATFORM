"""
TraceHarbor API — Request Correlation ID Middleware

Attaches a unique correlation ID to every request for end-to-end traceability
across logs, responses, and downstream services.

The correlation ID is:
1. Read from the incoming ``X-Request-ID`` header (if present)
2. Otherwise generated as a UUID4
3. Bound into structlog context for the duration of the request
4. Returned in the ``X-Request-ID`` response header
"""

import logging
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

logger = logging.getLogger("traceharbor.middleware")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns and propagates a request correlation ID and sanitizes unhandled errors."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Accept caller-provided ID or generate one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Bind into structlog context for all log entries during this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Store on request state so handlers can access it
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception(
                "Unhandled exception in request %s %s [request_id=%s]: %s",
                request.method,
                request.url.path,
                request_id,
                exc,
            )
            detail = str(exc) if settings.debug else "Internal server error"
            return JSONResponse(
                status_code=500,
                content={
                    "detail": detail,
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )

        # Echo back in response header
        response.headers["X-Request-ID"] = request_id

        return response
