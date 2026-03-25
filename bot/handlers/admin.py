import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.enums import UserRole, UserStatus
from bot.keyboards.admin import get_admin_keyboard
from bot.services.auth_service import AuthService
from bot.services.team_service import TeamService
from bot.utils.deps import get_session, require_admin
from bot.utils.time_format import format_duration, format_time

logger = logging.getLogger(__name__)

ENTER_FIRST_NAME = 0
ENTER_LAST_NAME = 1
ENTER_ROLE = 2

ROLE_LABELS = {
    "user": "👤 User",
    "admin": "👑 Admin",
}


async def generate_key_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    async with get_session() as session:
        auth = AuthService(session)
        user = await auth.get_user_by_telegram_id(query.from_user.id)
        if not user or not user.is_admin:
            await query.answer("Admin access required", show_alert=True)
            return ConversationHandler.END
        context.user_data["db_user_id"] = user.id

    await query.edit_message_text(
        "🔑 Generate Invite Key\n\nEnter the first name:"
    )
    return ENTER_FIRST_NAME


async def receive_first_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data["invite_first_name"] = update.message.text.strip()
    await update.message.reply_text("Enter the last name:")
    return ENTER_LAST_NAME


async def receive_last_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data["invite_last_name"] = update.message.text.strip()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 User", callback_data="role:user")],
        [InlineKeyboardButton("👑 Admin", callback_data="role:admin")],
    ])
    await update.message.reply_text("Select role:", reply_markup=keyboard)
    return ENTER_ROLE


async def receive_role(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    role = query.data.split(":")[1]  # "user" or "admin"
    first_name = context.user_data.get("invite_first_name", "")
    last_name = context.user_data.get("invite_last_name", "")
    user_id = context.user_data.get("db_user_id")

    try:
        async with get_session() as session:
            auth = AuthService(session)
            invite = await auth.generate_invite_code(
                first_name=first_name,
                last_name=last_name,
                created_by_user_id=user_id,
                role=role,
            )

        role_label = ROLE_LABELS.get(role, role)
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("◀️ Back to Admin", callback_data="admin:menu")]]
        )
        await query.edit_message_text(
            f"✅ Invite code generated!\n\n"
            f"👤 For: {first_name} {last_name}\n"
            f"🔑 Code: `{invite.code}`\n"
            f"Role: {role_label}\n\n"
            f"Share this code with the user.",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    except Exception as e:
        logger.exception("Error generating invite code")
        await query.edit_message_text(f"❌ Error: {e}")

    context.user_data.pop("invite_first_name", None)
    context.user_data.pop("invite_last_name", None)
    return ConversationHandler.END


async def cancel_generate(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data.pop("invite_first_name", None)
    context.user_data.pop("invite_last_name", None)
    await update.message.reply_text("Key generation cancelled.")
    return ConversationHandler.END


@require_admin
async def admin_panel_inline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    keyboard = get_admin_keyboard()
    await query.edit_message_text("⚙️ Admin Panel", reply_markup=keyboard)


@require_admin
async def team_management(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    requester_role = context.user_data.get("db_user_role", UserRole.USER)
    await _show_team_management(query, requester_role)


async def _show_team_management(query, requester_role: UserRole = UserRole.ADMIN) -> None:
    async with get_session() as session:
        service = TeamService(session)
        data = await service.get_team_management_data()

    if not data:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("◀️ Back to Admin", callback_data="admin:menu")]]
        )
        await query.edit_message_text(
            "📋 Team Management\n\nNo team members yet.", reply_markup=keyboard
        )
        return

    role_badge = {
        UserRole.SUPERADMIN: " [SA]",
        UserRole.ADMIN: " [A]",
        UserRole.USER: "",
    }

    lines = ["📋 Team Management"]
    buttons = []

    for m in data:
        user = m["user"]
        badge = role_badge.get(user.role, "")
        lines.append("")
        lines.append(f"{m['status_emoji']} {m['display_name']}{badge}")
        lines.append(f"    Status: {m['status'].value.capitalize()}")
        if m["first_start_today"]:
            lines.append(f"    First start: {format_time(m['first_start_today'])}")
        if m["status"] != UserStatus.OFFLINE and m["current_session_start"]:
            lines.append(f"    Session start: {format_time(m['current_session_start'])}")
            lines.append(f"    Session work: {format_duration(m['current_session_work'])}")
        if m["last_end_today"]:
            lines.append(f"    Last stop: {format_time(m['last_end_today'])}")
        lines.append(f"    Today total: {format_duration(m['today_work_time'])}")
        lines.append(f"    Paused: {format_duration(m['today_pause_time'])}")
        lines.append(f"    Sessions: {m['total_sessions_today']}")

        # Delete button logic:
        # - superadmin can delete anyone except themselves
        # - admin can only delete regular users
        can_delete = False
        if user.is_superadmin:
            can_delete = False
        elif user.is_admin and requester_role == UserRole.SUPERADMIN:
            can_delete = True
        elif not user.is_admin:
            can_delete = True

        if can_delete:
            buttons.append(
                [InlineKeyboardButton(
                    f"🗑 Delete {m['display_name']}",
                    callback_data=f"admin:delete:{user.id}",
                )]
            )

    buttons.append(
        [InlineKeyboardButton("◀️ Back to Admin", callback_data="admin:menu")]
    )

    text = "\n".join(lines)
    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(text, reply_markup=keyboard)


@require_admin
async def confirm_delete_user(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split(":")[2])

    async with get_session() as session:
        auth = AuthService(session)
        user = await auth.get_user_by_id(user_id)
        if not user:
            await query.answer("User not found", show_alert=True)
            return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Yes, delete", callback_data=f"admin:confirm_del:{user_id}"
            ),
            InlineKeyboardButton(
                "❌ Cancel", callback_data="admin:team_management"
            ),
        ]
    ])
    await query.edit_message_text(
        f"⚠️ Delete {user.first_name} {user.last_name}?\n\n"
        f"This will remove the user and all their work history.",
        reply_markup=keyboard,
    )


@require_admin
async def execute_delete_user(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split(":")[2])
    requester_role = context.user_data.get("db_user_role", UserRole.USER)

    try:
        async with get_session() as session:
            auth = AuthService(session)
            name = await auth.delete_user(user_id, requester_role=requester_role)

        await query.answer(f"✅ {name} deleted", show_alert=True)
    except ValueError as e:
        await query.answer(f"❌ {e}", show_alert=True)

    await _show_team_management(query, requester_role)


generate_key_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(generate_key_start, pattern="^admin:generate_key$")
    ],
    states={
        ENTER_FIRST_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_first_name)
        ],
        ENTER_LAST_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_last_name)
        ],
        ENTER_ROLE: [
            CallbackQueryHandler(receive_role, pattern="^role:(user|admin)$")
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_generate)],
    per_message=False,
)
