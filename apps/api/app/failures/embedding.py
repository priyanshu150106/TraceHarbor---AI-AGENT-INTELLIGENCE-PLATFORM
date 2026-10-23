"""
TraceHarbor API — Pluggable Embedding Service

Provider-neutral interface for computing vector embeddings of normalized
failure summaries. Supports configurable providers via environment variables.

Design:
- Content-hash dedup: avoids re-embedding unchanged text
- Batch support with configurable batch sizes
- Bounded retries with exponential backoff
- Timeout protection
- Never makes external API calls during unit tests
- Falls back to "embedding unavailable" when no provider is configured

Supported providers (via EMBEDDING_PROVIDER env var):
- "openai" — OpenAI text-embedding-3-small (requires OPENAI_API_KEY)
- "fake"   — Deterministic fake embeddings for testing only
- ""       — No embedding provider; clustering unavailable

A lexical (TF-IDF) fallback is provided as a clearly-labelled alternative
when vector embeddings are not available.
"""

import hashlib
import logging
import math
import struct
from abc import ABC, abstractmethod

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract embedding provider interface."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the dimensionality of the embedding vectors."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the embedding provider."""
        ...

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Compute embeddings for a batch of texts.
        Returns a list of float vectors, one per input text.
        Raises EmbeddingError on failure.
        """
        ...


class EmbeddingError(Exception):
    """Raised when an embedding operation fails."""

    pass


class FakeEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic fake embedding provider for testing.
    Generates fixed-dimension vectors from a hash of the input text.
    These are NOT genuine semantic embeddings — they are purely for
    testing vector storage and search mechanics.
    """

    def __init__(self, dimensions: int = 64):
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def provider_name(self) -> str:
        return "fake"

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            vec = self._deterministic_vector(text)
            results.append(vec)
        return results

    def _deterministic_vector(self, text: str) -> list[float]:
        """
        Generate a deterministic unit vector from the SHA-256 hash of the text.
        This is NOT a semantic embedding — similar texts will NOT produce
        similar vectors unless they are identical.
        """
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Expand hash to fill dimensions
        expanded = b""
        i = 0
        while len(expanded) < self._dimensions * 4:
            expanded += hashlib.sha256(h + struct.pack(">I", i)).digest()
            i += 1

        # Convert to floats
        vec = []
        for j in range(self._dimensions):
            # Unpack 4 bytes as unsigned int, normalize to [-1, 1]
            val = struct.unpack(">I", expanded[j * 4 : (j + 1) * 4])[0]
            vec.append((val / (2**32 - 1)) * 2 - 1)

        # Normalize to unit vector
        magnitude = math.sqrt(sum(x * x for x in vec))
        if magnitude > 0:
            vec = [x / magnitude for x in vec]

        return vec


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider using the text-embedding-3-small model.
    Requires OPENAI_API_KEY to be set.

    Features:
    - Batch processing (up to 2048 texts per request)
    - Configurable timeout and retries
    - Rate limit handling with exponential backoff
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = 256,
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
        batch_size: int = 100,
    ):
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._max_retries = max_retries
        self._timeout = timeout_seconds
        self._batch_size = batch_size

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def provider_name(self) -> str:
        return "openai"

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using OpenAI API with batching and retry."""
        import asyncio

        try:
            import httpx
        except ImportError:
            raise EmbeddingError(
                "httpx is required for OpenAI embeddings. Install with: pip install httpx"
            ) from None

        all_embeddings: list[list[float]] = []

        for batch_start in range(0, len(texts), self._batch_size):
            batch = texts[batch_start : batch_start + self._batch_size]
            embeddings = await self._embed_batch(batch, httpx, asyncio)
            all_embeddings.extend(embeddings)

        return all_embeddings

    async def _embed_batch(
        self, texts: list[str], httpx_module: object, asyncio_module: object
    ) -> list[list[float]]:
        """Embed a single batch with retries."""
        last_error = None

        for attempt in range(self._max_retries):
            try:
                async with httpx_module.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/embeddings",
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self._model,
                            "input": texts,
                            "dimensions": self._dimensions,
                        },
                    )

                    if response.status_code == 429:
                        # Rate limited — exponential backoff
                        wait = min(2**attempt * 1.0, 30.0)
                        logger.warning(
                            "OpenAI rate limit hit, retrying in %.1fs", wait
                        )
                        await asyncio_module.sleep(wait)
                        continue

                    if response.status_code != 200:
                        raise EmbeddingError(
                            f"OpenAI API returned {response.status_code}: "
                            f"{response.text[:500]}"
                        )

                    data = response.json()
                    embeddings = [item["embedding"] for item in data["data"]]

                    # Validate dimensions and finite values
                    for emb in embeddings:
                        if len(emb) != self._dimensions:
                            raise EmbeddingError(
                                f"Expected {self._dimensions} dimensions, "
                                f"got {len(emb)}"
                            )
                        if not all(math.isfinite(v) for v in emb):
                            raise EmbeddingError(
                                "Embedding contains non-finite values"
                            )

                    return embeddings

            except EmbeddingError:
                raise
            except Exception as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    wait = min(2**attempt * 0.5, 10.0)
                    logger.warning(
                        "Embedding attempt %d failed: %s, retrying in %.1fs",
                        attempt + 1,
                        str(e),
                        wait,
                    )
                    await asyncio_module.sleep(wait)

        raise EmbeddingError(
            f"Embedding failed after {self._max_retries} attempts: {last_error}"
        )


def get_embedding_provider() -> EmbeddingProvider | None:
    """
    Create the configured embedding provider based on environment settings.
    Returns None if no provider is configured (clustering unavailable).
    """
    provider_name = getattr(settings, "embedding_provider", "").strip().lower()

    if not provider_name:
        logger.info(
            "No embedding provider configured (EMBEDDING_PROVIDER not set). "
            "Semantic clustering is unavailable."
        )
        return None

    if provider_name == "fake":
        dims = getattr(settings, "embedding_dimensions", 64)
        return FakeEmbeddingProvider(dimensions=dims)

    if provider_name == "openai":
        api_key = getattr(settings, "openai_api_key", None)
        if not api_key:
            logger.warning(
                "OpenAI embedding provider configured but OPENAI_API_KEY not set. "
                "Semantic clustering is unavailable."
            )
            return None

        dims = getattr(settings, "embedding_dimensions", 256)
        return OpenAIEmbeddingProvider(
            api_key=api_key,
            dimensions=dims,
        )

    logger.warning("Unknown embedding provider '%s'. Clustering unavailable.", provider_name)
    return None


def validate_embedding(vector: list[float], expected_dims: int) -> bool:
    """Validate that an embedding vector has correct dimensions and finite values."""
    if len(vector) != expected_dims:
        return False
    return all(math.isfinite(v) for v in vector)
