import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.enums import UserStatus
from bot.keyboards.status import get_status_keyboard
from bot.services.auth_service import AuthService
from bot.services.tracking_service import TrackingService
from bot.utils.deps import get_session, require_auth
from bot.utils.notify import notify_admin, schedule_revert
from bot.utils.time_format import format_duration

logger = logging.getLogger(__name__)


async def _get_user_display_name(user_id: int) -> str:
    async with get_session() as session:
        auth = AuthService(session)
        user = await auth.get_user_by_id(user_id)
        if user:
            return f"{user.first_name} {user.last_name}"
    return "Unknown"


@require_auth
async def start_work(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = context.user_data["db_user_id"]
    user_status = context.user_data.get("db_user_status", UserStatus.OFFLINE)

    try:
        async with get_session() as session:
            service = TrackingService(session)
            if user_status == UserStatus.PAUSED:
                await service.resume_work(user_id)
                text = "▶️ Work resumed!"
                action = "resumed work"
            else:
                await service.start_work(user_id)
                text = "▶️ Work started! Good luck!"
                action = "started work"

        keyboard = get_status_keyboard(UserStatus.WORKING)
        await query.edit_message_text(text, reply_markup=keyboard)

        name = await _get_user_display_name(user_id)
        await notify_admin(context.bot, f"📢 {name} {action}")

    except ValueError as e:
        keyboard = get_status_keyboard(user_status)
        msg = await query.edit_message_text(f"⚠️ {e}", reply_markup=keyboard)
        schedule_revert(msg, context, "🔄 Change Status", keyboard)


@require_auth
async def pause_work(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = context.user_data["db_user_id"]
    user_status = context.user_data.get("db_user_status", UserStatus.OFFLINE)

    try:
        async with get_session() as session:
            service = TrackingService(session)
            await service.pause_work(user_id)

        keyboard = get_status_keyboard(UserStatus.PAUSED)
        await query.edit_message_text("⏸ Work paused.", reply_markup=keyboard)

        name = await _get_user_display_name(user_id)
        await notify_admin(context.bot, f"📢 {name} paused work")

    except ValueError as e:
        keyboard = get_status_keyboard(user_status)
        msg = await query.edit_message_text(f"⚠️ {e}", reply_markup=keyboard)
        schedule_revert(msg, context, "🔄 Change Status", keyboard)


@require_auth
async def stop_work(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = context.user_data["db_user_id"]
    user_status = context.user_data.get("db_user_status", UserStatus.OFFLINE)

    try:
        async with get_session() as session:
            service = TrackingService(session)
            summary = await service.stop_work(user_id)

        text = (
            "⏹ Work stopped!\n\n"
            f"📊 Session summary:\n"
            f"  Total time: {format_duration(summary['session_duration'])}\n"
            f"  Work time: {format_duration(summary['work_duration'])}\n"
            f"  Paused: {format_duration(summary['pause_duration'])}\n"
        )

        # Remove inline keyboard, just show summary text
        await query.edit_message_text(text)

        name = await _get_user_display_name(user_id)
        await notify_admin(
            context.bot,
            f"📢 {name} stopped work\n"
            f"   Work: {format_duration(summary['work_duration'])}\n"
            f"   Paused: {format_duration(summary['pause_duration'])}",
        )

    except ValueError as e:
        keyboard = get_status_keyboard(user_status)
        msg = await query.edit_message_text(f"⚠️ {e}", reply_markup=keyboard)
        schedule_revert(msg, context, "🔄 Change Status", keyboard)
