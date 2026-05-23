from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE_PATH = BACKEND_ROOT / ".env"


class AppEnvironment(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
    )

    app_name: str = Field(alias="APP_NAME")
    app_env: str = Field(alias="APP_ENV")
    api_prefix: str = Field(alias="API_PREFIX")
    debug: bool = Field(alias="DEBUG")
    backend_port: int = Field(alias="BACKEND_PORT", ge=1, le=65535)
    database_url: str = Field(alias="DATABASE_URL", min_length=1)
    database_pool_size: int = Field(default=5, alias="DATABASE_POOL_SIZE", ge=1, le=100)
    database_max_overflow: int = Field(default=10, alias="DATABASE_MAX_OVERFLOW", ge=0, le=100)
    database_pool_timeout: int = Field(default=30, alias="DATABASE_POOL_TIMEOUT", ge=1, le=300)
    database_pool_recycle: int = Field(
        default=1800,
        alias="DATABASE_POOL_RECYCLE",
        ge=60,
        le=86400,
    )
    test_database_url: str | None = Field(default=None, alias="TEST_DATABASE_URL")

    clerk_secret_key: str | None = Field(default=None, alias="CLERK_SECRET_KEY")
    clerk_jwt_issuer: str | None = Field(default=None, alias="CLERK_JWT_ISSUER")
    test_jwt_secret: str | None = Field(default=None, alias="TEST_JWT_SECRET")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    chroma_host: str | None = Field(default=None, alias="CHROMA_HOST")
    chroma_port: str | None = Field(default=None, alias="CHROMA_PORT")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    embedding_model: str | None = Field(default=None, alias="EMBEDDING_MODEL")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith("postgresql"):
            raise ValueError("DATABASE_URL must use a PostgreSQL driver URL")
        if "asyncpg" not in normalized:
            raise ValueError("DATABASE_URL must use the asyncpg driver for async SQLAlchemy")
        return normalized

    @field_validator("test_database_url")
    @classmethod
    def validate_test_database_url(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        normalized = str(value).strip()
        if not normalized.startswith("postgresql"):
            raise ValueError("TEST_DATABASE_URL must use a PostgreSQL driver URL")
        if "asyncpg" not in normalized:
            raise ValueError("TEST_DATABASE_URL must use the asyncpg driver")
        return normalized

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith("/"):
            raise ValueError("API_PREFIX must start with '/'")
        return normalized.rstrip("/") or "/"

    @model_validator(mode="after")
    def production_requires_clerk_issuer(self) -> Self:
        if self.app_env.lower() == "production":
            if not self.clerk_jwt_issuer or not str(self.clerk_jwt_issuer).strip():
                raise ValueError("CLERK_JWT_ISSUER is required when APP_ENV is production")
        return self


@lru_cache
def get_app_environment() -> AppEnvironment:
    return AppEnvironment()  # type: ignore[call-arg]
