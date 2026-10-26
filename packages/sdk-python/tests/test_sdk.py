"""
TraceHarbor SDK — Comprehensive Unit Test Suite
"""

import asyncio
import uuid

import pytest
from traceharbor.client import TraceHarborClient
from traceharbor.models import RunData, SpanData
from traceharbor.transport import HttpTransport
from traceharbor.truncation import redact_sensitive_data, truncate_value


class MockTransport:
    """Mock in-memory transport capturing enqueued telemetry for testing."""

    def __init__(self) -> None:
        self.enqueued_items: list[RunData | SpanData] = []
        self.flush_called = False
        self.shutdown_called = False

    def enqueue(self, item: RunData | SpanData) -> bool:
        self.enqueued_items.append(item)
        return True

    def flush(self, timeout: float = 5.0) -> None:
        self.flush_called = True

    def shutdown(self, timeout: float = 5.0) -> None:
        self.shutdown_called = True


@pytest.fixture
def test_client() -> TraceHarborClient:
    """Provides an isolated client backed by MockTransport."""
    client = TraceHarborClient(api_key="th_live_test_key_123", endpoint="http://testserver")
    mock_t = MockTransport()
    client.transport = mock_t  # type: ignore[assignment]
    return client


def test_sync_tracing(test_client: TraceHarborClient) -> None:
    """Verify synchronous function tracing creates Run and Span."""
    @test_client.trace(name="test_sync_fn", run=True)
    def add(a: int, b: int) -> int:
        return a + b

    result = add(2, 3)
    assert result == 5

    items = test_client.transport.enqueued_items  # type: ignore[attr-defined]
    assert len(items) == 2  # 1 Span, 1 Run

    spans = [i for i in items if isinstance(i, SpanData)]
    runs = [i for i in items if isinstance(i, RunData)]

    assert len(spans) == 1
    assert spans[0].name == "test_sync_fn"
    assert spans[0].status == "completed"
    assert spans[0].output == 5

    assert len(runs) == 1
    assert runs[0].name == "test_sync_fn"
    assert runs[0].status == "completed"
    assert runs[0].output == 5


@pytest.mark.asyncio
async def test_async_tracing(test_client: TraceHarborClient) -> None:
    """Verify asynchronous function tracing creates Run and Span."""
    @test_client.trace(name="test_async_fn", run=True)
    async def async_fetch(item: str) -> str:
        await asyncio.sleep(0.01)
        return f"fetched_{item}"

    res = await async_fetch("report")
    assert res == "fetched_report"

    items = test_client.transport.enqueued_items  # type: ignore[attr-defined]
    spans = [i for i in items if isinstance(i, SpanData)]
    assert len(spans) == 1
    assert spans[0].name == "test_async_fn"
    assert spans[0].status == "completed"
    assert spans[0].output == "fetched_report"


def test_parent_child_span_relationships(test_client: TraceHarborClient) -> None:
    """Verify child spans created with client.span inherit run_id and parent_span_id."""
    @test_client.trace(name="root_agent", run=True)
    def agent_workflow() -> str:
        with test_client.span("calculator_tool", span_type="tool") as tool_span:
            tool_span.set_input({"operation": "multiply", "x": 4, "y": 5})
            product = 4 * 5
            tool_span.set_output({"product": product})
            tool_span.set_tokens(prompt=10, completion=5, total=15, cost_usd=0.00005)
            return f"Result: {product}"

    ans = agent_workflow()
    assert ans == "Result: 20"

    items = test_client.transport.enqueued_items  # type: ignore[attr-defined]
    spans = [i for i in items if isinstance(i, SpanData)]
    runs = [i for i in items if isinstance(i, RunData)]

    assert len(spans) == 2  # child tool span + root agent span
    assert len(runs) == 1

    tool_span = next(s for s in spans if s.name == "calculator_tool")
    root_span = next(s for s in spans if s.name == "root_agent")

    assert tool_span.run_id == runs[0].id
    assert root_span.run_id == runs[0].id
    assert tool_span.parent_span_id == root_span.id
    assert tool_span.span_type == "tool"
    assert tool_span.total_tokens == 15


def test_exception_recording(test_client: TraceHarborClient) -> None:
    """Verify exceptions are caught, recorded as error status, and re-raised."""
    @test_client.trace(name="failing_fn", run=True)
    def faulty_call() -> None:
        raise ValueError("Invalid configuration provided")

    with pytest.raises(ValueError, match="Invalid configuration provided"):
        faulty_call()

    items = test_client.transport.enqueued_items  # type: ignore[attr-defined]
    spans = [i for i in items if isinstance(i, SpanData)]
    runs = [i for i in items if isinstance(i, RunData)]

    assert spans[0].status == "error"
    assert "ValueError: Invalid configuration provided" in spans[0].error

    assert runs[0].status == "error"
    assert "ValueError: Invalid configuration provided" in runs[0].error


def test_redaction_and_truncation() -> None:
    """Verify sensitive keys are redacted and long values are truncated."""
    payload = {
        "user": "alice",
        "api_key": "th_sk_sensitive_12345",
        "password": "supersecretpassword",
        "nested": {"access_token": "bearer_jwt_xyz", "safe_field": 42},
    }
    redacted = redact_sensitive_data(payload)
    assert redacted["user"] == "alice"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["nested"]["access_token"] == "[REDACTED]"
    assert redacted["nested"]["safe_field"] == 42

    long_str = "x" * 500
    truncated = truncate_value(long_str, limit=50)
    assert len(truncated) < 500
    assert "[truncated 450 chars]" in truncated


def test_kill_switch_behavior() -> None:
    """Verify tracing can be disabled completely via enabled=False or env var."""
    disabled_client = TraceHarborClient(api_key="key", enabled=False)
    mock_t = MockTransport()
    disabled_client.transport = mock_t  # type: ignore[assignment]

    @disabled_client.trace(name="disabled_fn", run=True)
    def compute(val: int) -> int:
        return val * 10

    res = compute(7)
    assert res == 70
    assert len(mock_t.enqueued_items) == 0  # No events recorded when disabled


def test_buffer_limits_and_overflow() -> None:
    """Verify queue drops events when capacity is exceeded without blocking or crashing."""
    transport = HttpTransport(
        endpoint="http://127.0.0.1:8000",
        api_key="test_key",
        max_queue_size=5,
    )
    transport._running = True

    # Fill queue to capacity
    for i in range(5):
        accepted = transport.enqueue(RunData(id=uuid.uuid4(), name=f"run_{i}"))
        assert accepted is True

    # 6th item exceeds capacity: must return False and not block
    overflow = transport.enqueue(RunData(id=uuid.uuid4(), name="overflow_run"))
    assert overflow is False

    transport.shutdown(timeout=0.5)


def test_flush_and_shutdown() -> None:
    """Verify flush and shutdown trigger transport lifecycle methods."""
    client = TraceHarborClient(api_key="key", endpoint="http://test")
    mock_t = MockTransport()
    client.transport = mock_t  # type: ignore[assignment]

    client.flush()
    assert mock_t.flush_called is True

    client.shutdown()
    assert mock_t.shutdown_called is True
    assert client.enabled is False


def test_telemetry_isolation_on_network_failure() -> None:
    """
    Verify application code executes normally even when telemetry transport encounters
    network errors or server unreachability.
    """
    client = TraceHarborClient(api_key="key", endpoint="http://unreachable-domain-1234.invalid")

    @client.trace(name="resilient_fn", run=True)
    def business_logic() -> str:
        return "critical_business_output"

    # Should not raise exception despite invalid endpoint
    output = business_logic()
    assert output == "critical_business_output"
    client.shutdown(timeout=0.1)


def test_disabled_client_lifecycle_and_reconfiguration() -> None:
    """Verify client with enabled=False has None transport and can reconfigure safely."""
    client = TraceHarborClient(enabled=False)
    assert client.enabled is False
    assert client.transport is None

    # Tracing should be an instant no-op and preserve function output
    @client.trace(name="disabled_test_fn", run=True)
    def compute(val: int) -> int:
        return val * 10

    assert compute(5) == 50

    # Reconfiguring should not crash with AttributeError
    client.reconfigure(api_key="new_key", enabled=False)
    assert client.transport is None
