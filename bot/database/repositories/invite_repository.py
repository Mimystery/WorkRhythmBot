from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.invite_code import InviteCodeEntity


@dataclass(frozen=True, slots=True, kw_only=True)
class InviteRepository:
    session: AsyncSession

    async def get_by_code(self, code: str) -> InviteCodeEntity | None:
        stmt = select(InviteCodeEntity).where(InviteCodeEntity.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_unused_by_code(self, code: str) -> InviteCodeEntity | None:
        stmt = select(InviteCodeEntity).where(
            InviteCodeEntity.code == code,
            InviteCodeEntity.used_by.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        code: str,
        first_name: str,
        last_name: str,
        created_by: int,
        role: str = "user",
    ) -> InviteCodeEntity:
        entity = InviteCodeEntity(
            code=code,
            first_name=first_name,
            last_name=last_name,
            created_by=created_by,
            role=role,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def mark_as_used(self, code_id: int, used_by: int) -> None:
        stmt = (
            update(InviteCodeEntity)
            .where(InviteCodeEntity.id == code_id)
            .values(used_by=used_by, used_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
