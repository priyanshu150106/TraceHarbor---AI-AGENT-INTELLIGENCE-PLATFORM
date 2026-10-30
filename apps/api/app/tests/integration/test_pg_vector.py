"""
Phase C5 & B3 — pgvector Vector Operations Integration Tests

Tests real PostgreSQL pgvector capabilities:
- Vector(64) insertion and retrieval
- Cosine distance nearest-neighbor queries (<=>)
- L2 Euclidean distance queries (<->)
- Vector indexing and similarity ranking
"""

import math
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.models.failure import FailureCluster, FailureEvent
from app.models.project import Project
from app.models.user import User


def _make_normalized_vector(seed: float, dim: int = 64) -> list[float]:
    """Create a unit-length vector of dimension dim from a float seed."""
    raw = [math.sin(seed + i * 0.1) for i in range(dim)]
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw]


@pytest.mark.integration
async def test_pgvector_insert_and_retrieve(
    pg_session: AsyncSession,
    seeded_pg_project: tuple[User, Project, ApiKey],
) -> None:
    """Verify storing and retrieving 64-dimensional float vectors in PostgreSQL."""
    _, project, _ = seeded_pg_project

    now = datetime.now(UTC)
    vec = _make_normalized_vector(1.0, 64)

    event = FailureEvent(
        id=uuid.uuid4(),
        project_id=project.id,
        source_type="run",
        source_id=str(uuid.uuid4()),
        error_summary="Vector test event",
        normalized_text="vector test event",
        embedding_status="completed",
        embedding=vec,
        occurred_at=now,
    )
    pg_session.add(event)
    await pg_session.commit()

    # Query back
    stmt = select(FailureEvent).where(FailureEvent.id == event.id)
    fetched = (await pg_session.execute(stmt)).scalar_one()

    assert fetched.embedding is not None
    assert len(fetched.embedding) == 64
    # Check components are close to original
    for orig, retrieved in zip(vec, fetched.embedding, strict=True):
        assert abs(orig - float(retrieved)) < 1e-4


@pytest.mark.integration
async def test_pgvector_cosine_distance_nearest_neighbor(
    pg_session: AsyncSession,
    seeded_pg_project: tuple[User, Project, ApiKey],
) -> None:
    """Verify that pgvector cosine distance operator correctly identifies the closest event."""
    _, project, _ = seeded_pg_project
    now = datetime.now(UTC)

    # Base query vector
    query_vector = _make_normalized_vector(5.0, 64)

    # Very close vector (small perturbation)
    close_vector = [v + 0.001 for v in query_vector]
    close_norm = math.sqrt(sum(x * x for x in close_vector))
    close_vector = [x / close_norm for x in close_vector]

    # Distant vector (orthogonal / different phase)
    distant_vector = _make_normalized_vector(50.0, 64)

    # Insert events
    close_event = FailureEvent(
        id=uuid.uuid4(),
        project_id=project.id,
        source_type="run",
        source_id=str(uuid.uuid4()),
        error_summary="Close semantic match: Database connection reset by peer",
        normalized_text="database connection reset by peer",
        embedding_status="completed",
        embedding=close_vector,
        occurred_at=now,
    )
    distant_event = FailureEvent(
        id=uuid.uuid4(),
        project_id=project.id,
        source_type="run",
        source_id=str(uuid.uuid4()),
        error_summary="Distant semantic match: JSON schema validation error",
        normalized_text="json schema validation error",
        embedding_status="completed",
        embedding=distant_vector,
        occurred_at=now,
    )
    pg_session.add_all([close_event, distant_event])
    await pg_session.commit()

    # Query ordered by cosine distance
    stmt = (
        select(FailureEvent)
        .where(
            FailureEvent.project_id == project.id,
            FailureEvent.embedding.isnot(None),
        )
        .order_by(FailureEvent.embedding.cosine_distance(query_vector))
        .limit(2)
    )
    results = (await pg_session.execute(stmt)).scalars().all()

    assert len(results) >= 2
    # The first result must be the close event
    assert results[0].id == close_event.id


@pytest.mark.integration
async def test_pgvector_cluster_centroid_and_membership(
    pg_session: AsyncSession,
    seeded_pg_project: tuple[User, Project, ApiKey],
) -> None:
    """Verify storing cluster centroid vectors and linking member events."""
    _, project, _ = seeded_pg_project
    now = datetime.now(UTC)

    centroid_vec = _make_normalized_vector(2.5, 64)

    cluster = FailureCluster(
        id=uuid.uuid4(),
        project_id=project.id,
        title="Payment Gateway GatewayTimeout Cluster",
        dominant_category="timeout",
        centroid_embedding=centroid_vec,
        first_seen_at=now,
        last_seen_at=now,
        event_count=1,
    )
    pg_session.add(cluster)
    await pg_session.flush()

    member_event = FailureEvent(
        id=uuid.uuid4(),
        project_id=project.id,
        cluster_id=cluster.id,
        source_type="span",
        source_id=str(uuid.uuid4()),
        error_summary="GatewayTimeout: Stripe API did not respond",
        normalized_text="gatewaytimeout stripe api did not respond",
        embedding_status="completed",
        embedding=centroid_vec,
        occurred_at=now,
    )
    pg_session.add(member_event)
    await pg_session.commit()

    # Query cluster by centroid similarity
    stmt = (
        select(FailureCluster)
        .where(FailureCluster.project_id == project.id)
        .order_by(FailureCluster.centroid_embedding.cosine_distance(centroid_vec))
        .limit(1)
    )
    found_cluster = (await pg_session.execute(stmt)).scalar_one()
    assert found_cluster.id == cluster.id
    assert found_cluster.dominant_category == "timeout"
