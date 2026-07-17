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
        extra="ignore",
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

    enable_original_file_storage: bool = Field(default=False, alias="ENABLE_ORIGINAL_FILE_STORAGE")
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_service_role_key: str | None = Field(default=None, alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_storage_bucket: str | None = Field(default=None, alias="SUPABASE_STORAGE_BUCKET")

    root_agent_api_key: str | None = Field(default=None, alias="ROOT_AGENT_API_KEY")
    root_agent_model: str = Field(alias="ROOT_AGENT_MODEL", min_length=1)

    planning_api_key: str | None = Field(default=None, alias="PLANNING_API_KEY")
    planning_model: str = Field(alias="PLANNING_MODEL", min_length=1)

    query_rewrite_api_key: str | None = Field(default=None, alias="QUERY_REWRITE_API_KEY")
    query_rewrite_model: str = Field(alias="QUERY_REWRITE_MODEL", min_length=1)

    context_api_key: str | None = Field(default=None, alias="CONTEXT_API_KEY")
    context_model: str = Field(alias="CONTEXT_MODEL", min_length=1)

    generation_api_key: str | None = Field(default=None, alias="GENERATION_API_KEY")
    generation_model: str = Field(alias="GENERATION_MODEL", min_length=1)

    reviewer_api_key: str | None = Field(default=None, alias="REVIEWER_API_KEY")
    reviewer_model: str = Field(alias="REVIEWER_MODEL", min_length=1)

    evaluation_api_key: str | None = Field(default=None, alias="EVALUATION_API_KEY")
    evaluation_model: str = Field(alias="EVALUATION_MODEL", min_length=1)

    fallback_generation_api_key: str | None = Field(
        default=None, alias="FALLBACK_GENERATION_API_KEY"
    )
    fallback_generation_model: str = Field(alias="FALLBACK_GENERATION_MODEL", min_length=1)
    huggingface_api_key: str | None = Field(default=None, alias="HUGGINGFACE_API_KEY")
    embedding_model: str = Field(
        default="BAAI/bge-base-en-v1.5",
        alias="EMBEDDING_MODEL",
        min_length=1,
    )
    embedding_batch_size: int = Field(default=100, alias="EMBEDDING_BATCH_SIZE", ge=1, le=10000)
    embedding_max_retries: int = Field(default=3, alias="EMBEDDING_MAX_RETRIES", ge=1, le=10)
    embedding_retry_delay_seconds: float = Field(
        default=2.0, alias="EMBEDDING_RETRY_DELAY_SECONDS", ge=0.1, le=60.0
    )
    embedding_timeout_seconds: float = Field(
        default=30.0, alias="EMBEDDING_TIMEOUT_SECONDS", ge=1.0, le=300.0
    )
    retrieval_default_top_k: int = Field(default=8, alias="RETRIEVAL_DEFAULT_TOP_K", ge=1, le=50)
    retrieval_max_top_k: int = Field(default=50, alias="RETRIEVAL_MAX_TOP_K", ge=1, le=100)
    retrieval_minimum_similarity: float = Field(
        default=0.20,
        alias="RETRIEVAL_MIN_SIMILARITY",
        ge=0.0,
        le=1.0,
    )
    hybrid_retrieval_enabled: bool = Field(
        default=True,
        alias="HYBRID_RETRIEVAL_ENABLED",
    )
    hybrid_candidate_pool_size: int = Field(
        default=100,
        alias="HYBRID_CANDIDATE_POOL_SIZE",
        ge=10,
        le=500,
    )
    rrf_k: int = Field(
        default=60,
        alias="RRF_K",
        ge=10,
        le=200,
    )

    rag_max_chunks: int = Field(default=6, alias="RAG_MAX_CHUNKS", ge=1, le=50)
    rag_max_context_chars: int = Field(
        default=12000,
        alias="RAG_MAX_CONTEXT_CHARS",
        ge=500,
        le=500_000,
    )
    rag_max_context_tokens: int = Field(
        default=6000,
        alias="RAG_MAX_CONTEXT_TOKENS",
        ge=100,
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
    chat_memory_max_tokens: int = Field(
        default=2000,
        alias="CHAT_MEMORY_MAX_TOKENS",
        ge=100,
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

    chunk_size: int = Field(
        default=1200,
        alias="CHUNK_SIZE",
        ge=10,
        le=50000,
    )
    chunk_overlap: int = Field(
        default=150,
        alias="CHUNK_OVERLAP",
        ge=0,
        le=25000,
    )
    parent_chunk_size: int = Field(
        default=1200,
        alias="PARENT_CHUNK_SIZE",
        ge=10,
        le=50000,
    )
    child_chunk_size: int = Field(
        default=400,
        alias="CHILD_CHUNK_SIZE",
        ge=10,
        le=25000,
    )
    child_chunk_overlap: int = Field(
        default=50,
        alias="CHILD_CHUNK_OVERLAP",
        ge=0,
        le=12500,
    )

    ingestion_version: str = Field(
        default="1.0.0",
        alias="INGESTION_VERSION",
    )
    semantic_chunk_max_tokens: int = Field(
        default=300,
        alias="SEMANTIC_CHUNK_MAX_TOKENS",
        ge=10,
        le=50000,
    )
    semantic_chunk_min_tokens: int = Field(
        default=25,
        alias="SEMANTIC_CHUNK_MIN_TOKENS",
        ge=1,
        le=25000,
    )
    clerk_webhook_signing_key: str | None = Field(default=None, alias="CLERK_WEBHOOK_SIGNING_KEY")

    cors_allowed_origins: list[str] = Field(default=[], alias="CORS_ALLOWED_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: list[str] = Field(default=["*"], alias="CORS_ALLOW_METHODS")
    cors_allow_headers: list[str] = Field(default=["*"], alias="CORS_ALLOW_HEADERS")

    rate_limit_window_seconds: int = Field(
        default=60,
        alias="RATE_LIMIT_WINDOW_SECONDS",
        ge=1,
        le=3600,
    )
    rate_limit_chat_message: int = Field(
        default=60,
        alias="RATE_LIMIT_CHAT_MESSAGE",
        ge=1,
        le=10000,
    )
    rate_limit_chat_stream: int = Field(
        default=30,
        alias="RATE_LIMIT_CHAT_STREAM",
        ge=1,
        le=10000,
    )
    rate_limit_rag_ask: int = Field(
        default=60,
        alias="RATE_LIMIT_RAG_ASK",
        ge=1,
        le=10000,
    )
    rate_limit_documents_upload: int = Field(
        default=20,
        alias="RATE_LIMIT_DOCUMENTS_UPLOAD",
        ge=1,
        le=10000,
    )
    rate_limit_evaluation_run: int = Field(
        default=10,
        alias="RATE_LIMIT_EVALUATION_RUN",
        ge=1,
        le=10000,
    )
    rate_limit_benchmark_run: int = Field(
        default=5,
        alias="RATE_LIMIT_BENCHMARK_RUN",
        ge=1,
        le=10000,
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

    @field_validator(
        "embedding_model",
        "root_agent_model",
        "planning_model",
        "query_rewrite_model",
        "context_model",
        "generation_model",
        "reviewer_model",
        "evaluation_model",
        "fallback_generation_model",
    )
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

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            if not value.strip():
                return []
            return [x.strip() for x in value.split(",") if x.strip()]
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        return []

    @field_validator("cors_allow_methods", "cors_allow_headers", mode="before")
    @classmethod
    def parse_cors_lists(cls, value: object) -> list[str]:
        if value is None:
            return ["*"]
        if isinstance(value, str):
            if not value.strip():
                return ["*"]
            return [x.strip() for x in value.split(",") if x.strip()]
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        return ["*"]

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
    def chunk_overlap_consistency(self) -> Self:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be < CHUNK_SIZE")
        return self

    @model_validator(mode="after")
    def strict_env_requires_clerk_issuer(self) -> Self:
        env = self.app_env.lower()
        if env in {"production", "staging"}:
            if not self.clerk_jwt_issuer or not str(self.clerk_jwt_issuer).strip():
                raise ValueError(
                    "CLERK_JWT_ISSUER is required when APP_ENV is production or staging"
                )
        return self


@lru_cache
def get_app_environment() -> AppEnvironment:
    settings = AppEnvironment()  # type: ignore[call-arg]
    from src.core.deploymentSettingsValidation import enforce_deployment_settings

    enforce_deployment_settings(settings)
    return settings
