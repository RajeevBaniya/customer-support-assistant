from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

DataType = TypeVar("DataType")


class SuccessResponse(BaseModel, Generic[DataType]):
    """Standard success API response schema."""

    success: bool = True
    data: DataType
    message: str | None = None


class ErrorDetail(BaseModel):
    """Details block for error response schemas."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard error API response schema."""

    success: bool = False
    error: ErrorDetail


def format_success_response(
    data: DataType,
    *,
    message: str | None = None,
) -> dict[str, Any]:
    """Format success response as serialized dictionary."""
    payload = SuccessResponse[DataType](data=data, message=message)
    return payload.model_dump(exclude_none=True)


def format_error_response(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Format error response as serialized dictionary."""
    payload = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details or {},
        ),
    )
    return payload.model_dump()
