from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import redis.asyncio as redis_async
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src import models
from src.api.v1.analyticsRoutes import analytics_router
from src.api.v1.authRoutes import auth_router
from src.api.v1.chatRoutes import chat_router
from src.api.v1.documentRoutes import document_router
from src.api.v1.evaluationRoutes import evaluation_router
from src.api.v1.healthRoutes import health_router
from src.api.v1.metricsRoutes import metrics_router
from src.api.v1.ragRoutes import rag_router
from src.api.v1.retrievalRoutes import retrieval_router
from src.api.v1.userRoutes import user_router
from src.api.v1.webhookRoutes import webhook_router
from src.core.appEnvironment import get_app_environment
from src.database.databaseManager import DatabaseManager
from src.database.databaseSession import (
    clear_session_factory,
    configure_session_factory,
    get_session_factory,
)
from src.database.migrationState import inspect_migration_state
from src.evaluation import models as evaluation_models
from src.middleware.authMiddleware import AuthMiddleware
from src.middleware.observabilityMiddleware import ObservabilityMiddleware
from src.middleware.organizationMiddleware import OrganizationMiddleware
from src.middleware.secureHeadersMiddleware import SecureHeadersMiddleware
from src.observability.structuredLogger import configure_structured_logging, get_logger
from src.shared.customExceptions import BaseApplicationException, RateLimitException
from src.shared.responseFormatter import format_error_response

_ = (models.__spec__, evaluation_models.__spec__)

logger = get_logger(__name__)


def _register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(BaseApplicationException)
    async def handle_application_exception(
        _request: Request,
        exception: BaseApplicationException,
    ) -> JSONResponse:
        payload = format_error_response(
            code=exception.error_code,
            message=exception.message,
            details=exception.details,
        )
        response = JSONResponse(status_code=exception.status_code, content=payload)
        if isinstance(exception, RateLimitException):
            response.headers["Retry-After"] = str(exception.retry_after)
        return response


def _register_routers(application: FastAPI) -> None:
    settings = application.state.settings
    application.include_router(health_router)
    application.include_router(metrics_router)
    application.include_router(webhook_router)
    application.include_router(auth_router, prefix=settings.api_prefix)
    application.include_router(user_router, prefix=settings.api_prefix)
    application.include_router(chat_router, prefix=settings.api_prefix)
    application.include_router(document_router, prefix=settings.api_prefix)
    application.include_router(evaluation_router, prefix=settings.api_prefix)
    application.include_router(analytics_router, prefix=settings.api_prefix)
    application.include_router(retrieval_router, prefix=settings.api_prefix)
    application.include_router(rag_router, prefix=settings.api_prefix)


def _build_redis_client(settings) -> redis_async.Redis | None:
    url = settings.redis_url
    if not url or not str(url).strip():
        return None
    from src.realtime.redis_connection import normalize_redis_url_for_tls

    normalized = normalize_redis_url_for_tls(str(url))
    return redis_async.Redis.from_url(normalized, decode_responses=True)


def create_application() -> FastAPI:
    settings = get_app_environment()
    configure_structured_logging(debug=settings.debug)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        startup_logger = get_logger("application.lifecycle")
        startup_logger.info(
            "application_starting",
            application_name=settings.app_name,
            app_env=settings.app_env,
            api_prefix=settings.api_prefix,
        )

        database_manager = DatabaseManager(settings)
        configure_session_factory(database_manager.engine)
        migration_report = await inspect_migration_state(database_manager.engine)
        if not migration_report.aligned:
            startup_logger.warning(
                "migration_revision_mismatch",
                current_revision=migration_report.current_revision,
                head_revision=migration_report.head_revision,
            )

        redis_client = _build_redis_client(settings)

        application.state.settings = settings
        application.state.started_at = datetime.now(UTC)
        application.state.database_manager = database_manager
        application.state.migration_report = migration_report
        application.state.async_session_factory = get_session_factory()
        application.state.redis_client = redis_client

        connected = await database_manager.verify_connection()
        startup_logger.info(
            "database_connectivity_checked",
            connected=connected,
            migration_aligned=migration_report.aligned,
        )

        startup_logger.info("application_started")
        yield

        if redis_client is not None:
            await redis_client.aclose()

        await database_manager.close()
        clear_session_factory()
        startup_logger.info("application_shutdown_complete")

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    application.state.settings = settings
    _register_exception_handlers(application)
    application.add_middleware(OrganizationMiddleware)
    application.add_middleware(AuthMiddleware)
    application.add_middleware(ObservabilityMiddleware)
    application.add_middleware(SecureHeadersMiddleware)
    _register_routers(application)

    logger.info(
        "application_configured",
        application_name=settings.app_name,
        api_v1_prefix=settings.api_prefix,
    )
    return application
