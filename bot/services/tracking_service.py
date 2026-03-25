from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.repositories.session_repository import SessionRepository
from bot.database.repositories.user_repository import UserRepository
from bot.enums import SessionStatus, UserStatus
from bot.models.work_pause import WorkPauseEntity
from bot.models.work_session import WorkSessionEntity


class TrackingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session=session)
        self._session_repo = SessionRepository(session=session)

    async def start_work(self, user_id: int) -> WorkSessionEntity:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        if user.status == UserStatus.WORKING:
            raise ValueError("Already working")
        if user.status == UserStatus.PAUSED:
            raise ValueError("Currently paused — resume or stop first")

        work_session = await self._session_repo.create_session(user_id)
        await self._user_repo.update_status(user_id, UserStatus.WORKING)
        return work_session

    async def pause_work(self, user_id: int) -> WorkPauseEntity:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        if user.status != UserStatus.WORKING:
            raise ValueError("Not currently working")

        active_session = await self._session_repo.get_active_session(user_id)
        if not active_session:
            raise ValueError("No active session found")

        pause = await self._session_repo.create_pause(active_session.id)
        await self._session_repo.update_session_status(
            active_session.id, SessionStatus.PAUSED
        )
        await self._user_repo.update_status(user_id, UserStatus.PAUSED)
        return pause

    async def resume_work(self, user_id: int) -> WorkSessionEntity:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        if user.status != UserStatus.PAUSED:
            raise ValueError("Not currently paused")

        active_session = await self._session_repo.get_active_session(user_id)
        if not active_session:
            raise ValueError("No active session found")

        open_pause = await self._session_repo.get_open_pause(active_session.id)
        if open_pause:
            await self._session_repo.end_pause(open_pause.id)

        await self._session_repo.update_session_status(
            active_session.id, SessionStatus.ACTIVE
        )
        await self._user_repo.update_status(user_id, UserStatus.WORKING)
        return active_session

    async def stop_work(self, user_id: int) -> dict:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        if user.status == UserStatus.OFFLINE:
            raise ValueError("Not currently working")

        active_session = await self._session_repo.get_active_session(user_id)
        if not active_session:
            raise ValueError("No active session found")

        # Close open pause if paused
        if user.status == UserStatus.PAUSED:
            open_pause = await self._session_repo.get_open_pause(active_session.id)
            if open_pause:
                await self._session_repo.end_pause(open_pause.id)

        await self._session_repo.end_session(active_session.id)
        await self._user_repo.update_status(user_id, UserStatus.OFFLINE)

        # Recalculate after closing
        now = datetime.now(timezone.utc)
        session_duration = now - active_session.started_at
        pause_duration = await self._calculate_pause_duration(active_session.id)
        work_duration = session_duration - pause_duration

        return {
            "session_duration": session_duration,
            "pause_duration": pause_duration,
            "work_duration": work_duration,
        }

    async def get_user_status_info(self, user_id: int) -> dict:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        now = datetime.now(timezone.utc)
        active_session = await self._session_repo.get_active_session(user_id)

        current_session_duration = timedelta()
        current_pause_duration = timedelta()
        current_work_duration = timedelta()

        if active_session:
            current_session_duration = now - active_session.started_at
            current_pause_duration = await self._calculate_pause_duration(
                active_session.id, now=now
            )
            current_work_duration = current_session_duration - current_pause_duration

        today_total = await self.get_today_total_work_time(user_id)

        return {
            "status": user.status,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "today_total_work_time": today_total,
            "current_session_duration": current_work_duration,
            "current_pause_duration": current_pause_duration,
        }

    async def get_today_total_work_time(self, user_id: int) -> timedelta:
        sessions = await self._session_repo.get_today_sessions(user_id)
        total = timedelta()
        now = datetime.now(timezone.utc)

        for sess in sessions:
            end = sess.ended_at or now
            elapsed = end - sess.started_at
            pause_dur = timedelta()
            for pause in sess.pauses:
                p_end = pause.resumed_at or now
                pause_dur += p_end - pause.paused_at
            total += elapsed - pause_dur

        return total

    async def _calculate_pause_duration(
        self, session_id: int, now: datetime | None = None
    ) -> timedelta:
        if now is None:
            now = datetime.now(timezone.utc)
        pauses = await self._session_repo.get_pauses_for_session(session_id)
        total = timedelta()
        for pause in pauses:
            p_end = pause.resumed_at or now
            total += p_end - pause.paused_at
        return total
