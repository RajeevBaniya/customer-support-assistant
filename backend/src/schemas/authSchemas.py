from datetime import datetime

from pydantic import Field

from src.schemas.commonSchemas import ApiModel


class ClerkTokenPayload(ApiModel):
    sub: str = Field(min_length=1, max_length=128)
    email: str | None = None
    email_verified: bool | None = None
    given_name: str | None = None
    family_name: str | None = None
    issuer: str
    expires_at: datetime


class AuthMeResponse(ApiModel):
    clerk_user_id: str
    email: str | None
    email_verified: bool | None
    given_name: str | None
    family_name: str | None
    issuer: str
    expires_at: datetime
