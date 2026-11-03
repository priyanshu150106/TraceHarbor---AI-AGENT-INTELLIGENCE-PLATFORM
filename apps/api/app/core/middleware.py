"""
TraceHarbor API — Request Correlation ID & Security Middlewares

Attaches a unique correlation ID to every request for end-to-end traceability
across logs, responses, and downstream services.
Enforces maximum request payload limits to protect against memory exhaustion.
"""

import json
import logging
import uuid

import structlog
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings

logger = logging.getLogger("traceharbor.middleware")


class PayloadTooLargeError(StarletteHTTPException):
    """Exception raised when streamed or declared request body exceeds maximum allowed bytes."""

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=413, detail=detail)


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
        except StarletteHTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers={"X-Request-ID": request_id},
            )
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


class ContentLengthLimitMiddleware:
    """
    Pure ASGI middleware enforcing strict maximum request payload limits.
    Protects against:
    - Declared Content-Length exceeding limit (rejected immediately without body read)
    - Missing Content-Length with chunked/streamed transfer exceeding limit (streaming abort)
    - Spoofed or misleading Content-Length headers
    - Invalid or negative Content-Length headers (HTTP 400)
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        max_bytes = settings.max_request_body_bytes

        # 1. Fast path: check declared Content-Length header
        for raw_key, raw_val in scope.get("headers", []):
            if raw_key.lower() == b"content-length":
                try:
                    content_length = int(raw_val.decode("ascii").strip())
                    if content_length < 0:
                        await self._send_response(send, 400, "Invalid negative Content-Length header.")
                        return
                    if content_length > max_bytes:
                        await self._send_response(
                            send,
                            413,
                            f"Request payload size ({content_length} bytes) exceeds "
                            f"maximum permitted limit of {max_bytes} bytes.",
                        )
                        return
                except (ValueError, UnicodeDecodeError):
                    await self._send_response(send, 400, "Invalid Content-Length header format.")
                    return
                break

        # 2. Streaming / chunked body enforcement
        bytes_received = 0
        response_started = False

        async def monitored_receive() -> Message:
            nonlocal bytes_received
            message = await receive()
            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                bytes_received += len(chunk)
                if bytes_received > max_bytes:
                    raise PayloadTooLargeError(
                        f"Request payload size ({bytes_received} bytes) exceeds "
                        f"maximum permitted limit of {max_bytes} bytes."
                    )
            return message

        async def monitored_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, monitored_receive, monitored_send)
        except PayloadTooLargeError as exc:
            if not response_started:
                await self._send_response(send, 413, exc.detail)

    @staticmethod
    async def _send_response(send: Send, status_code: int, detail: str) -> None:
        body = json.dumps({"detail": detail}).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
            "more_body": False,
        })
