from __future__ import annotations

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import BaseEntityWithAudit


class WorkspaceEntity(BaseEntityWithAudit):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    members: Mapped[list["UserEntity"]] = relationship(
        back_populates="workspace", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Workspace {self.name} (id={self.id})>"
