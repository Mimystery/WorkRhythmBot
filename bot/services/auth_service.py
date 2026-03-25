import secrets

from sqlalchemy import delete, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.repositories.invite_repository import InviteRepository
from bot.database.repositories.user_repository import UserRepository
from bot.enums import UserRole
from bot.models.invite_code import InviteCodeEntity
from bot.models.user import UserEntity
from bot.models.work_pause import WorkPauseEntity
from bot.models.work_session import WorkSessionEntity


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session=session)
        self._invite_repo = InviteRepository(session=session)

    async def get_user_by_telegram_id(self, telegram_id: int) -> UserEntity | None:
        return await self._user_repo.get_by_telegram_id(telegram_id)

    async def get_user_by_id(self, user_id: int) -> UserEntity | None:
        return await self._user_repo.get_by_id(user_id)

    async def get_user_count(self) -> int:
        return await self._user_repo.count()

    async def register_admin_bootstrap(
        self, telegram_id: int, first_name: str, last_name: str
    ) -> UserEntity:
        count = await self._user_repo.count()
        if count > 0:
            raise ValueError("Admin bootstrap only allowed when no users exist")
        if telegram_id != settings.admin_id:
            raise ValueError("Only the configured admin can bootstrap")
        return await self._user_repo.create(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.SUPERADMIN,
        )

    async def validate_invite_code(self, code: str) -> InviteCodeEntity | None:
        return await self._invite_repo.get_unused_by_code(code)

    async def register_user(self, telegram_id: int, code: str) -> UserEntity:
        invite = await self._invite_repo.get_unused_by_code(code)
        if invite is None:
            raise ValueError("Invalid or already used invite code")

        # Superadmin is only assigned via bootstrap
        role = UserRole(invite.role) if invite.role else UserRole.USER

        user = await self._user_repo.create(
            telegram_id=telegram_id,
            first_name=invite.first_name,
            last_name=invite.last_name,
            role=role,
        )
        await self._invite_repo.mark_as_used(invite.id, used_by=user.id)
        return user

    async def delete_user(self, user_id: int, requester_role: UserRole = UserRole.ADMIN) -> str:
        """Delete user and all related data. Returns display name."""
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        if user.is_superadmin:
            raise ValueError("Cannot delete superadmin")
        if user.is_admin and requester_role != UserRole.SUPERADMIN:
            raise ValueError("Only superadmin can delete admins")

        display_name = f"{user.first_name} {user.last_name}"

        session_ids_subq = (
            select(WorkSessionEntity.id)
            .where(WorkSessionEntity.user_id == user_id)
            .scalar_subquery()
        )

        await self._session.execute(
            delete(WorkPauseEntity).where(
                WorkPauseEntity.session_id.in_(session_ids_subq)
            )
        )
        await self._session.execute(
            delete(WorkSessionEntity).where(WorkSessionEntity.user_id == user_id)
        )
        await self._session.execute(
            sa_update(InviteCodeEntity)
            .where(InviteCodeEntity.used_by == user_id)
            .values(used_by=None, used_at=None)
        )
        await self._user_repo.delete_by_id(user_id)

        return display_name

    async def generate_invite_code(
        self, first_name: str, last_name: str, created_by_user_id: int, role: str = "user"
    ) -> InviteCodeEntity:
        code = secrets.token_hex(4).upper()
        return await self._invite_repo.create(
            code=code,
            first_name=first_name,
            last_name=last_name,
            created_by=created_by_user_id,
            role=role,
        )
