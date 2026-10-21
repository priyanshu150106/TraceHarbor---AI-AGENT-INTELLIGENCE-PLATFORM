"""
TraceHarbor SDK — Span Context Manager & Handle
"""

import time
import traceback
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from traceharbor.context import (
    get_current_run_id,
    get_current_span_id,
    set_current_run_id,
    set_current_span_id,
)
from traceharbor.models import SpanData
from traceharbor.truncation import redact_sensitive_data, truncate_value


class SpanHandle:
    """
    Handle returned by context managers allowing fine-grained control
    over span inputs, outputs, tokens, cost, and metadata.
    """

    def __init__(
        self,
        name: str,
        span_type: str = "agent",
        run_id: uuid.UUID | None = None,
        parent_span_id: uuid.UUID | None = None,
        client: Any = None,
    ) -> None:
        self.client = client
        self.span_id = uuid.uuid4()
        self.run_id = run_id or get_current_run_id() or uuid.uuid4()
        self.parent_span_id = parent_span_id or get_current_span_id()
        self.name = name
        self.span_type = span_type
        self.status = "running"
        self.input: dict[str, Any] | None = None
        self.output: dict[str, Any] | None = None
        self.error: str | None = None
        self.model: str | None = None
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.total_tokens: int = 0
        self.cost_usd: Decimal = Decimal("0.000000")
        self.metadata: dict[str, Any] = {}
        self.started_at: datetime = datetime.now(timezone.utc)
        self.ended_at: datetime | None = None
        self._start_perf: float = time.perf_counter()

        self._prev_run_token: Any = None
        self._prev_span_token: Any = None

    def set_input(self, data: Any) -> "SpanHandle":
        """Capture span input with redaction and truncation."""
        if not isinstance(data, dict):
            data = {"value": data}
        redacted = redact_sensitive_data(data)
        self.input = truncate_value(redacted)
        return self

    def set_output(self, data: Any) -> "SpanHandle":
        """Capture span output with redaction and truncation."""
        if not isinstance(data, dict):
            data = {"value": data}
        redacted = redact_sensitive_data(data)
        self.output = truncate_value(redacted)
        return self

    def set_error(self, err: Exception | str) -> "SpanHandle":
        """Record error message and stack trace on the span."""
        self.status = "error"
        if isinstance(err, Exception):
            self.error = f"{type(err).__name__}: {str(err)}\n{traceback.format_exc()}"
        else:
            self.error = str(err)
        return self

    def set_tokens(
        self,
        prompt: int = 0,
        completion: int = 0,
        total: int = 0,
        cost_usd: Decimal | float = Decimal("0.000000"),
        model: str | None = None,
    ) -> "SpanHandle":
        """Record token usage, estimated cost, and model identifier."""
        self.prompt_tokens = prompt
        self.completion_tokens = completion
        self.total_tokens = total or (prompt + completion)
        self.cost_usd = Decimal(str(cost_usd))
        if model:
            self.model = model
        return self

    def set_metadata(self, key_or_dict: str | dict[str, Any], value: Any = None) -> "SpanHandle":
        """Attach arbitrary metadata key-values to the span."""
        if isinstance(key_or_dict, dict):
            self.metadata.update(key_or_dict)
        else:
            self.metadata[key_or_dict] = value
        return self

    def __enter__(self) -> "SpanHandle":
        self._prev_run_id = get_current_run_id()
        self._prev_span_id = get_current_span_id()
        set_current_run_id(self.run_id)
        set_current_span_id(self.span_id)
        self.started_at = datetime.now(timezone.utc)
        self._start_perf = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        duration_ms = int((time.perf_counter() - self._start_perf) * 1000)
        self.ended_at = datetime.now(timezone.utc)

        if exc_val is not None:
            self.status = "error"
            self.error = f"{exc_type.__name__ if exc_type else 'Error'}: {str(exc_val)}"
        elif self.status == "running":
            self.status = "completed"

        # Restore previous context
        set_current_run_id(self._prev_run_id)
        set_current_span_id(self._prev_span_id)


        # Enqueue span telemetry to transport
        if self.client and hasattr(self.client, "enqueue_span"):
            span_data = SpanData(
                id=self.span_id,
                run_id=self.run_id,
                parent_span_id=self.parent_span_id,
                name=self.name,
                span_type=self.span_type,
                status=self.status,
                input=self.input,
                output=self.output,
                error=self.error,
                model=self.model,
                prompt_tokens=self.prompt_tokens,
                completion_tokens=self.completion_tokens,
                total_tokens=self.total_tokens,
                cost_usd=self.cost_usd,
                duration_ms=duration_ms,
                started_at=self.started_at,
                ended_at=self.ended_at,
                metadata=self.metadata,
            )
            self.client.enqueue_span(span_data)
