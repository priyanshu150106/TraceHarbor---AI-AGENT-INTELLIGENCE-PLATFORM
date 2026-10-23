"""
TraceHarbor API — Failure Intelligence & Semantic Clustering Tests (Phase 6)

Comprehensive test suite covering:
- Redaction of PII, credentials, tokens, URLs, and file paths
- Failure event normalization across runs, spans, experiments, and safety test results
- Idempotent failure ingestion (no duplicates on repeated sync)
- Fake embedding provider determinism and validation
- Cosine similarity threshold boundaries with known vectors
- Lexical similarity fallback
- Single-pass incremental clustering assignment and metadata aggregation
- Cluster status transitions and audit log (ClusterStatusChange)
- Similarity search (vector and lexical fallback)
- Project / tenant isolation on all failure endpoints
"""

import math
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.failures.clustering import (
    assign_events_to_clusters,
    compute_cluster_metadata,
    cosine_similarity,
    generate_cluster_title,
    lexical_similarity,
)
from app.failures.embedding import FakeEmbeddingProvider, validate_embedding
from app.failures.normalizer import (
    normalize_experiment_result_failure,
    normalize_run_failure,
    normalize_safety_test_failure,
    normalize_span_failure,
)
from app.failures.redaction import (
    normalize_error_text,
    redact_text,
    sanitize_error_summary,
)
from app.tests.conftest import (
    OTHER_PROJECT_API_KEY,
    TEST_API_KEY,
)

# ------------------- 1. Redaction & Normalization Unit Tests -------------------


def test_redaction_sanitization() -> None:
    """Verify sensitive credentials, keys, IPs, emails, and file paths are stripped."""
    raw = (
        "Fatal error in https://alice:secret123@api.openai.com/v1?token=sk-99999\n"
        "Contact engineer at dev@traceharbor.internal or call 555-123-4567.\n"
        "Failed reading C:\\Users\\priya\\secret_file.json or /home/ubuntu/app/secrets.env\n"
        "Client IP 192.168.1.50:8000 sent bearer token: Bearer eyJhbGciOiJIUzI1NiJ9.test"
    )
    redacted = redact_text(raw)

    assert "secret123" not in redacted
    assert "[CREDENTIALS_REDACTED]" in redacted
    assert "sk-99999" not in redacted
    assert "dev@traceharbor.internal" not in redacted
    assert "[EMAIL_REDACTED]" in redacted
    assert "555-123-4567" not in redacted
    assert "[PHONE_REDACTED]" in redacted
    assert "C:\\Users\\priya" not in redacted
    assert "[PATH_REDACTED]" in redacted
    assert "192.168.1.50" not in redacted
    assert "[IP_REDACTED]" in redacted


def test_normalization_and_summary() -> None:
    """Verify normalization strips line numbers, memory addresses, and stabilizes error text."""
    raw = "ConnectionError at 0x7fff5fbff820 line 42 at 10:20: failed to connect to host"
    normalized = normalize_error_text(raw)

    assert "0xaddr" in normalized
    assert "line n" in normalized
    assert "at n:n" in normalized
    assert normalized.islower()

    summary = sanitize_error_summary(raw, max_length=50)
    assert len(summary) <= 50


# ------------------- 2. Normalizer Unit Tests -------------------


def test_failure_event_normalizers() -> None:
    """Verify normalization from runs, spans, experiments, and safety test results."""
    proj_id = uuid.uuid4()
    run_id = uuid.uuid4()
    now = datetime.now(UTC)

    # Run failure
    run_data = normalize_run_failure(
        run_id=run_id,
        project_id=proj_id,
        error="ConnectionRefusedError: Connection refused",
        started_at=now,
        metadata={"agent_name": "SupportBot", "version": "1.2.0"},
    )
    assert run_data.source_type == "run"
    assert run_data.agent_name == "SupportBot"
    assert run_data.agent_version == "1.2.0"
    assert run_data.severity == "high"
    assert run_data.content_hash is not None

    # Span failure
    span_id = uuid.uuid4()
    span_data = normalize_span_failure(
        span_id=span_id,
        run_id=run_id,
        project_id=proj_id,
        error="Tool call timed out after 30s",
        span_type="tool",
        span_name="search_web",
        model="gpt-4o",
        started_at=now,
    )
    assert span_data.source_type == "span"
    assert span_data.failure_category == "tool_error"
    assert span_data.model_name == "gpt-4o"

    # Experiment failure
    exp_data = normalize_experiment_result_failure(
        result_id=uuid.uuid4(),
        project_id=proj_id,
        error="AssertionError: Expected 200 OK",
        status="failed",
        experiment_name="Regression Test Suite",
        agent_name="AnalystAgent",
        agent_version="2.0",
        run_id=None,
        created_at=now,
    )
    assert exp_data.failure_category == "eval_failure"

    # Safety failure
    safety_data = normalize_safety_test_failure(
        result_id=uuid.uuid4(),
        project_id=proj_id,
        error="Canary leaked in response",
        category="prompt_injection",
        severity="critical",
        agent_name="Assistant",
        agent_version="1.0",
        campaign_name="Red Team Baseline",
        run_id=None,
        created_at=now,
    )
    assert safety_data.failure_category == "safety_failure"
    assert safety_data.severity == "critical"


# ------------------- 3. Embedding Provider Tests -------------------


@pytest.mark.asyncio
async def test_fake_embedding_provider() -> None:
    """Verify FakeEmbeddingProvider produces deterministic, valid unit vectors."""
    provider = FakeEmbeddingProvider(dimensions=64)
    assert provider.dimensions == 64
    assert provider.provider_name == "fake"

    vecs = await provider.embed_texts(["Error 1", "Error 1", "Error 2"])
    assert len(vecs) == 3

    # Identical texts produce identical vectors
    assert vecs[0] == vecs[1]
    # Different texts produce different vectors
    assert vecs[0] != vecs[2]

    # Validate unit vector norm ~ 1.0
    for vec in vecs:
        assert validate_embedding(vec, expected_dims=64)
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-4


# ------------------- 4. Cosine Similarity & Boundaries Tests -------------------


def test_cosine_similarity_boundaries() -> None:
    """Verify cosine similarity mathematical boundaries with known vectors."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    v4 = [-1.0, 0.0, 0.0]

    # Identical: 1.0
    assert abs(cosine_similarity(v1, v2) - 1.0) < 1e-6
    # Orthogonal: 0.0
    assert abs(cosine_similarity(v1, v3) - 0.0) < 1e-6
    # Opposite: -1.0
    assert abs(cosine_similarity(v1, v4) - (-1.0)) < 1e-6

    # Dimension mismatch raises ValueError
    with pytest.raises(ValueError):
        cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])


def test_lexical_similarity_fallback() -> None:
    """Verify lexical similarity fallback token Jaccard calculation."""
    s1 = "database connection timeout error"
    s2 = "database connection timeout exception"
    s3 = "unrelated syntax error in parser"

    high = lexical_similarity(s1, s2)
    low = lexical_similarity(s1, s3)

    assert high > 0.5
    assert low < 0.2
    assert lexical_similarity("", "abc") == 0.0


# ------------------- 5. Clustering Algorithm & Metadata Tests -------------------


def test_clustering_assignment_and_min_cluster_size() -> None:
    """Verify single-pass incremental clustering with threshold and min_cluster_size."""
    e1_id = uuid.uuid4()
    e2_id = uuid.uuid4()
    e3_id = uuid.uuid4()

    # e1 and e2 have identical vectors; e3 has an orthogonal vector
    v_a = [1.0, 0.0, 0.0, 0.0]
    v_b = [0.0, 1.0, 0.0, 0.0]

    events = [
        (e1_id, v_a, {"severity": "high", "error_summary": "Timeout in API", "occurred_at": datetime.now(UTC)}),
        (e2_id, v_a, {"severity": "critical", "error_summary": "Timeout in API again", "occurred_at": datetime.now(UTC)}),
        (e3_id, v_b, {"severity": "low", "error_summary": "Parser warning", "occurred_at": datetime.now(UTC)}),
    ]

    res = assign_events_to_clusters(
        events_with_embeddings=events,
        existing_clusters=[],
        threshold=0.85,
        min_cluster_size=2,
    )

    # e1 and e2 form a cluster of size 2
    assert len(res["new_clusters"]) == 1
    # e3 has size 1 (< min_cluster_size=2), so remains unassigned
    assert e3_id in res["unassigned"]
    assert res["assignments"][e1_id] == res["assignments"][e2_id]


def test_cluster_title_and_metadata_computation() -> None:
    """Verify cluster title and aggregated metadata."""
    summaries = [
        "TypeError: unsupported operand type for +",
        "TypeError: cannot concatenate 'str' and 'int'",
    ]
    title = generate_cluster_title(summaries)
    assert "TypeError" in title

    events = [
        {
            "severity": "critical",
            "failure_category": "runtime_error",
            "agent_name": "OrderBot",
            "agent_version": "1.0",
            "model_name": "gpt-4o",
            "run_id": uuid.uuid4(),
            "trace_id": "tr_1",
            "error_summary": summaries[0],
            "occurred_at": datetime(2026, 10, 20, 10, 0, tzinfo=UTC),
        },
        {
            "severity": "high",
            "failure_category": "runtime_error",
            "agent_name": "OrderBot",
            "agent_version": "1.1",
            "model_name": "gpt-4o",
            "run_id": uuid.uuid4(),
            "trace_id": "tr_2",
            "error_summary": summaries[1],
            "occurred_at": datetime(2026, 10, 20, 11, 0, tzinfo=UTC),
        },
    ]

    meta = compute_cluster_metadata(events)
    assert meta["dominant_category"] == "runtime_error"
    assert meta["event_count"] == 2
    assert meta["severity_distribution"] == {"critical": 1, "high": 1}
    assert "OrderBot@1.0" in meta["affected_agents"]
    assert "OrderBot@1.1" in meta["affected_agents"]
    assert len(meta["representative_traces"]) == 2


# ------------------- 6. API Integration Tests: Sync & Idempotency -------------------


@pytest.mark.asyncio
async def test_failure_sync_and_idempotency(client: AsyncClient) -> None:
    """Verify that syncing failed runs creates failure events, and repeated sync creates 0 duplicates."""
    headers = {"X-API-Key": TEST_API_KEY}

    # 1. Ingest a failed run
    run_id = str(uuid.uuid4())
    ingest_payload = {
        "runs": [
            {
                "id": run_id,
                "name": "Failed Payment Agent",
                "status": "error",
                "error": "PaymentGatewayTimeout: Stripe API did not respond in 5000ms",
                "started_at": datetime.now(UTC).isoformat(),
                "metadata": {"agent": "PaymentAgent", "version": "3.1.0"},
            }
        ]
    }
    res_ingest = await client.post("/v1/ingest/spans", json=ingest_payload, headers=headers)
    assert res_ingest.status_code == 200

    # 2. First Sync
    res_sync1 = await client.post("/v1/failures/sync", json={"auto_embed": False}, headers=headers)
    assert res_sync1.status_code == 200
    data1 = res_sync1.json()
    assert data1["scanned"] >= 1
    assert data1["created"] >= 1

    # 3. Second Sync: must be strictly idempotent
    res_sync2 = await client.post("/v1/failures/sync", json={"auto_embed": False}, headers=headers)
    assert res_sync2.status_code == 200
    data2 = res_sync2.json()
    assert data2["created"] == 0
    assert data2["skipped"] >= 1

    # 4. Verify Failure Event listing
    res_list = await client.get("/v1/failures", headers=headers)
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total"] >= 1
    ev = list_data["items"][0]
    assert "PaymentGatewayTimeout" in ev["error_summary"]
    assert ev["source_type"] == "run"
    assert ev["agent_name"] == "PaymentAgent"


# ------------------- 7. API Integration Tests: Clustering & Status Transitions -------------------


@pytest.mark.asyncio
async def test_clustering_job_and_status_transitions(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify clustering job execution, cluster status change, and audit trail."""
    # Enable fake embedding provider for deterministic clustering in tests
    from app.core.config import settings
    monkeypatch.setattr(settings, "embedding_provider", "fake")
    monkeypatch.setattr(settings, "embedding_dimensions", 64)

    headers = {"X-API-Key": TEST_API_KEY}

    # 1. Ingest 2 identical failed runs so they form a cluster
    run1 = str(uuid.uuid4())
    run2 = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()
    err_text = "DatabaseLockTimeout: deadlock detected on resource rows"

    ingest_payload = {
        "runs": [
            {
                "id": run1,
                "name": "DB Task 1",
                "status": "error",
                "error": err_text,
                "started_at": now_iso,
                "metadata": {"agent": "WorkerAgent", "version": "1.0"},
            },
            {
                "id": run2,
                "name": "DB Task 2",
                "status": "error",
                "error": err_text,
                "started_at": now_iso,
                "metadata": {"agent": "WorkerAgent", "version": "1.0"},
            },
        ]
    }
    res_ing = await client.post("/v1/ingest/spans", json=ingest_payload, headers=headers)
    assert res_ing.status_code == 200

    # 2. Sync with auto_embed=True (using fake embedding provider)
    await client.post("/v1/failures/sync", json={"auto_embed": True}, headers=headers)

    # 3. Run clustering job
    cluster_run_res = await client.post(
        "/v1/failures/clusters/run",
        json={"similarity_threshold": 0.85, "min_cluster_size": 2},
        headers=headers,
    )
    assert cluster_run_res.status_code == 200
    run_res_data = cluster_run_res.json()
    assert run_res_data["clusters_created"] >= 1
    assert run_res_data["events_assigned"] >= 2

    # 4. List clusters
    clusters_res = await client.get("/v1/failures/clusters", headers=headers)
    assert clusters_res.status_code == 200
    clusters_data = clusters_res.json()
    assert clusters_data["total"] >= 1
    cluster = clusters_data["items"][0]
    cluster_id = cluster["id"]
    assert cluster["status"] == "new"
    assert cluster["event_count"] >= 2

    # 5. Update cluster status to 'investigating'
    update_res = await client.patch(
        f"/v1/failures/clusters/{cluster_id}/status",
        json={"status": "investigating", "resolution_notes": "Assigned to database team for indexing"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "investigating"

    # 6. Get cluster detail with evidence & audit history
    detail_res = await client.get(f"/v1/failures/clusters/{cluster_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["status"] == "investigating"
    assert len(detail["recent_events"]) >= 2
    assert len(detail["status_history"]) >= 2  # created + updated

    # Check audit history entries
    statuses = [h["new_status"] for h in detail["status_history"]]
    assert "investigating" in statuses
    assert "new" in statuses


# ------------------- 8. API Integration Tests: Similarity Search -------------------


@pytest.mark.asyncio
async def test_similarity_search_endpoint(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify similarity search endpoint returns matches with vector and fallback indicators."""
    headers = {"X-API-Key": TEST_API_KEY}

    # 1. Ingest a failure
    run_id = str(uuid.uuid4())
    res_ing1 = await client.post(
        "/v1/ingest/spans",
        json={
            "runs": [
                {
                    "id": run_id,
                    "name": "Search Target Agent",
                    "status": "error",
                    "error": "MemoryLimitExceeded: Docker container exceeded 2048MB memory limit",
                    "started_at": datetime.now(UTC).isoformat(),
                }
            ]
        },
        headers=headers,
    )
    assert res_ing1.status_code == 200
    await client.post("/v1/failures/sync", json={"auto_embed": False}, headers=headers)

    # 2. Search using lexical fallback (since embedding provider is not configured)
    search_res = await client.post(
        "/v1/failures/search",
        json={"query_text": "container exceeded memory limit", "threshold": 0.2},
        headers=headers,
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["search_method"] in ("vector_similarity", "lexical_fallback")
    assert search_data["total"] >= 1
    assert "MemoryLimitExceeded" in search_data["results"][0]["error_summary"]


# ------------------- 9. Tenant Isolation Tests -------------------


@pytest.mark.asyncio
async def test_tenant_isolation_on_failure_endpoints(client: AsyncClient) -> None:
    """Verify primary and secondary projects are isolated: no cross-project data leakage."""
    primary_headers = {"X-API-Key": TEST_API_KEY}
    other_headers = {"X-API-Key": OTHER_PROJECT_API_KEY}

    # 1. Primary project ingests and syncs a failure
    p_run = str(uuid.uuid4())
    res_ing2 = await client.post(
        "/v1/ingest/spans",
        json={
            "runs": [
                {
                    "id": p_run,
                    "name": "Primary Confidential Agent",
                    "status": "error",
                    "error": "ConfidentialPrimaryError: Secret code leak in run",
                    "started_at": datetime.now(UTC).isoformat(),
                }
            ]
        },
        headers=primary_headers,
    )
    assert res_ing2.status_code == 200
    await client.post("/v1/failures/sync", json={"auto_embed": False}, headers=primary_headers)

    # Fetch event id
    p_list = (await client.get("/v1/failures", headers=primary_headers)).json()
    assert p_list["total"] >= 1
    event_id = p_list["items"][0]["id"]

    # 2. Secondary project lists failures: should NOT see primary's failure event
    other_list = (await client.get("/v1/failures", headers=other_headers)).json()
    other_ids = [item["id"] for item in other_list["items"]]
    assert event_id not in other_ids

    # 3. Secondary project direct GET by ID: must return 404
    direct_get = await client.get(f"/v1/failures/{event_id}", headers=other_headers)
    assert direct_get.status_code == 404

    # 4. Secondary project overview: must not count primary's events
    other_overview = (await client.get("/v1/failures/overview", headers=other_headers)).json()
    assert other_overview["total_failure_events"] == 0
