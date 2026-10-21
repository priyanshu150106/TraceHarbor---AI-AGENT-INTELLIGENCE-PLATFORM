"""
TraceHarbor SDK — Core Client
"""

import functools
import inspect
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from traceharbor.context import (
    get_current_run_id,
    get_current_span_id,
    set_current_run_id,
    set_current_span_id,
)
from traceharbor.models import RunData, SpanData
from traceharbor.span import SpanHandle
from traceharbor.transport import HttpTransport
from traceharbor.truncation import redact_sensitive_data, truncate_value

logger = logging.getLogger("traceharbor.client")


class TraceHarborClient:
    """
    Main TraceHarbor SDK client.
    Handles telemetry configuration, lifecycle, background queue dispatch,
    and automatic function decorators / context managers.
    """

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        enabled: bool | None = None,
        batch_size: int = 50,
        flush_interval: float = 2.0,
        max_queue_size: int = 5000,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        truncate_limit: int = 10000,
    ) -> None:
        # Check kill-switch environment variable
        env_enabled = os.environ.get("TRACEHARBOR_ENABLED", "true").lower() not in ("0", "false", "no")
        self.enabled = env_enabled if enabled is None else (enabled and env_enabled)

        self.api_key = api_key or os.environ.get("TRACEHARBOR_API_KEY", "")
        self.endpoint = (endpoint or os.environ.get("TRACEHARBOR_ENDPOINT", "http://127.0.0.1:8000")).rstrip("/")
        self.truncate_limit = truncate_limit

        if not self.api_key and self.enabled:
            # Remain enabled but defer transport creation until init(api_key=...) is called
            self.transport = None
        elif self.enabled:
            self.transport = HttpTransport(
                endpoint=self.endpoint,
                api_key=self.api_key,
                batch_size=batch_size,
                flush_interval=flush_interval,
                max_queue_size=max_queue_size,
                max_retries=max_retries,
                backoff_factor=backoff_factor,
            )

    def reconfigure(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        enabled: bool | None = None,
        batch_size: int = 50,
        flush_interval: float = 2.0,
        max_queue_size: int = 5000,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        truncate_limit: int = 10000,
    ) -> None:
        """Reconfigure client settings and restart background transport."""
        if self.transport:
            self.transport.shutdown(timeout=1.0)
            self.transport = None

        env_enabled = os.environ.get("TRACEHARBOR_ENABLED", "true").lower() not in ("0", "false", "no")
        self.enabled = env_enabled if enabled is None else (enabled and env_enabled)
        self.api_key = api_key or os.environ.get("TRACEHARBOR_API_KEY", "")
        self.endpoint = (endpoint or os.environ.get("TRACEHARBOR_ENDPOINT", "http://127.0.0.1:8000")).rstrip("/")
        self.truncate_limit = truncate_limit

        if not self.api_key and self.enabled:
            logger.warning(
                "TraceHarbor initialized without an API key. Tracing will be inactive until configured."
            )
            self.enabled = False
        elif self.enabled:
            self.transport = HttpTransport(
                endpoint=self.endpoint,
                api_key=self.api_key,
                batch_size=batch_size,
                flush_interval=flush_interval,
                max_queue_size=max_queue_size,
                max_retries=max_retries,
                backoff_factor=backoff_factor,
            )


    def enqueue_run(self, run: RunData) -> None:
        """Enqueue run telemetry safely."""
        if self.enabled and self.transport:
            self.transport.enqueue(run)

    def enqueue_span(self, span: SpanData) -> None:
        """Enqueue span telemetry safely."""
        if self.enabled and self.transport:
            self.transport.enqueue(span)

    def span(
        self,
        name: str,
        span_type: str = "tool",
        metadata: dict[str, Any] | None = None,
    ) -> SpanHandle:
        """
        Create a fine-grained span context manager for tools, steps, or custom logic.
        """
        handle = SpanHandle(
            name=name,
            span_type=span_type,
            client=self if self.enabled else None,
        )
        if metadata:
            handle.set_metadata(metadata)
        return handle

    def trace(
        self,
        name: str | None = None,
        version: str | None = None,
        run: bool = True,
        span_type: str = "agent",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for tracing synchronous and asynchronous functions.
        If run=True (default), starts a new Run context and a root Span.
        If run=False, creates a child Span within the current active Run.
        """
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            fn_name = name or fn.__name__
            meta = dict(metadata or {})
            if version:
                meta["version"] = version

            if not self.enabled:
                # Kill switch enabled: return original function unchanged
                return fn

            if inspect.iscoroutinefunction(fn):
                @functools.wraps(fn)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    run_id = uuid.uuid4() if run or not get_current_run_id() else get_current_run_id()
                    span_id = uuid.uuid4()
                    parent_span_id = None if run else get_current_span_id()

                    prev_run = get_current_run_id()
                    prev_span = get_current_span_id()
                    set_current_run_id(run_id)
                    set_current_span_id(span_id)

                    start_time = datetime.now(timezone.utc)
                    start_perf = time.perf_counter()

                    input_data = self._capture_args(fn, args, kwargs)
                    status_str = "completed"
                    error_msg = None
                    result = None

                    try:
                        result = await fn(*args, **kwargs)
                        return result
                    except Exception as exc:
                        status_str = "error"
                        error_msg = f"{type(exc).__name__}: {str(exc)}"
                        raise
                    finally:
                        duration_ms = int((time.perf_counter() - start_perf) * 1000)
                        end_time = datetime.now(timezone.utc)
                        output_data = self._capture_result(result) if status_str == "completed" else None

                        # Emit Span
                        self.enqueue_span(
                            SpanData(
                                id=span_id,
                                run_id=run_id,
                                parent_span_id=parent_span_id,
                                name=fn_name,
                                span_type=span_type,
                                status=status_str,
                                input=input_data,
                                output=output_data,
                                error=error_msg,
                                duration_ms=duration_ms,
                                started_at=start_time,
                                ended_at=end_time,
                                metadata=meta,
                            )
                        )

                        # Emit Run if this was the root
                        if run:
                            self.enqueue_run(
                                RunData(
                                    id=run_id,
                                    name=fn_name,
                                    status=status_str,
                                    input=input_data,
                                    output=output_data,
                                    error=error_msg,
                                    tags=tags or [],
                                    metadata=meta,
                                    duration_ms=duration_ms,
                                    started_at=start_time,
                                    ended_at=end_time,
                                )
                            )

                        set_current_run_id(prev_run)
                        set_current_span_id(prev_span)

                return async_wrapper
            else:
                @functools.wraps(fn)
                def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                    run_id = uuid.uuid4() if run or not get_current_run_id() else get_current_run_id()
                    span_id = uuid.uuid4()
                    parent_span_id = None if run else get_current_span_id()

                    prev_run = get_current_run_id()
                    prev_span = get_current_span_id()
                    set_current_run_id(run_id)
                    set_current_span_id(span_id)

                    start_time = datetime.now(timezone.utc)
                    start_perf = time.perf_counter()

                    input_data = self._capture_args(fn, args, kwargs)
                    status_str = "completed"
                    error_msg = None
                    result = None

                    try:
                        result = fn(*args, **kwargs)
                        return result
                    except Exception as exc:
                        status_str = "error"
                        error_msg = f"{type(exc).__name__}: {str(exc)}"
                        raise
                    finally:
                        duration_ms = int((time.perf_counter() - start_perf) * 1000)
                        end_time = datetime.now(timezone.utc)
                        output_data = self._capture_result(result) if status_str == "completed" else None

                        # Emit Span
                        self.enqueue_span(
                            SpanData(
                                id=span_id,
                                run_id=run_id,
                                parent_span_id=parent_span_id,
                                name=fn_name,
                                span_type=span_type,
                                status=status_str,
                                input=input_data,
                                output=output_data,
                                error=error_msg,
                                duration_ms=duration_ms,
                                started_at=start_time,
                                ended_at=end_time,
                                metadata=meta,
                            )
                        )

                        # Emit Run if this was the root
                        if run:
                            self.enqueue_run(
                                RunData(
                                    id=run_id,
                                    name=fn_name,
                                    status=status_str,
                                    input=input_data,
                                    output=output_data,
                                    error=error_msg,
                                    tags=tags or [],
                                    metadata=meta,
                                    duration_ms=duration_ms,
                                    started_at=start_time,
                                    ended_at=end_time,
                                )
                            )

                        set_current_run_id(prev_run)
                        set_current_span_id(prev_span)

                return sync_wrapper

        return decorator

    def _capture_args(self, fn: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
        """Inspect and bind arguments, redacting sensitive parameters."""
        try:
            sig = inspect.signature(fn)
            bound = sig.bind_partial(*args, **kwargs)
            captured = dict(bound.arguments)
        except Exception:
            captured = {"args": list(args), "kwargs": kwargs}

        redacted = redact_sensitive_data(captured)
        return truncate_value(redacted, limit=self.truncate_limit)

    def _capture_result(self, result: Any) -> Any:
        """Capture and redact return values."""
        if result is None:
            return None
        if not isinstance(result, (dict, list, str, int, float, bool)):
            result = str(result)
        redacted = redact_sensitive_data(result)
        return truncate_value(redacted, limit=self.truncate_limit)

    def flush(self, timeout: float = 5.0) -> None:
        """Force flush all buffered telemetry to the ingestion endpoint."""
        if self.enabled and self.transport:
            self.transport.flush(timeout=timeout)

    def shutdown(self, timeout: float = 5.0) -> None:
        """Flush remaining events and terminate transport worker threads."""
        if self.enabled and self.transport:
            self.transport.shutdown(timeout=timeout)
            self.enabled = False
