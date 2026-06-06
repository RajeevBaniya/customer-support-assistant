from typing import Any


class BaseApplicationException(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class ValidationException(BaseApplicationException):
    def __init__(
        self,
        message: str = "Request validation failed",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code="validation_error",
            status_code=422,
            details=details,
        )


class AuthException(BaseApplicationException):
    def __init__(
        self,
        message: str = "Authentication failed",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code="auth_error",
            status_code=401,
            details=details,
        )


class ResourceNotFoundException(BaseApplicationException):
    def __init__(
        self,
        message: str = "Resource not found",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code="resource_not_found",
            status_code=404,
            details=details,
        )


class RateLimitException(BaseApplicationException):
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        retry_after: int = 60,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {"retry_after_seconds": retry_after, **(details or {})}
        super().__init__(
            message,
            error_code="rate_limit_exceeded",
            status_code=429,
            details=merged,
        )
        self.retry_after = retry_after


class WebhookVerificationException(BaseApplicationException):
    def __init__(
        self,
        message: str = "Webhook verification failed",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code="webhook_verification_failed",
            status_code=400,
            details=details,
        )
