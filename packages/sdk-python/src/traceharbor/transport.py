"""
TraceHarbor SDK — Background HTTP Transport & Batching
"""

import logging
import queue
import threading
import time

import httpx

from traceharbor.models import RunData, SpanData

logger = logging.getLogger("traceharbor.transport")


class HttpTransport:
    """
    Asynchronous, non-blocking HTTP transport for trace telemetry.
    Buffers events in an in-memory queue and flushes them in batches
    via a background daemon thread with retries and exponential backoff.
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        batch_size: int = 50,
        flush_interval: float = 2.0,
        max_queue_size: int = 5000,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_queue_size = max_queue_size
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        self._queue: queue.Queue[RunData | SpanData] = queue.Queue(maxsize=max_queue_size)
        self._running = True
        self._flush_event = threading.Event()
        self._client = httpx.Client(timeout=10.0)

        # Worker thread
        self._worker = threading.Thread(target=self._worker_loop, name="TraceHarborWorker", daemon=True)
        self._worker.start()

    def enqueue(self, item: RunData | SpanData) -> bool:
        """
        Add an item to the outbound buffer.
        Non-blocking: if the queue is full, logs a warning and drops the event
        to safeguard agent application performance and memory.
        """
        if not self._running:
            return False
        try:
            self._queue.put_nowait(item)
            return True
        except queue.Full:
            logger.warning(
                "TraceHarbor telemetry buffer full (%d items). Dropping event to preserve application memory.",
                self.max_queue_size,
            )
            return False

    def _worker_loop(self) -> None:
        """Background loop draining queue and flushing batches periodically."""
        last_flush_time = time.time()

        while self._running or not self._queue.empty():
            try:
                # Wait for items or flush signal
                timeout = max(0.1, self.flush_interval - (time.time() - last_flush_time))
                self._flush_event.wait(timeout=timeout)
                self._flush_event.clear()

                batch = self._drain_batch()
                if batch:
                    self._send_batch(batch)
                    last_flush_time = time.time()
            except Exception as e:
                logger.debug("Unexpected error in TraceHarbor transport worker: %s", e)

    def _drain_batch(self) -> list[RunData | SpanData]:
        """Drain up to batch_size items from the in-memory queue."""
        batch: list[RunData | SpanData] = []
        while len(batch) < self.batch_size:
            try:
                item = self._queue.get_nowait()
                batch.append(item)
            except queue.Empty:
                break
        return batch

    def _send_batch(self, batch: list[RunData | SpanData]) -> None:
        """Serialize and send batch to ingestion endpoint with exponential backoff."""
        if not batch:
            return

        runs = [item.to_dict() for item in batch if isinstance(item, RunData)]
        spans = [item.to_dict() for item in batch if isinstance(item, SpanData)]
        payload = {"runs": runs, "spans": spans}

        url = f"{self.endpoint}/v1/ingest/spans"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "TraceHarbor-Python-SDK/0.1.0",
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    for _ in batch:
                        self._queue.task_done()
                    return
                elif resp.status_code in (401, 403):
                    logger.error(
                        "TraceHarbor authentication failed (HTTP %d). Ingestion rejected: %s",
                        resp.status_code,
                        resp.text,
                    )
                    break
                else:
                    logger.warning(
                        "TraceHarbor ingestion HTTP %d (attempt %d/%d): %s",
                        resp.status_code,
                        attempt,
                        self.max_retries,
                        resp.text,
                    )
            except httpx.TransportError as exc:
                logger.warning(
                    "TraceHarbor network error on ingest (attempt %d/%d): %s",
                    attempt,
                    self.max_retries,
                    exc,
                )

            if attempt < self.max_retries:
                sleep_sec = self.backoff_factor * (2 ** (attempt - 1))
                time.sleep(sleep_sec)

        # Mark tasks done even if failed after retries to prevent queue deadlock
        for _ in batch:
            try:
                self._queue.task_done()
            except ValueError:
                pass

    def flush(self, timeout: float = 5.0) -> None:
        """Force flush all queued events and block until completed or timed out."""
        self._flush_event.set()
        deadline = time.time() + timeout
        while not self._queue.empty() and time.time() < deadline:
            time.sleep(0.05)

    def shutdown(self, timeout: float = 5.0) -> None:
        """Flush remaining events and gracefully terminate worker thread."""
        self._running = False
        self.flush(timeout=timeout)
        if self._worker.is_alive():
            self._worker.join(timeout=1.0)
        self._client.close()
