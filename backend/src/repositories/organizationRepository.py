import re
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.organizationModel import Organization


def normalize_slug(raw: str) -> str:
    lowered = raw.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return (slug or "workspace")[:128]


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(Organization.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def reserve_unique_slug(self, base: str) -> str:
        candidate = normalize_slug(base)
        slug = candidate
        for _ in range(24):
            existing = await self.get_by_slug(slug)
            if existing is None:
                return slug
            suffix = uuid4().hex[:8]
            stem = candidate[: max(1, 120 - len(suffix) - 1)]
            slug = f"{stem}-{suffix}"
        return f"{candidate[:100]}-{uuid4().hex}"

    async def add(self, organization: Organization) -> Organization:
        self._session.add(organization)
        await self._session.flush()
        return organization

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        return await self._session.get(Organization, organization_id)
