import json
from functools import lru_cache

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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

    LLM_PROVIDER: str = "mock"
    LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: SecretStr | None = None

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TIMEOUT_SECONDS: float = 120.0

    AUTH_SECRET_KEY: SecretStr = SecretStr("change-me-in-production")
    ACCESS_TOKEN_TTL_SECONDS: int = 86400
    DEV_USER_ID: str = "00000000-0000-0000-0000-000000000001"

    LOG_LEVEL: str = "INFO"

    @field_validator("ALLOWED_ORIGINS", "ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def parse_string_list(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)

                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                return [item.strip() for item in value.split(",") if item.strip()]

        return list(value)

    @field_validator("EMBEDDING_PROVIDER", "LLM_PROVIDER")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        provider = value.strip().lower()
        supported_providers = {"mock", "openai", "ollama"}

        if provider not in supported_providers:
            supported = ", ".join(sorted(supported_providers))
            raise ValueError(f"Unsupported provider '{provider}'. Expected one of: {supported}")

        return provider

    @field_validator("OLLAMA_BASE_URL")
    @classmethod
    def clean_ollama_base_url(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.APP_ENV.lower() == "production":
            if self.AUTH_SECRET_KEY.get_secret_value() == "change-me-in-production":
                raise ValueError("AUTH_SECRET_KEY must be configured in production")

            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError("SQLite is not supported in production")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
