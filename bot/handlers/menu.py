import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import settings
from bot.enums import UserStatus
from bot.keyboards.admin import get_admin_keyboard
from bot.keyboards.menu import (
    get_main_menu_keyboard,
    get_start_keyboard,
)
from bot.keyboards.status import get_status_keyboard
from bot.services.team_service import TeamService
from bot.services.tracking_service import TrackingService
from bot.services.workspace_service import WorkspaceService
from bot.utils.deps import get_session, require_admin, require_auth
from bot.utils.time_format import format_duration, format_time

logger = logging.getLogger(__name__)


@require_auth
async def handle_team_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    workspace_id = context.user_data["db_workspace_id"]

    async with get_session() as session:
        service = TeamService(session)
        members = await service.get_all_members_with_status(workspace_id)

    if not members:
        await update.message.reply_text("👥 Team Members\n\nNo team members yet.")
        return

    lines = ["👥 Team Members"]
    for m in members:
        lines.append("")
        lines.append(f"{m['status_emoji']} {m['display_name']}")
        lines.append(f"    Status: {m['status'].value.capitalize()}")
        if m["first_start_today"]:
            lines.append(f"    First start: {format_time(m['first_start_today'])}")
        if m["status"] != UserStatus.OFFLINE and m["current_session_start"]:
            lines.append(f"    Session start: {format_time(m['current_session_start'])}")
            lines.append(f"    Session work: {format_duration(m['current_session_work'])}")
        if m["last_end_today"]:
            lines.append(f"    Last stop: {format_time(m['last_end_today'])}")
        lines.append(f"    Today total: {format_duration(m['today_work_time'])}")
        lines.append(f"    Paused total: {format_duration(m['today_pause_time'])}")
        lines.append(f"    Sessions: {m['total_sessions_today']}")

    await update.message.reply_text("\n".join(lines))


@require_auth
async def handle_my_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = context.user_data["db_user_id"]

    async with get_session() as session:
        service = TrackingService(session)
        info = await service.get_user_status_info(user_id)

    status_emoji = {"working": "🟢", "paused": "🟡", "offline": "⚫"}.get(
        info["status"].value, "⚫"
    )

    text = (
        f"📊 My Status\n\n"
        f"👤 {info['first_name']} {info['last_name']}\n"
        f"Status: {status_emoji} {info['status'].value.capitalize()}\n\n"
        f"📅 Today's work time: {format_duration(info['today_total_work_time'])}\n"
    )

    if info["status"] != UserStatus.OFFLINE:
        text += (
            f"⏱ Current session: {format_duration(info['current_session_duration'])}\n"
            f"⏸ Paused: {format_duration(info['current_pause_duration'])}\n"
        )

    await update.message.reply_text(text)


@require_auth
async def handle_change_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_status = context.user_data.get("db_user_status", UserStatus.OFFLINE)
    keyboard = get_status_keyboard(user_status)
    await update.message.reply_text("🔄 Change Status", reply_markup=keyboard)


@require_admin
async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = get_admin_keyboard()
    await update.message.reply_text("⚙️ Admin Panel", reply_markup=keyboard)


@require_auth
async def handle_leave_workspace(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = context.user_data["db_user_id"]

    try:
        async with get_session() as session:
            ws_service = WorkspaceService(session)
            ws_name = await ws_service.leave_workspace(user_id)

        await update.message.reply_text(
            f"🚪 You left workspace \"{ws_name}\".\n\nUse /start to join or create a new one.",
            reply_markup=get_start_keyboard(),
        )
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")


@require_auth
async def handle_delete_workspace(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    workspace_id = context.user_data["db_workspace_id"]
    telegram_id = context.user_data["db_user_telegram_id"]

    try:
        async with get_session() as session:
            ws_service = WorkspaceService(session)
            ws_name = await ws_service.delete_workspace(workspace_id, telegram_id)

        await update.message.reply_text(
            f"🗑 Workspace \"{ws_name}\" deleted.\n\nUse /start to create a new one.",
            reply_markup=get_start_keyboard(),
        )
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
