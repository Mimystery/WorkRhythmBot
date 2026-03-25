from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import BaseEntityWithAudit


class InviteCodeEntity(BaseEntityWithAudit):
    __tablename__ = "invite_codes"

    code: Mapped[str] = mapped_column(String(8), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    workspace_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("workspaces.id"), nullable=False, index=True
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    used_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    workspace: Mapped["WorkspaceEntity"] = relationship(lazy="selectin")
    creator: Mapped["UserEntity"] = relationship(
        foreign_keys=[created_by], lazy="selectin"
    )
    user: Mapped["UserEntity | None"] = relationship(
        foreign_keys=[used_by], lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<InviteCode {self.code} for {self.first_name} {self.last_name}>"
