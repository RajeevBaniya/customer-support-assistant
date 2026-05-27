from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.baseModel import BaseRow
from src.models.organizationModel import Organization
from src.models.roleModel import Role
from src.models.userRolesTable import user_roles_table


class User(BaseRow):
    __tablename__ = "users"

    clerk_user_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    email_address: Mapped[str] = mapped_column(String(320), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )

    organization: Mapped[Organization] = relationship("Organization", back_populates="users")
    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary=user_roles_table,
        back_populates="users",
    )
