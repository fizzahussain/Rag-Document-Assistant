import hashlib
import math
from abc import ABC, abstractmethod

import httpx

from backend.app.config import settings
from backend.app.core.exceptions import RAGException


class BaseEmbeddingProvider(ABC):
    """Abstract interface for embedding generation services"""

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for text chunks"""

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Generate an embedding vector for a query"""


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Generate deterministic vectors for offline tests"""

    def __init__(
        self,
        dimension: int = settings.EMBEDDING_DIMENSION,
    ) -> None:
        self.dimension = dimension

    def _generate_vector(self, text: str) -> list[float]:
        seed_hash = hashlib.sha256(text.encode("utf-8")).digest()
        raw_vector: list[float] = []

        for index in range(self.dimension):
            byte_value = seed_hash[(index * 7) % len(seed_hash)]
            value = (byte_value / 255.0) * 2.0 - 1.0
            raw_vector.append(value)

        norm = math.sqrt(sum(value * value for value in raw_vector))

        if norm == 0:
            return [0.0] * self.dimension

        return [value / norm for value in raw_vector]

    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return [self._generate_vector(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._generate_vector(text)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Generate embeddings using the OpenAI API"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = settings.EMBEDDING_MODEL,
    ) -> None:
        if api_key is None and settings.OPENAI_API_KEY:
            api_key = settings.OPENAI_API_KEY.get_secret_value()

        if not api_key:
            raise RAGException("OPENAI_API_KEY is required for OpenAIEmbeddingProvider")

        self.api_key = api_key
        self.model = model
        self.endpoint = "https://api.openai.com/v1/embeddings"

    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "input": texts,
            "model": self.model,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise RAGException(f"Could not connect to OpenAI embeddings API: {exc}") from exc

        if response.status_code != 200:
            raise RAGException(
                f"OpenAI Embedding API error ({response.status_code}): {response.text}"
            )

        data = response.json()

        try:
            return [item["embedding"] for item in data["data"]]
        except (KeyError, TypeError) as exc:
            raise RAGException("OpenAI returned an invalid embedding response") from exc

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_texts([text])

        if not results:
            raise RAGException("OpenAI returned no query embedding")

        return results[0]


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Generate embeddings using a local Ollama server"""

    def __init__(
        self,
        model: str = settings.EMBEDDING_MODEL,
        base_url: str = settings.OLLAMA_BASE_URL,
        timeout_seconds: float = settings.OLLAMA_TIMEOUT_SECONDS,
    ) -> None:
        self.model = model
        self.endpoint = f"{base_url.rstrip('/')}/api/embed"
        self.timeout = httpx.Timeout(
            timeout_seconds,
            connect=10.0,
        )

    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        payload = {
            "model": self.model,
            "input": texts,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.endpoint,
                    json=payload,
                )
        except httpx.ConnectError as exc:
            raise RAGException(
                "Could not connect to Ollama at "
                f"{settings.OLLAMA_BASE_URL}. "
                "Make sure Ollama is running."
            ) from exc
        except httpx.TimeoutException as exc:
            raise RAGException("Ollama embedding request timed out") from exc
        except httpx.HTTPError as exc:
            raise RAGException(f"Ollama embedding request failed: {exc}") from exc

        if response.status_code != 200:
            raise RAGException(
                f"Ollama Embedding API error ({response.status_code}): {response.text}"
            )

        data = response.json()
        embeddings = data.get("embeddings")

        if not isinstance(embeddings, list):
            raise RAGException("Ollama returned an invalid embedding response")

        if len(embeddings) != len(texts):
            raise RAGException("Ollama returned the wrong number of embeddings")

        for embedding in embeddings:
            if not isinstance(embedding, list):
                raise RAGException("Ollama returned an invalid embedding vector")

            if len(embedding) != settings.EMBEDDING_DIMENSION:
                raise RAGException(
                    "Ollama embedding dimension mismatch: "
                    f"expected {settings.EMBEDDING_DIMENSION}, "
                    f"received {len(embedding)}"
                )

        return embeddings

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_texts([text])

        if not results:
            raise RAGException("Ollama returned no query embedding")

        return results[0]


class EmbeddingProviderFactory:
    """Return the configured embedding provider"""

    @staticmethod
    def get_provider() -> BaseEmbeddingProvider:
        provider_type = settings.EMBEDDING_PROVIDER.lower()

        if provider_type == "openai":
            return OpenAIEmbeddingProvider()

        if provider_type == "ollama":
            return OllamaEmbeddingProvider()

        if provider_type == "mock":
            return MockEmbeddingProvider()

        raise RAGException(f"Unsupported embedding provider: {provider_type}")
