from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.repositories.invite_repository import InviteRepository
from bot.database.repositories.user_repository import UserRepository
from bot.database.repositories.workspace_repository import WorkspaceRepository
from bot.enums import UserRole
from bot.models.invite_code import InviteCodeEntity
from bot.models.work_pause import WorkPauseEntity
from bot.models.work_session import WorkSessionEntity
from bot.models.workspace import WorkspaceEntity


class WorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._ws_repo = WorkspaceRepository(session=session)
        self._user_repo = UserRepository(session=session)
        self._invite_repo = InviteRepository(session=session)

    async def create_workspace(
        self, name: str, owner_telegram_id: int, first_name: str, last_name: str
    ) -> WorkspaceEntity:
        # Check user doesn't already own a workspace
        existing = await self._ws_repo.get_by_owner(owner_telegram_id)
        if existing:
            raise ValueError("You already own a workspace")

        workspace = await self._ws_repo.create(
            name=name, owner_telegram_id=owner_telegram_id
        )

        # Create or update user record
        user = await self._user_repo.get_by_telegram_id(owner_telegram_id)
        if user:
            await self._user_repo.update_workspace(
                user.id, workspace.id, role=UserRole.SUPERADMIN
            )
        else:
            await self._user_repo.create(
                telegram_id=owner_telegram_id,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.SUPERADMIN,
                workspace_id=workspace.id,
            )

        return workspace

    async def join_workspace(self, telegram_id: int, code: str) -> tuple:
        """Returns (user, workspace) tuple."""
        invite = await self._invite_repo.get_unused_by_code(code)
        if not invite:
            raise ValueError("Invalid or already used invite code")

        role = UserRole(invite.role) if invite.role else UserRole.USER

        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if user and user.workspace_id:
            raise ValueError("You're already in a workspace. Leave first.")

        if user:
            await self._user_repo.update_workspace(user.id, invite.workspace_id, role)
            # Refresh
            user = await self._user_repo.get_by_id(user.id)
        else:
            user = await self._user_repo.create(
                telegram_id=telegram_id,
                first_name=invite.first_name,
                last_name=invite.last_name,
                role=role,
                workspace_id=invite.workspace_id,
            )

        await self._invite_repo.mark_as_used(invite.id, used_by=user.id)
        workspace = await self._ws_repo.get_by_id(invite.workspace_id)
        return user, workspace

    async def leave_workspace(self, user_id: int) -> str:
        """User leaves workspace. Returns workspace name."""
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.workspace_id:
            raise ValueError("Not in a workspace")

        workspace = await self._ws_repo.get_by_id(user.workspace_id)
        if workspace and workspace.owner_telegram_id == user.telegram_id:
            raise ValueError("Owner cannot leave. Delete the workspace instead.")

        ws_name = workspace.name if workspace else "Unknown"

        # Clean up active sessions
        await self._cleanup_user_data(user_id)
        await self._user_repo.update_workspace(user_id, None, UserRole.USER)
        return ws_name

    async def delete_workspace(self, workspace_id: int, requester_telegram_id: int) -> str:
        """Delete workspace and all related data. Returns workspace name."""
        from bot.config import settings

        workspace = await self._ws_repo.get_by_id(workspace_id)
        if not workspace:
            raise ValueError("Workspace not found")

        is_global_admin = requester_telegram_id == settings.admin_id
        is_owner = workspace.owner_telegram_id == requester_telegram_id

        if not is_owner and not is_global_admin:
            raise ValueError("Only workspace owner or global admin can delete")

        ws_name = workspace.name

        # Get all users in workspace
        users = await self._user_repo.get_all_in_workspace(workspace_id)
        for u in users:
            await self._cleanup_user_data(u.id)

        # Clear users from workspace
        await self._user_repo.clear_workspace(workspace_id)
        # Delete invite codes
        await self._invite_repo.delete_by_workspace(workspace_id)
        # Delete workspace
        await self._ws_repo.delete_by_id(workspace_id)

        return ws_name

    async def _cleanup_user_data(self, user_id: int) -> None:
        """Delete work sessions and pauses for a user."""
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
