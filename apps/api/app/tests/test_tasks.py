"""
TraceHarbor API — Background Task System Unit & API Tests

Tests the BackgroundTaskManager, task lifecycle, exponential retries,
and async execution for clustering and sync operations.
"""

import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tasks import BackgroundTaskManager, task_manager
from app.tests.conftest import TEST_API_KEY


@pytest.mark.asyncio
async def test_task_manager_success_lifecycle() -> None:
    """Test successful task submission, execution, and state completion."""
    manager = BackgroundTaskManager(max_history=10)

    async def sample_job(x: int, y: int) -> dict[str, int]:
        await asyncio.sleep(0.01)
        return {"sum": x + y}

    task_id = manager.submit("add_numbers", sample_job, 10, 20)
    assert task_id is not None

    # Wait for completion
    for _ in range(50):
        task = manager.get_task(task_id)
        if task and task.status == "completed":
            break
        await asyncio.sleep(0.02)

    task = manager.get_task(task_id)
    assert task is not None
    assert task.status == "completed"
    assert task.progress == 1.0
    assert task.result == {"sum": 30}
    assert task.error is None
    assert task.retries == 0


@pytest.mark.asyncio
async def test_task_manager_retry_on_failure() -> None:
    """Test that task manager retries failed executions up to max_retries."""
    manager = BackgroundTaskManager(max_history=10)
    attempts = 0

    async def flaky_job() -> dict[str, str]:
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ValueError("Transient error")
        return {"status": "recovered"}

    # max_retries=2
    task_id = manager.submit("flaky_test", flaky_job, max_retries=2)

    for _ in range(100):
        task = manager.get_task(task_id)
        if task and task.status in ("completed", "failed"):
            break
        await asyncio.sleep(0.05)

    task = manager.get_task(task_id)
    assert task is not None
    assert task.status == "completed"
    assert task.retries == 1
    assert task.result == {"status": "recovered"}


@pytest.mark.asyncio
async def test_task_manager_cancellation() -> None:
    """Test cancelling an in-flight background task."""
    manager = BackgroundTaskManager(max_history=10)

    async def long_running_job() -> dict[str, str]:
        await asyncio.sleep(5.0)
        return {"done": "never"}

    task_id = manager.submit("long_job", long_running_job)
    await asyncio.sleep(0.05)

    cancelled = await manager.cancel(task_id)
    assert cancelled is True

    task = manager.get_task(task_id)
    assert task is not None
    assert task.status == "cancelled"


@pytest.mark.asyncio
async def test_api_trigger_clustering_in_background(client: AsyncClient) -> None:
    """Verify triggering clustering with run_in_background=True returns task_id and queued status."""
    headers = {"X-API-Key": TEST_API_KEY}
    res = await client.post(
        "/v1/failures/clusters/run",
        json={"run_in_background": True},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "queued"
    assert data["task_id"] is not None

    task_id = data["task_id"]

    # Poll status endpoint
    poll_res = await client.get(f"/v1/tasks/{task_id}", headers=headers)
    assert poll_res.status_code == 200
    task_data = poll_res.json()
    assert task_data["task_id"] == task_id
    assert task_data["task_type"] == "clustering"
    assert task_data["status"] in ("queued", "running", "completed")


@pytest.mark.asyncio
async def test_api_trigger_sync_in_background(client: AsyncClient) -> None:
    """Verify triggering failure sync with run_in_background=True returns task_id."""
    headers = {"X-API-Key": TEST_API_KEY}
    res = await client.post(
        "/v1/failures/sync",
        json={"auto_embed": False, "run_in_background": True},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "queued"
    assert data["task_id"] is not None

    task_id = data["task_id"]

    # Inspect task
    poll_res = await client.get(f"/v1/tasks/{task_id}", headers=headers)
    assert poll_res.status_code == 200
    assert poll_res.json()["task_type"] == "failure_sync"


@pytest.mark.asyncio
async def test_api_list_tasks_and_cancel(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Verify listing tasks and cancelling a task via API."""
    from sqlalchemy import select

    from app.models.api_key import ApiKey
    from app.tests.conftest import TEST_API_KEY_HASH

    res = await db_session.execute(
        select(ApiKey.project_id).where(ApiKey.key_hash == TEST_API_KEY_HASH)
    )
    project_id = res.scalar_one()

    headers = {"X-API-Key": TEST_API_KEY}

    async def slow_dummy() -> dict[str, str]:
        await asyncio.sleep(3.0)
        return {"status": "done"}

    tid = task_manager.submit("slow_dummy", slow_dummy, project_id=project_id)

    # List tasks
    list_res = await client.get("/v1/tasks", headers=headers)
    assert list_res.status_code == 200
    tasks_list = list_res.json()["tasks"]
    assert any(t["task_id"] == tid for t in tasks_list)

    # Cancel task
    cancel_res = await client.post(f"/v1/tasks/{tid}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["cancelled"] is True
