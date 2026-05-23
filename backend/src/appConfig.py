from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import models  # noqa: F401
from api.v1.authRoutes import auth_router
from api.v1.healthRoutes import health_router
from api.v1.userRoutes import user_router
from core.appEnvironment import get_app_environment
from database.databaseManager import DatabaseManager
from database.databaseSession import (
    clear_session_factory,
    configure_session_factory,
    get_session_factory,
)
from database.migrationState import inspect_migration_state
from middleware.authMiddleware import AuthMiddleware
from middleware.organizationMiddleware import OrganizationMiddleware
from observability.structuredLogger import configure_structured_logging, get_logger
from shared.customExceptions import BaseApplicationException
from shared.responseFormatter import format_error_response

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
        return JSONResponse(status_code=exception.status_code, content=payload)


def _register_routers(application: FastAPI) -> None:
    settings = application.state.settings
    application.include_router(health_router)
    application.include_router(auth_router, prefix=settings.api_prefix)
    application.include_router(user_router, prefix=settings.api_prefix)


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

        application.state.settings = settings
        application.state.started_at = datetime.now(UTC)
        application.state.database_manager = database_manager
        application.state.migration_report = migration_report
        application.state.async_session_factory = get_session_factory()

        connected = await database_manager.verify_connection()
        startup_logger.info(
            "database_connectivity_checked",
            connected=connected,
            migration_aligned=migration_report.aligned,
        )

        startup_logger.info("application_started")
        yield

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
    _register_routers(application)

    logger.info(
        "application_configured",
        application_name=settings.app_name,
        api_v1_prefix=settings.api_prefix,
    )
    return application
