from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.baseModel import BaseRow

if TYPE_CHECKING:
    from src.models.userModel import User


class Organization(BaseRow):
    __tablename__ = "organizations"

    organization_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)

    users: Mapped[list[User]] = relationship("User", back_populates="organization")
