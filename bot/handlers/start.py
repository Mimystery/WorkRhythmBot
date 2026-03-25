import logging

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.config import settings
from bot.keyboards.menu import get_main_menu_keyboard
from bot.services.auth_service import AuthService
from bot.utils.deps import get_session

logger = logging.getLogger(__name__)

AWAITING_CODE = 0


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id

    async with get_session() as session:
        auth = AuthService(session)

        # Check if already registered
        user = await auth.get_user_by_telegram_id(telegram_id)
        if user:
            keyboard = get_main_menu_keyboard(is_admin=user.is_admin)
            await update.message.reply_text(
                f"Welcome back, {user.first_name}! 📋",
                reply_markup=keyboard,
            )
            return ConversationHandler.END

        # Admin bootstrap: first user with admin ID gets auto-registered
        user_count = await auth.get_user_count()
        if user_count == 0 and telegram_id == settings.admin_id:
            tg_user = update.effective_user
            user = await auth.register_admin_bootstrap(
                telegram_id=telegram_id,
                first_name=tg_user.first_name or "Admin",
                last_name=tg_user.last_name or "",
            )
            keyboard = get_main_menu_keyboard(is_admin=True)
            await update.message.reply_text(
                f"Welcome, {user.first_name}! You've been registered as admin. 👑",
                reply_markup=keyboard,
            )
            return ConversationHandler.END

    # Not registered — ask for invite code
    await update.message.reply_text(
        "Welcome! 👋\n\nPlease enter your invite code to register:"
    )
    return AWAITING_CODE


async def receive_invite_code(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    code = update.message.text.strip()
    telegram_id = update.effective_user.id

    try:
        async with get_session() as session:
            auth = AuthService(session)

            # Check not already registered (race condition guard)
            existing = await auth.get_user_by_telegram_id(telegram_id)
            if existing:
                keyboard = get_main_menu_keyboard(is_admin=existing.is_admin)
                await update.message.reply_text(
                    "You're already registered!", reply_markup=keyboard
                )
                return ConversationHandler.END

            user = await auth.register_user(
                telegram_id=telegram_id,
                code=code,
            )

        keyboard = get_main_menu_keyboard(is_admin=user.is_admin)
        await update.message.reply_text(
            f"Welcome, {user.first_name} {user.last_name}! ✅\n\n"
            "You've been successfully registered.",
            reply_markup=keyboard,
        )
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text(
            "❌ Invalid or already used invite code.\n\nPlease try again:"
        )
        return AWAITING_CODE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Registration cancelled.")
    return ConversationHandler.END


registration_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start_command)],
    states={
        AWAITING_CODE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_invite_code)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
