from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class SuccessResponse(BaseModel, Generic[DataT]):
    success: bool = True
    data: DataT
    message: str | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


def format_success_response(
    data: DataT,
    *,
    message: str | None = None,
) -> dict[str, Any]:
    payload = SuccessResponse[DataT](data=data, message=message)
    return payload.model_dump(exclude_none=True)


def format_error_response(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details or {},
        ),
    )
    return payload.model_dump()
