"""Embedding generation providers with deterministic offline fallback (Phase 20)."""

import hashlib
import math
import re
from abc import ABC, abstractmethod

import httpx

from prism.logging.logger import get_logger

logger = get_logger(__name__)


def _normalize_vector(vec: list[float]) -> list[float]:
    """Normalize a vector to unit L2 length."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


class BaseEmbeddingProvider(ABC):
    """Abstract interface for embedding generation."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimensionality."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Compute an embedding vector for a single text."""

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Compute embedding vectors for a batch of texts."""


class DeterministicEmbeddingProvider(BaseEmbeddingProvider):
    """Zero-dependency, pure-Python deterministic embedding provider.

    Produces high-speed normalized 128-dimensional semantic representations
    using token hashing and n-gram term frequency projections.
    Guarantees 100% offline testing and cross-platform reproducibility.
    """

    def __init__(self, dimension: int = 128) -> None:
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_text(self, text: str) -> list[float]:
        """Compute normalized vector synchronously within async signature."""
        return self._compute_embedding(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Compute batch vectors."""
        return [self._compute_embedding(t) for t in texts]

    def _compute_embedding(self, text: str) -> list[float]:
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return [0.0] * self._dim

        vec = [0.0] * self._dim

        for token in tokens:
            # MD5 hash mapped into dimensional buckets with sign hashing
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dim
            sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
            vec[idx] += sign

        # Sub-word character n-grams for code symbols and compound words
        for token in tokens:
            if len(token) >= 4:
                for j in range(len(token) - 2):
                    ngram = token[j : j + 3]
                    h_ng = int(hashlib.md5(ngram.encode("utf-8")).hexdigest(), 16)
                    idx_ng = h_ng % self._dim
                    vec[idx_ng] += 0.5

        return _normalize_vector(vec)


class RemoteEmbeddingProvider(BaseEmbeddingProvider):
    """Remote embedding provider with seamless deterministic fallback."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "text-embedding-3-small",
        dimension: int = 1536,
        timeout_seconds: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dim = dimension
        self._timeout = timeout_seconds
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)
        self._fallback = DeterministicEmbeddingProvider(dimension=dimension)

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_text(self, text: str) -> list[float]:
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self._api_key:
            return await self._fallback.embed_batch(texts)

        endpoint = f"{self._base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": texts,
        }

        try:
            res = await self._client.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self._timeout,
            )
            if res.status_code == 200:
                data = res.json().get("data", [])
                return [item["embedding"] for item in data]
            logger.warning(
                "Remote embedding call returned HTTP %d, using fallback",
                res.status_code,
            )
        except (httpx.RequestError, KeyError, ValueError, RuntimeError, OSError) as e:
            logger.warning(
                "Remote embedding call failed (%s), falling back to deterministic: %s",
                type(e).__name__,
                e,
            )

        return await self._fallback.embed_batch(texts)
