import uuid
from contextvars import ContextVar, Token

# Context variables for tracking active trace execution across threads & async tasks
_current_run_id: ContextVar[uuid.UUID | None] = ContextVar("current_run_id", default=None)
_current_span_id: ContextVar[uuid.UUID | None] = ContextVar("current_span_id", default=None)


def get_current_run_id() -> uuid.UUID | None:
    """Return the active Run ID in the current execution context."""
    return _current_run_id.get()


def get_current_span_id() -> uuid.UUID | None:
    """Return the active Span ID in the current execution context."""
    return _current_span_id.get()


def set_current_run_id(run_id: uuid.UUID | None) -> Token[uuid.UUID | None]:
    """Set the active Run ID in the current context."""
    return _current_run_id.set(run_id)


def set_current_span_id(span_id: uuid.UUID | None) -> Token[uuid.UUID | None]:
    """Set the active Span ID in the current context."""
    return _current_span_id.set(span_id)

