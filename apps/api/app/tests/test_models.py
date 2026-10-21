"""
TraceHarbor API — Models and Security Logic Tests
"""

import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.models.api_key import ApiKey
from app.models.run import Run
from app.models.span import Span
from app.models.user import User


def test_user_instantiation() -> None:
    """Test user model instantiation and default fields."""
    user = User(
        email="dev@traceharbor.local",
        password_hash="$2b$12$e8YkZp3B/...",
        display_name="Dev Engineer",
    )
    assert user.email == "dev@traceharbor.local"
    assert user.display_name == "Dev Engineer"
    assert user.is_active is True


def test_api_key_hashing_contract() -> None:
    """
    Test the security contract of API keys:
    API keys must never be stored as plaintext; only SHA-256 hash is persisted.
    Prefix (first 8 chars) is preserved for UI identification.
    """
    raw_api_key = "th_live_" + "a" * 32
    prefix = raw_api_key[:8]
    key_hash = hashlib.sha256(raw_api_key.encode("utf-8")).hexdigest()

    project_id = uuid.uuid4()
    api_key_record = ApiKey(
        project_id=project_id,
        name="Production Ingestion Key",
        key_hash=key_hash,
        key_prefix=prefix,
    )

    assert api_key_record.key_prefix == "th_live_"
    assert len(api_key_record.key_hash) == 64
    assert api_key_record.key_hash != raw_api_key
    assert api_key_record.is_active is True


def test_run_and_span_model_structure() -> None:
    """Test Run and Span model instantiation and attribute mapping."""
    run_id = uuid.uuid4()
    project_id = uuid.uuid4()
    now = datetime.now(UTC)

    run = Run(
        id=run_id,
        project_id=project_id,
        name="Test Agent Run",
        status="running",
        input={"question": "What is the capital of France?"},
        tags=["test", "qa"],
        run_metadata={"environment": "test"},
        total_tokens=150,
        total_cost_usd=Decimal("0.000300"),
        started_at=now,
    )
    assert run.id == run_id
    assert run.status == "running"
    assert run.tags == ["test", "qa"]
    assert run.run_metadata["environment"] == "test"
    assert run.total_tokens == 150

    span_id = uuid.uuid4()
    span = Span(
        id=span_id,
        run_id=run_id,
        name="openai.chat.completions.create",
        span_type="llm",
        status="completed",
        model="gpt-4o",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost_usd=Decimal("0.000300"),
        duration_ms=420,
        started_at=now,
        span_metadata={"temperature": 0.2},
    )
    assert span.id == span_id
    assert span.run_id == run_id
    assert span.span_type == "llm"
    assert span.duration_ms == 420
    assert span.span_metadata["temperature"] == 0.2
