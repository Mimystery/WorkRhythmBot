from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.repositories.session_repository import SessionRepository
from bot.database.repositories.user_repository import UserRepository
from bot.enums import UserStatus


STATUS_EMOJI = {
    UserStatus.WORKING: "🟢",
    UserStatus.PAUSED: "🟡",
    UserStatus.OFFLINE: "⚫",
}

STATUS_ORDER = {
    UserStatus.WORKING: 0,
    UserStatus.PAUSED: 1,
    UserStatus.OFFLINE: 2,
}


class TeamService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session=session)
        self._session_repo = SessionRepository(session=session)

    async def get_all_members_with_status(self) -> list[dict]:
        users = await self._user_repo.get_all()
        now = datetime.now(timezone.utc)
        result = []

        for user in users:
            sessions_today = await self._session_repo.get_today_sessions(user.id)
            active_session = await self._session_repo.get_active_session(user.id)

            # Today's total work time
            today_work = timedelta()
            today_pause = timedelta()
            first_start = None
            last_end = None

            for sess in sessions_today:
                end = sess.ended_at or now
                elapsed = end - sess.started_at
                p_dur = timedelta()
                for pause in sess.pauses:
                    p_end = pause.resumed_at or now
                    p_dur += p_end - pause.paused_at
                today_work += elapsed - p_dur
                today_pause += p_dur

                if first_start is None or sess.started_at < first_start:
                    first_start = sess.started_at
                if sess.ended_at:
                    if last_end is None or sess.ended_at > last_end:
                        last_end = sess.ended_at

            # Current session info
            current_session_work = timedelta()
            current_session_start = None
            if active_session:
                current_session_start = active_session.started_at
                c_elapsed = now - active_session.started_at
                c_pause = timedelta()
                for pause in active_session.pauses:
                    p_end = pause.resumed_at or now
                    c_pause += p_end - pause.paused_at
                current_session_work = c_elapsed - c_pause

            result.append(
                {
                    "user": user,
                    "status_emoji": STATUS_EMOJI.get(user.status, "⚫"),
                    "display_name": f"{user.first_name} {user.last_name}",
                    "status": user.status,
                    "today_work_time": today_work,
                    "today_pause_time": today_pause,
                    "total_sessions_today": len(sessions_today),
                    "first_start_today": first_start,
                    "last_end_today": last_end,
                    "current_session_start": current_session_start,
                    "current_session_work": current_session_work,
                    "is_active": active_session is not None,
                }
            )

        result.sort(key=lambda x: STATUS_ORDER.get(x["user"].status, 99))
        return result

    async def get_team_management_data(self) -> list[dict]:
        return await self.get_all_members_with_status()
