import logging

from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters
from telegram.request import HTTPXRequest

from bot.config import settings
from bot.handlers.admin import (
    admin_panel_inline,
    confirm_delete_user,
    execute_delete_user,
    generate_key_handler,
    team_management,
)
from bot.handlers.menu import (
    handle_admin_panel,
    handle_change_status,
    handle_delete_workspace,
    handle_leave_workspace,
    handle_my_status,
    handle_team_members,
)
from bot.handlers.start import registration_handler
from bot.handlers.status import pause_work, start_work, stop_work
from bot.keyboards.menu import (
    BTN_ADMIN,
    BTN_CHANGE_STATUS,
    BTN_DELETE_WORKSPACE,
    BTN_LEAVE_WORKSPACE,
    BTN_MY_STATUS,
    BTN_TEAM,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def error_handler(update, context) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    if update and update.callback_query:
        try:
            await update.callback_query.answer(
                "❌ An error occurred. Try again.", show_alert=True
            )
        except Exception:
            pass
    elif update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An unexpected error occurred. Please try again later."
        )


def main() -> None:
    request = HTTPXRequest(connect_timeout=20.0, read_timeout=20.0)
    app = (
        Application.builder()
        .token(settings.bot_token)
        .request(request)
        .build()
    )

    # ConversationHandlers (take priority by order)
    app.add_handler(registration_handler)
    app.add_handler(generate_key_handler)

    # Main menu — ReplyKeyboard text buttons
    app.add_handler(MessageHandler(filters.Text([BTN_TEAM]), handle_team_members))
    app.add_handler(MessageHandler(filters.Text([BTN_MY_STATUS]), handle_my_status))
    app.add_handler(MessageHandler(filters.Text([BTN_CHANGE_STATUS]), handle_change_status))
    app.add_handler(MessageHandler(filters.Text([BTN_ADMIN]), handle_admin_panel))
    app.add_handler(MessageHandler(filters.Text([BTN_LEAVE_WORKSPACE]), handle_leave_workspace))
    app.add_handler(MessageHandler(filters.Text([BTN_DELETE_WORKSPACE]), handle_delete_workspace))

    # Status actions — InlineKeyboard callbacks
    app.add_handler(CallbackQueryHandler(start_work, pattern="^status:start$"))
    app.add_handler(CallbackQueryHandler(pause_work, pattern="^status:pause$"))
    app.add_handler(CallbackQueryHandler(stop_work, pattern="^status:stop$"))

    # Admin inline sub-menu callbacks
    app.add_handler(CallbackQueryHandler(admin_panel_inline, pattern="^admin:menu$"))
    app.add_handler(CallbackQueryHandler(team_management, pattern="^admin:team_management$"))
    app.add_handler(CallbackQueryHandler(confirm_delete_user, pattern=r"^admin:delete:\d+$"))
    app.add_handler(CallbackQueryHandler(execute_delete_user, pattern=r"^admin:confirm_del:\d+$"))

    # Global error handler
    app.add_error_handler(error_handler)

    logger.info("Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
