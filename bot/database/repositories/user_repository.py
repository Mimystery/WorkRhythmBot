from dataclasses import dataclass

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.enums import UserRole, UserStatus
from bot.models.user import UserEntity


@dataclass(frozen=True, slots=True, kw_only=True)
class UserRepository:
    session: AsyncSession

    async def get_by_telegram_id(self, telegram_id: int) -> UserEntity | None:
        stmt = select(UserEntity).where(UserEntity.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> UserEntity | None:
        stmt = select(UserEntity).where(UserEntity.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_in_workspace(self, workspace_id: int) -> list[UserEntity]:
        stmt = (
            select(UserEntity)
            .where(UserEntity.workspace_id == workspace_id)
            .order_by(UserEntity.first_name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        stmt = select(func.count(UserEntity.id))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create(
        self,
        telegram_id: int,
        first_name: str,
        last_name: str,
        role: UserRole = UserRole.USER,
        workspace_id: int | None = None,
    ) -> UserEntity:
        entity = UserEntity(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            role=role,
            workspace_id=workspace_id,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update_status(self, user_id: int, status: UserStatus) -> None:
        stmt = update(UserEntity).where(UserEntity.id == user_id).values(status=status)
        await self.session.execute(stmt)

    async def update_workspace(
        self, user_id: int, workspace_id: int | None, role: UserRole = UserRole.USER
    ) -> None:
        stmt = (
            update(UserEntity)
            .where(UserEntity.id == user_id)
            .values(workspace_id=workspace_id, role=role, status=UserStatus.OFFLINE)
        )
        await self.session.execute(stmt)

    async def delete_by_id(self, user_id: int) -> None:
        stmt = delete(UserEntity).where(UserEntity.id == user_id)
        await self.session.execute(stmt)

    async def clear_workspace(self, workspace_id: int) -> None:
        """Remove all users from a workspace (set workspace_id=None, role=user)."""
        stmt = (
            update(UserEntity)
            .where(UserEntity.workspace_id == workspace_id)
            .values(workspace_id=None, role=UserRole.USER, status=UserStatus.OFFLINE)
        )
        await self.session.execute(stmt)
