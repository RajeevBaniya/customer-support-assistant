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
    ("GROQ_API_KEY", "groq_api_key"),
    ("GEMINI_API_KEY", "gemini_api_key"),
)


def is_strict_deployment_env(app_env: str) -> bool:
    return app_env.strip().lower() in STRICT_DEPLOYMENT_ENVS


def _field_present(settings: AppEnvironment, attr: str) -> bool:
    raw = getattr(settings, attr, None)
    if raw is None:
        return False
    return bool(str(raw).strip())


def missing_deployment_requirements(settings: AppEnvironment) -> list[str]:
    missing: list[str] = []
    for env_name, attr in _REQUIRED_SECRET_FIELDS:
        if not _field_present(settings, attr):
            missing.append(env_name)
    return missing


def enforce_deployment_settings(settings: AppEnvironment) -> None:
    if not is_strict_deployment_env(settings.app_env):
        return
    missing = missing_deployment_requirements(settings)
    if not missing:
        return
    joined = ", ".join(missing)
    raise ValueError(f"deployment_configuration_incomplete: missing {joined}")
