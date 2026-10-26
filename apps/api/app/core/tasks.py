"""
TraceHarbor API — Reliable Background Task Manager

Provides lightweight, in-process async background task execution with:
- Task lifecycle tracking (queued, running, completed, failed, cancelled)
- Bounded retries with exponential backoff
- Progress tracking and result collection
- Memory bounds on completed task history
- Graceful shutdown during application lifecycle
"""

import asyncio
import logging
import uuid
from collections import OrderedDict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("traceharbor.tasks")

MAX_RETAINED_TASKS = 500


@dataclass
class TaskInfo:
    task_id: str
    task_type: str
    project_id: uuid.UUID | None
    status: str = "queued"  # queued, running, completed, failed, cancelled
    progress: float = 0.0
    result: dict[str, Any] | None = None
    error: str | None = None
    retries: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "project_id": str(self.project_id) if self.project_id else None,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class BackgroundTaskManager:
    """In-process async task manager with status tracking, retries, and graceful shutdown."""

    def __init__(self, max_history: int = MAX_RETAINED_TASKS) -> None:
        self._max_history = max_history
        self._tasks: OrderedDict[str, TaskInfo] = OrderedDict()
        self._running_asyncio_tasks: dict[str, asyncio.Task[Any]] = {}
        self._lock = asyncio.Lock()

    def _prune_history_locked(self) -> None:
        """Evict oldest terminal tasks if limit is reached."""
        while len(self._tasks) > self._max_history:
            # Pop the oldest task
            oldest_id, oldest_info = next(iter(self._tasks.items()))
            if oldest_info.status in ("completed", "failed", "cancelled"):
                self._tasks.pop(oldest_id)
            else:
                break

    def get_task(self, task_id: str) -> TaskInfo | None:
        """Fetch task status information by task ID."""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        project_id: uuid.UUID | None = None,
        status_filter: str | None = None,
        limit: int = 50,
    ) -> list[TaskInfo]:
        """List tasks with optional project and status filtering."""
        items: list[TaskInfo] = []
        for task in reversed(self._tasks.values()):
            if project_id is not None and task.project_id != project_id:
                continue
            if status_filter is not None and task.status != status_filter:
                continue
            items.append(task)
            if len(items) >= limit:
                break
        return items

    def submit(
        self,
        task_type: str,
        coro_fn: Callable[..., Coroutine[Any, Any, dict[str, Any] | None]],
        *args: Any,
        project_id: uuid.UUID | None = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> str:
        """
        Submit a coroutine for asynchronous execution in the background.
        Returns the generated task_id immediately.
        """
        task_id = str(uuid.uuid4())
        info = TaskInfo(
            task_id=task_id,
            task_type=task_type,
            project_id=project_id,
            max_retries=max_retries,
        )
        self._tasks[task_id] = info
        self._prune_history_locked()

        asyncio_task = asyncio.create_task(
            self._execute_with_retries(task_id, coro_fn, *args, **kwargs),
            name=f"bg_task_{task_type}_{task_id}",
        )
        self._running_asyncio_tasks[task_id] = asyncio_task
        return task_id

    async def _execute_with_retries(
        self,
        task_id: str,
        coro_fn: Callable[..., Coroutine[Any, Any, dict[str, Any] | None]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Execute the task with bounded exponential backoff retries."""
        info = self._tasks.get(task_id)
        if not info:
            return

        info.started_at = datetime.now(UTC)
        info.status = "running"
        info.progress = 0.1

        for attempt in range(info.max_retries + 1):
            try:
                # If canceled externally
                if info.status == "cancelled":
                    break

                logger.info(
                    "Executing task %s (%s) attempt %d/%d",
                    task_id,
                    info.task_type,
                    attempt + 1,
                    info.max_retries + 1,
                )
                result = await coro_fn(*args, **kwargs)
                info.status = "completed"
                info.progress = 1.0
                info.result = result if isinstance(result, dict) else {"result": result}
                info.completed_at = datetime.now(UTC)
                logger.info("Task %s completed successfully", task_id)
                break
            except asyncio.CancelledError:
                info.status = "cancelled"
                info.completed_at = datetime.now(UTC)
                logger.info("Task %s was cancelled", task_id)
                break
            except Exception as exc:
                info.retries = attempt + 1
                logger.warning(
                    "Task %s attempt %d failed: %s",
                    task_id,
                    info.retries,
                    str(exc),
                    exc_info=True,
                )
                if attempt < info.max_retries:
                    # Exponential backoff: 1s, 2s, 4s... capped at 10s
                    backoff = min(1.0 * (2**attempt), 10.0)
                    await asyncio.sleep(backoff)
                else:
                    info.status = "failed"
                    info.error = str(exc)
                    info.completed_at = datetime.now(UTC)
                    logger.error("Task %s failed after %d retries", task_id, info.max_retries)
            finally:
                if task_id in self._running_asyncio_tasks and info.status in (
                    "completed",
                    "failed",
                    "cancelled",
                ):
                    self._running_asyncio_tasks.pop(task_id, None)

    async def cancel(self, task_id: str) -> bool:
        """Cancel a running or queued background task."""
        info = self._tasks.get(task_id)
        if not info or info.status in ("completed", "failed", "cancelled"):
            return False

        info.status = "cancelled"
        info.completed_at = datetime.now(UTC)
        asyncio_task = self._running_asyncio_tasks.pop(task_id, None)
        if asyncio_task and not asyncio_task.done():
            asyncio_task.cancel()
        return True

    async def shutdown(self, timeout: float = 5.0) -> None:
        """Cancel all running tasks and wait for them to finish during graceful shutdown."""
        logger.info(
            "Shutting down BackgroundTaskManager (%d running tasks)",
            len(self._running_asyncio_tasks),
        )
        for task_id, task in list(self._running_asyncio_tasks.items()):
            info = self._tasks.get(task_id)
            if info:
                info.status = "cancelled"
                info.completed_at = datetime.now(UTC)
            if not task.done():
                task.cancel()

        if self._running_asyncio_tasks:
            tasks_to_wait = list(self._running_asyncio_tasks.values())
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_wait, return_exceptions=True),
                    timeout=timeout,
                )
            except TimeoutError:
                logger.warning("Background tasks shutdown timed out after %.1fs", timeout)

        self._running_asyncio_tasks.clear()


# Global singleton task manager
task_manager = BackgroundTaskManager()
