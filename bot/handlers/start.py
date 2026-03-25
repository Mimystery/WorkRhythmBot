import logging

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.keyboards.menu import (
    BTN_CREATE_WORKSPACE,
    BTN_JOIN_WORKSPACE,
    REMOVE_KEYBOARD,
    get_main_menu_keyboard,
    get_start_keyboard,
)
from bot.services.auth_service import AuthService
from bot.services.workspace_service import WorkspaceService
from bot.utils.deps import get_session

logger = logging.getLogger(__name__)

CHOOSE_ACTION = 0
ENTER_WS_NAME = 1
ENTER_INVITE_CODE = 2


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tg = update.effective_user

    async with get_session() as session:
        auth = AuthService(session)
        user = await auth.get_user_by_telegram_id(tg.id)

        if user and user.workspace_id and user.workspace:
            ws = user.workspace
            is_owner = ws.owner_telegram_id == tg.id
            keyboard = get_main_menu_keyboard(
                is_admin=user.is_admin, is_owner=is_owner
            )
            await update.message.reply_text(
                f"Welcome back, {user.first_name}!\n"
                f"Workspace: {ws.name}",
                reply_markup=keyboard,
            )
            return ConversationHandler.END

    # Not in a workspace
    await update.message.reply_text(
        "Welcome! 👋\n\nChoose an option:",
        reply_markup=get_start_keyboard(),
    )
    return CHOOSE_ACTION


async def choose_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🏢 Enter a name for your workspace:",
        reply_markup=REMOVE_KEYBOARD,
    )
    return ENTER_WS_NAME


async def choose_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🔑 Enter your invite code:",
        reply_markup=REMOVE_KEYBOARD,
    )
    return ENTER_INVITE_CODE


async def receive_ws_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ws_name = update.message.text.strip()
    tg = update.effective_user

    if not ws_name:
        await update.message.reply_text("Name cannot be empty. Try again:")
        return ENTER_WS_NAME

    try:
        async with get_session() as session:
            ws_service = WorkspaceService(session)
            workspace = await ws_service.create_workspace(
                name=ws_name,
                owner_telegram_id=tg.id,
                first_name=tg.first_name or "User",
                last_name=tg.last_name or "",
            )

        keyboard = get_main_menu_keyboard(is_admin=True, is_owner=True)
        await update.message.reply_text(
            f"✅ Workspace \"{workspace.name}\" created!\n\n"
            f"You're the owner. Generate invite codes to add members.",
            reply_markup=keyboard,
        )
        return ConversationHandler.END

    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return ConversationHandler.END


async def receive_invite_code(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    code = update.message.text.strip()
    tg = update.effective_user

    try:
        async with get_session() as session:
            ws_service = WorkspaceService(session)
            user, workspace = await ws_service.join_workspace(
                telegram_id=tg.id, code=code
            )

        is_owner = workspace.owner_telegram_id == tg.id
        keyboard = get_main_menu_keyboard(
            is_admin=user.is_admin, is_owner=is_owner
        )
        await update.message.reply_text(
            f"✅ Joined workspace \"{workspace.name}\"!\n\n"
            f"Welcome, {user.first_name}!",
            reply_markup=keyboard,
        )
        return ConversationHandler.END

    except ValueError as e:
        await update.message.reply_text(
            f"❌ {e}\n\nTry again or /cancel:"
        )
        return ENTER_INVITE_CODE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Cancelled.",
        reply_markup=get_start_keyboard(),
    )
    return ConversationHandler.END


registration_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start_command)],
    states={
        CHOOSE_ACTION: [
            MessageHandler(filters.Text([BTN_CREATE_WORKSPACE]), choose_create),
            MessageHandler(filters.Text([BTN_JOIN_WORKSPACE]), choose_join),
        ],
        ENTER_WS_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ws_name)
        ],
        ENTER_INVITE_CODE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_invite_code)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
