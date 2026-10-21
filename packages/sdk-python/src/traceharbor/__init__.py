"""
TraceHarbor Python SDK — Observe. Evaluate. Secure.

Client-side observability, evaluation, and security telemetry for AI Agents.
"""

import atexit
from typing import Any, Callable

from traceharbor.client import TraceHarborClient
from traceharbor.context import get_current_run_id, get_current_span_id
from traceharbor.span import SpanHandle

__version__ = "0.1.0"

_default_client: TraceHarborClient | None = None


def init(
    api_key: str | None = None,
    endpoint: str | None = None,
    enabled: bool | None = None,
    batch_size: int = 50,
    flush_interval: float = 2.0,
    max_queue_size: int = 5000,
    max_retries: int = 3,
    backoff_factor: float = 0.5,
    truncate_limit: int = 10000,
) -> TraceHarborClient:
    """
    Initialize or reconfigure the global TraceHarbor SDK client.
    Should be called once at application startup.
    """
    global _default_client
    if _default_client is None:
        _default_client = TraceHarborClient(
            api_key=api_key,
            endpoint=endpoint,
            enabled=enabled,
            batch_size=batch_size,
            flush_interval=flush_interval,
            max_queue_size=max_queue_size,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            truncate_limit=truncate_limit,
        )
    else:
        _default_client.reconfigure(
            api_key=api_key,
            endpoint=endpoint,
            enabled=enabled,
            batch_size=batch_size,
            flush_interval=flush_interval,
            max_queue_size=max_queue_size,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            truncate_limit=truncate_limit,
        )
    return _default_client



def get_client() -> TraceHarborClient:
    """Return the global client or initialize a fallback client if none exists."""
    global _default_client
    if _default_client is None:
        _default_client = TraceHarborClient()
    return _default_client


def trace(
    name: str | None = None,
    version: str | None = None,
    run: bool = True,
    span_type: str = "agent",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Callable[..., Any]:
    """
    Decorator for tracing synchronous or asynchronous functions.

    Example:
        @traceharbor.trace(name="support_agent", version="1.0")
        def answer(question: str) -> str:
            return "Example response"
    """
    client = get_client()
    return client.trace(
        name=name,
        version=version,
        run=run,
        span_type=span_type,
        tags=tags,
        metadata=metadata,
    )


def span(
    name: str,
    span_type: str = "tool",
    metadata: dict[str, Any] | None = None,
) -> SpanHandle:
    """
    Context manager for fine-grained tracing of steps, tool executions, or LLM calls.

    Example:
        with traceharbor.span("search_kb", span_type="tool") as s:
            s.set_input({"query": query})
            res = execute_tool()
            s.set_output({"result": res})
    """
    client = get_client()
    return client.span(name=name, span_type=span_type, metadata=metadata)


def flush(timeout: float = 5.0) -> None:
    """Force flush all buffered telemetry to the backend."""
    if _default_client is not None:
        _default_client.flush(timeout=timeout)


def shutdown(timeout: float = 5.0) -> None:
    """Flush pending telemetry and stop background transport threads."""
    global _default_client
    if _default_client is not None:
        _default_client.shutdown(timeout=timeout)
        _default_client = None


# Ensure clean flush on interpreter exit
atexit.register(shutdown)

__all__ = [
    "init",
    "get_client",
    "trace",
    "span",
    "flush",
    "shutdown",
    "get_current_run_id",
    "get_current_span_id",
    "TraceHarborClient",
    "SpanHandle",
    "__version__",
]
