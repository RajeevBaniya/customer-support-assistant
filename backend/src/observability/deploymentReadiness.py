from __future__ import annotations

from typing import TypedDict

from src.core.appEnvironment import AppEnvironment
from src.core.deploymentSettingsValidation import (
    is_strict_deployment_env,
    missing_deployment_requirements,
)
from src.database.migrationState import MigrationReport
from src.jobs.jobConfig import celery_broker_url


class DeploymentReadinessBundle(TypedDict, total=False):
    deployment_ready: bool
    missing_requirements: list[str]
    warnings: list[str]


def _collect_warnings(settings: AppEnvironment, migration: MigrationReport | None) -> list[str]:
    warnings: list[str] = []
    env = settings.app_env.strip().lower()
    if is_strict_deployment_env(settings.app_env) and settings.debug:
        warnings.append("debug_enabled_in_strict_environment")
    if migration is not None and not migration.aligned:
        warnings.append("database_migration_revision_not_aligned")
    if is_strict_deployment_env(settings.app_env) and celery_broker_url(settings) is None:
        warnings.append("celery_broker_not_resolved")
    if env == "production" and settings.test_jwt_secret:
        warnings.append("test_jwt_secret_enabled_in_production")
    return warnings


def deployment_readiness_bundle(
    settings: AppEnvironment,
    *,
    migration: MigrationReport | None = None,
) -> DeploymentReadinessBundle:
    missing = missing_deployment_requirements(settings)
    warnings = _collect_warnings(settings, migration)
    if is_strict_deployment_env(settings.app_env):
        ready = len(missing) == 0
    else:
        ready = True
    return {
        "deployment_ready": ready,
        "missing_requirements": missing,
        "warnings": warnings,
    }
