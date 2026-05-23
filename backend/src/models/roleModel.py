from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.baseModel import BaseRow
from models.userRolesTable import user_roles_table

if TYPE_CHECKING:
    from models.userModel import User


class Role(BaseRow):
    __tablename__ = "roles"

    role_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    role_description: Mapped[str | None] = mapped_column(String(512), nullable=True)

    users: Mapped[list[User]] = relationship(
        "User",
        secondary=user_roles_table,
        back_populates="roles",
    )
