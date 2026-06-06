from typing import Any

from src.observability.structuredLogger import get_logger

_logger = get_logger("security.audit")


class AuditLogger:
    def log_auth_event(
        self,
        *,
        event: str,
        org_id: str | None,
        user_id: str | None,
        request_id: str | None,
        ip_address: str | None,
        outcome: str,
        **extra: Any,
    ) -> None:
        _logger.info(
            event,
            category="auth",
            org_id=org_id,
            user_id=user_id,
            request_id=request_id,
            ip_address=ip_address,
            outcome=outcome,
            **extra,
        )

    def log_upload_event(
        self,
        *,
        event: str,
        org_id: str | None,
        user_id: str | None,
        request_id: str | None,
        ip_address: str | None,
        filename: str,
        outcome: str,
        **extra: Any,
    ) -> None:
        _logger.info(
            event,
            category="upload",
            org_id=org_id,
            user_id=user_id,
            request_id=request_id,
            ip_address=ip_address,
            filename=filename,
            outcome=outcome,
            **extra,
        )

    def log_rate_limit_event(
        self,
        *,
        endpoint: str,
        org_id: str | None,
        user_id: str | None,
        request_id: str | None,
        ip_address: str | None,
        retry_after: int,
    ) -> None:
        _logger.warning(
            "rate_limit_blocked",
            category="rate_limit",
            endpoint=endpoint,
            org_id=org_id,
            user_id=user_id,
            request_id=request_id,
            ip_address=ip_address,
            retry_after_seconds=retry_after,
        )

    def log_webhook_event(
        self,
        *,
        event: str,
        svix_id: str | None,
        outcome: str,
        **extra: Any,
    ) -> None:
        _logger.info(
            event,
            category="webhook",
            svix_id=svix_id,
            outcome=outcome,
            **extra,
        )

    def log_delete_event(
        self,
        *,
        event: str,
        org_id: str | None,
        user_id: str | None,
        request_id: str | None,
        resource_id: str | None,
        outcome: str,
        **extra: Any,
    ) -> None:
        _logger.info(
            event,
            category="delete",
            org_id=org_id,
            user_id=user_id,
            request_id=request_id,
            resource_id=resource_id,
            outcome=outcome,
            **extra,
        )


audit_logger = AuditLogger()
