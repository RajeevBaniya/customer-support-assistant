from __future__ import annotations

from src.core.appEnvironment import AppEnvironment

STRICT_DEPLOYMENT_ENVS = frozenset({"production", "staging"})

_REQUIRED_SECRET_FIELDS: tuple[tuple[str, str], ...] = (
    ("DATABASE_URL", "database_url"),
    ("REDIS_URL", "redis_url"),
    ("PINECONE_API_KEY", "pinecone_api_key"),
    ("PINECONE_INDEX_NAME", "pinecone_index_name"),
    ("PINECONE_CLOUD", "pinecone_cloud"),
    ("PINECONE_REGION", "pinecone_region"),
    ("CLOUDINARY_CLOUD_NAME", "cloudinary_cloud_name"),
    ("CLOUDINARY_API_KEY", "cloudinary_api_key"),
    ("CLOUDINARY_API_SECRET", "cloudinary_api_secret"),
    ("CLERK_JWT_ISSUER", "clerk_jwt_issuer"),
    ("CLERK_WEBHOOK_SIGNING_KEY", "clerk_webhook_signing_key"),
    ("ROOT_AGENT_API_KEY", "root_agent_api_key"),
    ("PLANNING_API_KEY", "planning_api_key"),
    ("QUERY_REWRITE_API_KEY", "query_rewrite_api_key"),
    ("CONTEXT_API_KEY", "context_api_key"),
    ("GENERATION_API_KEY", "generation_api_key"),
    ("REVIEWER_API_KEY", "reviewer_api_key"),
    ("EVALUATION_API_KEY", "evaluation_api_key"),
    ("FALLBACK_GENERATION_API_KEY", "fallback_generation_api_key"),
    ("HUGGINGFACE_API_KEY", "huggingface_api_key"),
)


def is_strict_deployment_env(app_env: str) -> bool:
    return app_env.strip().lower() in STRICT_DEPLOYMENT_ENVS


def _field_present(settings: AppEnvironment, attr: str) -> bool:
    field_value = getattr(settings, attr, None)
    if field_value is None:
        return False
    return bool(str(field_value).strip())


def missing_deployment_requirements(settings: AppEnvironment) -> list[str]:
    missing_fields: list[str] = []
    for env_name, attr in _REQUIRED_SECRET_FIELDS:
        if not _field_present(settings, attr):
            missing_fields.append(env_name)
    return missing_fields


def enforce_deployment_settings(settings: AppEnvironment) -> None:
    if not is_strict_deployment_env(settings.app_env):
        return
    missing_fields = missing_deployment_requirements(settings)
    if not missing_fields:
        return
    joined_missing_fields = ", ".join(missing_fields)
    raise ValueError(f"deployment_configuration_incomplete: missing {joined_missing_fields}")
