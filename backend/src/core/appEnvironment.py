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

    app_name: str = Field(default="RecallStack", alias="APP_NAME", min_length=1)
    app_env: str = Field(alias="APP_ENV")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    debug: bool = Field(alias="DEBUG")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT", ge=1, le=65535)
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

    pinecone_api_key: str | None = Field(default=None, alias="PINECONE_API_KEY")
    pinecone_index_name: str | None = Field(default=None, alias="PINECONE_INDEX_NAME")
    pinecone_cloud: str | None = Field(default=None, alias="PINECONE_CLOUD")
    pinecone_region: str | None = Field(default=None, alias="PINECONE_REGION")

    cloudinary_cloud_name: str | None = Field(default=None, alias="CLOUDINARY_CLOUD_NAME")
    cloudinary_api_key: str | None = Field(default=None, alias="CLOUDINARY_API_KEY")
    cloudinary_api_secret: str | None = Field(default=None, alias="CLOUDINARY_API_SECRET")

    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    embedding_model: str = Field(
        default="BAAI/bge-base-en-v1.5",
        alias="EMBEDDING_MODEL",
        min_length=1,
    )
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE", ge=1, le=512)
    retrieval_default_top_k: int = Field(default=8, alias="RETRIEVAL_DEFAULT_TOP_K", ge=1, le=50)
    retrieval_max_top_k: int = Field(default=50, alias="RETRIEVAL_MAX_TOP_K", ge=1, le=100)
    retrieval_minimum_similarity: float = Field(
        default=0.20,
        alias="RETRIEVAL_MIN_SIMILARITY",
        ge=0.0,
        le=1.0,
    )
    active_llm_provider: str = Field(default="groq", alias="ACTIVE_LLM_PROVIDER", min_length=1)
    groq_model: str = Field(default="llama-3.1-8b-instant", alias="GROQ_MODEL", min_length=1)
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL", min_length=1)
    rag_max_chunks: int = Field(default=6, alias="RAG_MAX_CHUNKS", ge=1, le=50)
    rag_max_context_chars: int = Field(
        default=12000,
        alias="RAG_MAX_CONTEXT_CHARS",
        ge=500,
        le=500_000,
    )
    llm_timeout_seconds: float = Field(default=60.0, alias="LLM_TIMEOUT_SECONDS", ge=5.0, le=300.0)
    chat_history_max_messages: int = Field(
        default=12,
        alias="CHAT_HISTORY_MAX_MESSAGES",
        ge=1,
        le=50,
    )
    chat_history_max_chars: int = Field(
        default=8000,
        alias="CHAT_HISTORY_MAX_CHARS",
        ge=500,
        le=100_000,
    )
    redis_stream_ttl_seconds: int = Field(
        default=900,
        alias="REDIS_STREAM_TTL_SECONDS",
        ge=60,
        le=86400,
    )
    chat_stream_max_duration_seconds: int = Field(
        default=180,
        alias="CHAT_STREAM_MAX_DURATION_SECONDS",
        ge=30,
        le=3600,
    )
    celery_broker_url: str | None = Field(default=None, alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(default=None, alias="CELERY_RESULT_BACKEND")
    ingestion_max_retries: int = Field(default=5, alias="INGESTION_MAX_RETRIES", ge=0, le=20)
    ingestion_retry_backoff_seconds: int = Field(
        default=10,
        alias="INGESTION_RETRY_BACKOFF_SECONDS",
        ge=1,
        le=600,
    )

    @field_validator("app_name", mode="before")
    @classmethod
    def app_name_or_default(cls, value: object) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            return "RecallStack"
        return str(value).strip()

    @field_validator("api_prefix", mode="before")
    @classmethod
    def api_prefix_or_default(cls, value: object) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            return "/api/v1"
        return str(value).strip()

    @field_validator("backend_port", mode="before")
    @classmethod
    def backend_port_or_default(cls, value: object) -> object:
        if value is None:
            return 8000
        if isinstance(value, str) and not value.strip():
            return 8000
        return value

    @field_validator("embedding_model", "groq_model", "gemini_model")
    @classmethod
    def strip_nonempty_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("pinecone_index_name", "pinecone_cloud", "pinecone_region", mode="before")
    @classmethod
    def empty_pinecone_str_to_none(cls, value: object) -> str | None:
        if value is None:
            return None
        s = str(value).strip()
        return s or None

    @field_validator("active_llm_provider")
    @classmethod
    def normalize_active_llm_provider(cls, value: str) -> str:
        name = value.strip().lower()
        if name not in {"groq", "gemini"}:
            raise ValueError("ACTIVE_LLM_PROVIDER must be 'groq' or 'gemini'")
        return name

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

    @property
    def resolved_storage_provider(self) -> str:
        return "cloudinary"

    @property
    def resolved_embedding_model(self) -> str:
        return self.embedding_model.strip()

    def pinecone_configured(self) -> bool:
        key = self.pinecone_api_key
        name = self.pinecone_index_name
        cloud = self.pinecone_cloud
        region = self.pinecone_region
        if not key or not str(key).strip():
            return False
        if not name or not str(name).strip():
            return False
        if not cloud or not str(cloud).strip():
            return False
        if not region or not str(region).strip():
            return False
        return True

    def cloudinary_configured(self) -> bool:
        return bool(
            self.cloudinary_cloud_name
            and str(self.cloudinary_cloud_name).strip()
            and self.cloudinary_api_key
            and str(self.cloudinary_api_key).strip()
            and self.cloudinary_api_secret
            and str(self.cloudinary_api_secret).strip()
        )

    @model_validator(mode="after")
    def retrieval_top_k_consistency(self) -> Self:
        if self.retrieval_default_top_k > self.retrieval_max_top_k:
            raise ValueError("RETRIEVAL_DEFAULT_TOP_K must be <= RETRIEVAL_MAX_TOP_K")
        return self

    @model_validator(mode="after")
    def production_requires_clerk_issuer(self) -> Self:
        if self.app_env.lower() == "production":
            if not self.clerk_jwt_issuer or not str(self.clerk_jwt_issuer).strip():
                raise ValueError("CLERK_JWT_ISSUER is required when APP_ENV is production")
        return self


@lru_cache
def get_app_environment() -> AppEnvironment:
    return AppEnvironment()  # type: ignore[call-arg]
