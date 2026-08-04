import hashlib
import math
from abc import ABC, abstractmethod

import httpx

from backend.app.config import settings
from backend.app.core.exceptions import RAGException


class BaseEmbeddingProvider(ABC):
    """Abstract interface for embedding generation services."""

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generates embedding vectors for a batch of text chunks."""

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Generates an embedding vector for a single query text."""


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Generates deterministic pseudo-random unit-normalized vectors.

    Useful for offline testing and development without external API keys.
    """

    def __init__(self, dimension: int = settings.EMBEDDING_DIMENSION):
        self.dimension = dimension

    def _generate_vector(self, text: str) -> list[float]:
        # Hash text to generate a deterministic seed
        seed_hash = hashlib.sha256(text.encode("utf-8")).digest()
        raw_vector: list[float] = []

        for i in range(self.dimension):
            byte_val = seed_hash[(i * 7) % len(seed_hash)]
            val = (byte_val / 255.0) * 2.0 - 1.0  # Scale between -1 and 1
            raw_vector.append(val)

        # Normalize vector to unit length (L2 norm = 1.0)
        norm = math.sqrt(sum(x * x for x in raw_vector))
        if norm == 0:
            return [0.0] * self.dimension
        return [x / norm for x in raw_vector]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._generate_vector(text)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Generates embeddings using OpenAI API via HTTPX async client."""

    def __init__(
        self,
        api_key: str | None = (
            settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else None
        ),
        model: str = settings.EMBEDDING_MODEL,
    ):
        if not api_key:
            raise RAGException("OPENAI_API_KEY is required for OpenAIEmbeddingProvider")
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://api.openai.com/v1/embeddings"

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"input": texts, "model": self.model}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.endpoint, headers=headers, json=payload)
            if response.status_code != 200:
                raise RAGException(
                    f"OpenAI Embedding API error ({response.status_code}): {response.text}"
                )
            data = response.json()
            return [item["embedding"] for item in data["data"]]

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_texts([text])
        return results[0]


class EmbeddingProviderFactory:
    """Factory to retrieve configured embedding provider."""

    @staticmethod
    def get_provider() -> BaseEmbeddingProvider:
        provider_type = settings.EMBEDDING_PROVIDER.lower()
        if provider_type == "openai":
            return OpenAIEmbeddingProvider()
        else:
            return MockEmbeddingProvider()
