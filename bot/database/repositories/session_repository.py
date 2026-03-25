from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.enums import SessionStatus
from bot.models.work_pause import WorkPauseEntity
from bot.models.work_session import WorkSessionEntity


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionRepository:
    session: AsyncSession

    async def get_active_session(self, user_id: int) -> WorkSessionEntity | None:
        stmt = (
            select(WorkSessionEntity)
            .where(
                WorkSessionEntity.user_id == user_id,
                WorkSessionEntity.status.in_([SessionStatus.ACTIVE, SessionStatus.PAUSED]),
            )
            .options(selectinload(WorkSessionEntity.pauses))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_today_sessions(self, user_id: int) -> list[WorkSessionEntity]:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stmt = (
            select(WorkSessionEntity)
            .where(
                WorkSessionEntity.user_id == user_id,
                WorkSessionEntity.started_at >= today_start,
            )
            .options(selectinload(WorkSessionEntity.pauses))
            .order_by(WorkSessionEntity.started_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_session(self, user_id: int) -> WorkSessionEntity:
        now = datetime.now(timezone.utc)
        entity = WorkSessionEntity(
            user_id=user_id,
            started_at=now,
            status=SessionStatus.ACTIVE,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def end_session(self, session_id: int) -> None:
        stmt = (
            update(WorkSessionEntity)
            .where(WorkSessionEntity.id == session_id)
            .values(
                ended_at=datetime.now(timezone.utc),
                status=SessionStatus.COMPLETED,
            )
        )
        await self.session.execute(stmt)

    async def update_session_status(
        self, session_id: int, status: SessionStatus
    ) -> None:
        stmt = (
            update(WorkSessionEntity)
            .where(WorkSessionEntity.id == session_id)
            .values(status=status)
        )
        await self.session.execute(stmt)

    async def create_pause(self, session_id: int) -> WorkPauseEntity:
        entity = WorkPauseEntity(
            session_id=session_id,
            paused_at=datetime.now(timezone.utc),
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def end_pause(self, pause_id: int) -> None:
        stmt = (
            update(WorkPauseEntity)
            .where(WorkPauseEntity.id == pause_id)
            .values(resumed_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)

    async def get_open_pause(self, session_id: int) -> WorkPauseEntity | None:
        stmt = select(WorkPauseEntity).where(
            WorkPauseEntity.session_id == session_id,
            WorkPauseEntity.resumed_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pauses_for_session(
        self, session_id: int
    ) -> list[WorkPauseEntity]:
        stmt = (
            select(WorkPauseEntity)
            .where(WorkPauseEntity.session_id == session_id)
            .order_by(WorkPauseEntity.paused_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
