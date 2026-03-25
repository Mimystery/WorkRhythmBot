from __future__ import annotations

from sqlalchemy import BigInteger, Enum as SQLEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.enums import UserRole, UserStatus
from bot.models.base import BaseEntityWithAudit


class UserEntity(BaseEntityWithAudit):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(UserStatus, name="user_status"),
        nullable=False,
        default=UserStatus.OFFLINE,
    )
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.USER,
    )

    work_sessions: Mapped[list["WorkSessionEntity"]] = relationship(
        back_populates="user", lazy="selectin"
    )

    @property
    def is_admin(self) -> bool:
        return self.role in (UserRole.ADMIN, UserRole.SUPERADMIN)

    @property
    def is_superadmin(self) -> bool:
        return self.role == UserRole.SUPERADMIN

    def __repr__(self) -> str:
        return f"<User {self.first_name} {self.last_name} ({self.telegram_id}) role={self.role}>"
