"""SessionTool wrapping organization and user details access."""

from uuid import UUID

from pydantic import BaseModel

from src.models.organizationModel import Organization
from src.models.userModel import User
from src.repositories.organizationRepository import OrganizationRepository
from src.runtimeTools.baseTool import BaseTool


class LoadOrganizationRequest(BaseModel):
    """Schema for loading organization info."""

    organization_id: UUID


class LoadUserRequest(BaseModel):
    """Schema for loading user info."""

    user_id: UUID


class SessionTool(BaseTool):
    """Active session context loading tool."""

    async def load_organization(
        self, request: LoadOrganizationRequest
    ) -> Organization | None:
        """Load organization details."""
        repository = OrganizationRepository(self._session)
        return await repository.get_by_id(request.organization_id)

    async def load_user(self, request: LoadUserRequest) -> User | None:
        """Load user details."""
        return await self._session.get(User, request.user_id)
