from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.enums import SessionStatus
from bot.models.base import BaseEntityWithAudit


class WorkSessionEntity(BaseEntityWithAudit):
    __tablename__ = "work_sessions"
    __table_args__ = (
        Index("ix_work_sessions_user_status", "user_id", "status"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus, name="session_status"),
        nullable=False,
        default=SessionStatus.ACTIVE,
    )

    user: Mapped["UserEntity"] = relationship(
        back_populates="work_sessions", lazy="selectin"
    )
    pauses: Mapped[list["WorkPauseEntity"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<WorkSession {self.id} user={self.user_id} status={self.status}>"
