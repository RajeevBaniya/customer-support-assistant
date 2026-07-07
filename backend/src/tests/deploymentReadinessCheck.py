import pytest

from src.core.appEnvironment import AppEnvironment
from src.core.deploymentSettingsValidation import (
    enforce_deployment_settings,
    missing_deployment_requirements,
)
from src.observability.deploymentReadiness import deployment_readiness_bundle


def test_missing_requirements_detects_empty_redis() -> None:
    settings = AppEnvironment(
        APP_ENV="production",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://u:p@localhost:5432/db",
        REDIS_URL="",
        PINECONE_API_KEY="k",
        PINECONE_INDEX_NAME="idx",
        PINECONE_CLOUD="aws",
        PINECONE_REGION="us-east-1",
        CLOUDINARY_CLOUD_NAME="c",
        CLOUDINARY_API_KEY="k",
        CLOUDINARY_API_SECRET="s",
        CLERK_JWT_ISSUER="https://issuer.example",
        GROQ_API_KEY="g",
        GEMINI_API_KEY="m",
    )
    missing = missing_deployment_requirements(settings)
    assert "REDIS_URL" in missing


def test_enforce_skipped_for_test_env() -> None:
    settings = AppEnvironment(
        APP_ENV="test",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://u:p@localhost:5432/db",
    )
    enforce_deployment_settings(settings)


def test_enforce_raises_for_incomplete_production() -> None:
    settings = AppEnvironment.model_construct(
        app_env="production",
        debug=False,
        database_url="postgresql+asyncpg://u:p@localhost:5432/db",
        clerk_jwt_issuer="https://issuer.example",
        redis_url=None,
        pinecone_api_key=None,
        pinecone_index_name=None,
        pinecone_cloud=None,
        pinecone_region=None,
        cloudinary_cloud_name=None,
        cloudinary_api_key=None,
        cloudinary_api_secret=None,
        groq_api_key=None,
        gemini_api_key=None,
    )
    with pytest.raises(ValueError, match="deployment_configuration_incomplete"):
        enforce_deployment_settings(settings)


def test_deployment_bundle_ready_in_test_env() -> None:
    settings = AppEnvironment(
        APP_ENV="test",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://u:p@localhost:5432/db",
    )
    bundle = deployment_readiness_bundle(settings)
    assert bundle["deployment_ready"] is True
