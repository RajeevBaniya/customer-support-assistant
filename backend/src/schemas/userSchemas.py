from datetime import datetime
from uuid import UUID

from schemas.commonSchemas import ApiModel


class UserProfileResponse(ApiModel):
    id: UUID
    clerk_user_id: str
    email_address: str
    first_name: str | None
    last_name: str | None
    organization_id: UUID
    created_at: datetime
    updated_at: datetime


class OrganizationSummaryResponse(ApiModel):
    id: UUID
    organization_name: str
    slug: str
    created_at: datetime
    updated_at: datetime
