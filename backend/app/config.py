import json
from functools import lru_cache

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_ENV: str = "development"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    ALLOWED_ORIGINS: str | list[str] = [
        "http://localhost:7860",
        "http://127.0.0.1:7860",
    ]

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres_password@localhost:5432/rag_db"
    DB_ECHO: bool = False

    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_BLOCK_SIZE_BYTES: int = 1024 * 1024
    ALLOWED_EXTENSIONS: str | list[str] = [
        "pdf",
        "docx",
        "txt",
        "md",
        "csv",
        "html",
        "json",
    ]

    EMBEDDING_PROVIDER: str = "mock"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120
    CHUNK_CONTEXT_SUMMARY_ENABLED: bool = True
    CHUNK_CONTEXT_SUMMARY_MAX_CHARS: int = 700
    CHUNK_CONTEXT_LLM_STRIDE: int = 12

    CHAT_HISTORY_MESSAGES: int = 8

    OCR_ENABLED: bool = True
    OCR_LANGUAGE: str = "eng"
    OCR_DPI: int = 200
    OCR_MIN_TEXT_CHARS: int = 30

    LLM_PROVIDER: str = "mock"
    LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: SecretStr | None = None

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TIMEOUT_SECONDS: float = 120.0
    OLLAMA_KEEP_ALIVE: str = "-1"
    OLLAMA_WARMUP_ON_STARTUP: bool = True

    TRANSCRIPTION_PROVIDER: str = "faster-whisper"
    TRANSCRIPTION_MODEL: str = "small"
    TRANSCRIPTION_DEVICE: str = "cpu"
    TRANSCRIPTION_COMPUTE_TYPE: str = "int8"
    TRANSCRIPTION_LANGUAGE: str | None = None
    TRANSCRIPTION_BEAM_SIZE: int = 5
    TRANSCRIPTION_TIMEOUT_SECONDS: float = 180.0
    MAX_AUDIO_SIZE_MB: int = 25
    ALLOWED_AUDIO_EXTENSIONS: str | list[str] = [
        "wav",
        "mp3",
        "m4a",
        "ogg",
        "webm",
        "flac",
    ]

    AUTH_SECRET_KEY: SecretStr = SecretStr("change-me-in-production")
    ACCESS_TOKEN_TTL_SECONDS: int = 86400
    DEV_USER_ID: str = "00000000-0000-0000-0000-000000000001"

    LOG_LEVEL: str = "INFO"

    @field_validator(
        "ALLOWED_ORIGINS",
        "ALLOWED_EXTENSIONS",
        "ALLOWED_AUDIO_EXTENSIONS",
        mode="before",
    )
    @classmethod
    def parse_string_list(cls, value: str | list[str]) -> list[str]:
        """Parse JSON arrays or comma-separated environment values"""

        if isinstance(value, str):
            try:
                parsed = json.loads(value)

                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                return [item.strip() for item in value.split(",") if item.strip()]

        return [str(item).strip() for item in value if str(item).strip()]

    @field_validator(
        "EMBEDDING_PROVIDER",
        "LLM_PROVIDER",
    )
    @classmethod
    def validate_ai_provider(cls, value: str) -> str:
        """Validate embedding and language-model providers"""

        provider = value.strip().lower()
        supported_providers = {
            "mock",
            "openai",
            "ollama",
        }

        if provider not in supported_providers:
            supported = ", ".join(sorted(supported_providers))
            raise ValueError(f"Unsupported provider '{provider}'. Expected one of: {supported}")

        return provider

    @field_validator("TRANSCRIPTION_PROVIDER")
    @classmethod
    def validate_transcription_provider(cls, value: str) -> str:
        """Validate the configured speech-to-text provider"""

        provider = value.strip().lower()
        supported_providers = {
            "faster-whisper",
            "disabled",
        }

        if provider not in supported_providers:
            supported = ", ".join(sorted(supported_providers))
            raise ValueError(
                f"Unsupported transcription provider '{provider}'. Expected one of: {supported}"
            )

        return provider

    @field_validator("OLLAMA_BASE_URL")
    @classmethod
    def clean_ollama_base_url(cls, value: str) -> str:
        """Normalize the Ollama service URL"""

        return value.strip().rstrip("/")

    @field_validator(
        "ALLOWED_EXTENSIONS",
        "ALLOWED_AUDIO_EXTENSIONS",
    )
    @classmethod
    def normalize_extensions(cls, value: list[str]) -> list[str]:
        """Normalize configured file extensions"""

        normalized: list[str] = []

        for extension in value:
            clean_extension = extension.strip().lower().lstrip(".")

            if clean_extension and clean_extension not in normalized:
                normalized.append(clean_extension)

        return normalized

    @field_validator("TRANSCRIPTION_DEVICE")
    @classmethod
    def validate_transcription_device(cls, value: str) -> str:
        """Validate the faster-whisper execution device"""

        device = value.strip().lower()

        if device not in {
            "cpu",
            "cuda",
            "auto",
        }:
            raise ValueError("TRANSCRIPTION_DEVICE must be one of: auto, cpu, cuda")

        return device

    @field_validator("TRANSCRIPTION_COMPUTE_TYPE")
    @classmethod
    def clean_compute_type(cls, value: str) -> str:
        """Normalize the faster-whisper compute type"""

        compute_type = value.strip().lower()

        if not compute_type:
            raise ValueError("TRANSCRIPTION_COMPUTE_TYPE must not be empty")

        return compute_type

    @field_validator("TRANSCRIPTION_LANGUAGE")
    @classmethod
    def clean_transcription_language(
        cls,
        value: str | None,
    ) -> str | None:
        """Normalize an optional transcription language code"""

        if value is None:
            return None

        language = value.strip().lower()

        return language or None

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        """Validate cross-field configuration rules"""

        if self.APP_ENV.lower() == "production":
            if self.AUTH_SECRET_KEY.get_secret_value() == "change-me-in-production":
                raise ValueError("AUTH_SECRET_KEY must be configured in production")

            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError("SQLite is not supported in production")

        if self.MAX_UPLOAD_SIZE_MB <= 0:
            raise ValueError("MAX_UPLOAD_SIZE_MB must be greater than zero")

        if self.MAX_AUDIO_SIZE_MB <= 0:
            raise ValueError("MAX_AUDIO_SIZE_MB must be greater than zero")

        if self.CHUNK_SIZE <= 0:
            raise ValueError("CHUNK_SIZE must be greater than zero")

        if self.CHUNK_OVERLAP < 0 or self.CHUNK_OVERLAP >= self.CHUNK_SIZE:
            raise ValueError("CHUNK_OVERLAP must be between 0 and CHUNK_SIZE - 1")

        if self.CHUNK_CONTEXT_SUMMARY_MAX_CHARS <= 0:
            raise ValueError("CHUNK_CONTEXT_SUMMARY_MAX_CHARS must be greater than zero")

        if self.CHUNK_CONTEXT_LLM_STRIDE <= 0:
            raise ValueError("CHUNK_CONTEXT_LLM_STRIDE must be greater than zero")

        if self.CHAT_HISTORY_MESSAGES < 0:
            raise ValueError("CHAT_HISTORY_MESSAGES must not be negative")

        if self.OCR_DPI <= 0:
            raise ValueError("OCR_DPI must be greater than zero")

        if self.OCR_MIN_TEXT_CHARS < 0:
            raise ValueError("OCR_MIN_TEXT_CHARS must not be negative")

        if self.TRANSCRIPTION_BEAM_SIZE <= 0:
            raise ValueError("TRANSCRIPTION_BEAM_SIZE must be greater than zero")

        if self.TRANSCRIPTION_TIMEOUT_SECONDS <= 0:
            raise ValueError("TRANSCRIPTION_TIMEOUT_SECONDS must be greater than zero")

        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings"""

    return Settings()


settings = get_settings()
