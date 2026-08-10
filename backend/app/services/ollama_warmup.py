import httpx

from backend.app.config import ollama_keep_alive, settings
from backend.app.core.logging import logger
from backend.app.services.embedder import EmbeddingProviderFactory
from backend.app.services.http_client import get_http_client


async def warm_ollama_models() -> None:
    """Pre-load Ollama embedding and chat models to avoid first-request cold starts"""

    if not settings.OLLAMA_WARMUP_ON_STARTUP:
        return

    uses_ollama = (
        settings.EMBEDDING_PROVIDER.lower() == "ollama"
        or settings.LLM_PROVIDER.lower() == "ollama"
    )
    if not uses_ollama:
        return

    timeout = httpx.Timeout(settings.OLLAMA_TIMEOUT_SECONDS, connect=10.0)
    base_url = settings.OLLAMA_BASE_URL.rstrip("/")

    if settings.EMBEDDING_PROVIDER.lower() == "ollama":
        try:
            embedder = EmbeddingProviderFactory.get_provider()
            await embedder.embed_query("warmup")
            logger.info("Ollama embedding model warmed", model=settings.EMBEDDING_MODEL)
        except Exception as exc:
            logger.warning(
                "Ollama embedding warmup failed",
                model=settings.EMBEDDING_MODEL,
                error_type=exc.__class__.__name__,
            )

    if settings.LLM_PROVIDER.lower() == "ollama":
        payload = {
            "model": settings.LLM_MODEL,
            "messages": [{"role": "user", "content": "warmup"}],
            "stream": False,
            "think": False,
            "keep_alive": ollama_keep_alive(),
            "options": {"num_predict": 1},
        }
        try:
            client = get_http_client()
            response = await client.post(
                f"{base_url}/api/chat",
                json=payload,
                timeout=timeout,
            )
            if response.status_code == 200:
                logger.info("Ollama chat model warmed", model=settings.LLM_MODEL)
            else:
                logger.warning(
                    "Ollama chat warmup returned non-200 status",
                    model=settings.LLM_MODEL,
                    status_code=response.status_code,
                )
        except Exception as exc:
            logger.warning(
                "Ollama chat warmup failed",
                model=settings.LLM_MODEL,
                error_type=exc.__class__.__name__,
            )
