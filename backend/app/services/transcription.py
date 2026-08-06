import asyncio
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel
from pydantic import BaseModel

from backend.app.config import settings
from backend.app.core.exceptions import RAGException


class TranscriptionResult(BaseModel):
    """Contain a completed audio transcription"""

    text: str
    language: str | None
    language_probability: float | None
    duration_seconds: float | None
    execution_time_seconds: float


class BaseTranscriptionProvider(ABC):
    """Define audio transcription behavior"""

    @abstractmethod
    async def transcribe(
        self,
        audio_path: Path,
    ) -> TranscriptionResult:
        """Transcribe an audio file into text"""


class FasterWhisperTranscriptionProvider(BaseTranscriptionProvider):
    """Transcribe audio locally with faster-whisper"""

    def __init__(
        self,
        model_name: str = settings.TRANSCRIPTION_MODEL,
        device: str = settings.TRANSCRIPTION_DEVICE,
        compute_type: str = settings.TRANSCRIPTION_COMPUTE_TYPE,
        language: str | None = settings.TRANSCRIPTION_LANGUAGE,
        beam_size: int = settings.TRANSCRIPTION_BEAM_SIZE,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.beam_size = beam_size
        self._model: WhisperModel | None = None
        self._model_lock = asyncio.Lock()

    async def _get_model(self) -> WhisperModel:
        """Load and cache the Whisper model"""

        if self._model is not None:
            return self._model

        async with self._model_lock:
            if self._model is None:
                try:
                    self._model = await asyncio.to_thread(
                        WhisperModel,
                        self.model_name,
                        device=self.device,
                        compute_type=self.compute_type,
                    )
                except Exception as exc:
                    raise RAGException("The speech-to-text model could not be loaded") from exc

        return self._model

    def _transcribe_sync(
        self,
        model: WhisperModel,
        audio_path: Path,
    ) -> tuple[str, Any]:
        """Run the blocking faster-whisper transcription"""

        segments, information = model.transcribe(
            str(audio_path),
            language=self.language,
            beam_size=self.beam_size,
            vad_filter=True,
            condition_on_previous_text=False,
        )

        text_parts: list[str] = []

        for segment in segments:
            text = str(segment.text).strip()

            if text:
                text_parts.append(text)

        return " ".join(text_parts).strip(), information

    async def transcribe(
        self,
        audio_path: Path,
    ) -> TranscriptionResult:
        """Transcribe audio without blocking the FastAPI event loop"""

        start_time = time.perf_counter()

        if not await asyncio.to_thread(audio_path.is_file):
            raise RAGException("The uploaded audio file could not be found")

        model = await self._get_model()

        try:
            text, information = await asyncio.wait_for(
                asyncio.to_thread(
                    self._transcribe_sync,
                    model,
                    audio_path,
                ),
                timeout=settings.TRANSCRIPTION_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise RAGException("Audio transcription timed out") from exc
        except RAGException:
            raise
        except Exception as exc:
            raise RAGException("The audio file could not be transcribed") from exc

        if not text:
            raise RAGException("No speech was detected in the uploaded audio")

        language = getattr(information, "language", None)
        language_probability = getattr(
            information,
            "language_probability",
            None,
        )
        duration = getattr(information, "duration", None)

        return TranscriptionResult(
            text=text,
            language=str(language) if language else None,
            language_probability=(
                round(float(language_probability), 4) if language_probability is not None else None
            ),
            duration_seconds=(round(float(duration), 3) if duration is not None else None),
            execution_time_seconds=round(
                time.perf_counter() - start_time,
                3,
            ),
        )


class DisabledTranscriptionProvider(BaseTranscriptionProvider):
    """Reject transcription when speech-to-text is disabled"""

    async def transcribe(
        self,
        audio_path: Path,
    ) -> TranscriptionResult:
        """Reject the transcription request"""

        del audio_path

        raise RAGException("Speech-to-text is disabled in the application settings")


class TranscriptionProviderFactory:
    """Return the configured transcription provider"""

    @staticmethod
    def get_provider() -> BaseTranscriptionProvider:
        """Create the configured transcription provider"""

        provider_type = settings.TRANSCRIPTION_PROVIDER.lower()

        if provider_type == "faster-whisper":
            return FasterWhisperTranscriptionProvider()

        if provider_type == "disabled":
            return DisabledTranscriptionProvider()

        raise RAGException(f"Unsupported transcription provider: {provider_type}")


@lru_cache
def get_transcription_provider() -> BaseTranscriptionProvider:
    """Return the cached transcription provider"""

    return TranscriptionProviderFactory.get_provider()
