from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.workspace import WorkspaceEntity


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceRepository:
    session: AsyncSession

    async def get_by_id(self, workspace_id: int) -> WorkspaceEntity | None:
        stmt = select(WorkspaceEntity).where(WorkspaceEntity.id == workspace_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_owner(self, owner_telegram_id: int) -> WorkspaceEntity | None:
        stmt = select(WorkspaceEntity).where(
            WorkspaceEntity.owner_telegram_id == owner_telegram_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self) -> list[WorkspaceEntity]:
        stmt = select(WorkspaceEntity).order_by(WorkspaceEntity.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, name: str, owner_telegram_id: int) -> WorkspaceEntity:
        entity = WorkspaceEntity(name=name, owner_telegram_id=owner_telegram_id)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete_by_id(self, workspace_id: int) -> None:
        stmt = delete(WorkspaceEntity).where(WorkspaceEntity.id == workspace_id)
        await self.session.execute(stmt)
