from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class UuidField(BaseModel):
    id: UUID


class TimestampFields(BaseModel):
    created_at: datetime
    updated_at: datetime


class PageParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
