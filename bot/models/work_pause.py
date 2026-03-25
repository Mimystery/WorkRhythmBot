from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import BaseEntityWithAudit


class WorkPauseEntity(BaseEntityWithAudit):
    __tablename__ = "work_pauses"

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("work_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paused_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    session: Mapped["WorkSessionEntity"] = relationship(
        back_populates="pauses", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<WorkPause {self.id} session={self.session_id}>"
