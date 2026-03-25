import asyncio
import logging

from telegram import Bot, InlineKeyboardMarkup, Message

from bot.config import settings

logger = logging.getLogger(__name__)

REVERT_DELAY = 3  # seconds


async def _revert_message(
    message: Message, text: str, keyboard: InlineKeyboardMarkup, delay: int
) -> None:
    await asyncio.sleep(delay)
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except Exception:
        pass


def schedule_revert(
    message: Message,
    context,
    text: str,
    keyboard: InlineKeyboardMarkup,
    delay: int = REVERT_DELAY,
) -> None:
    """After delay, replace message content with text + keyboard."""
    context.application.create_task(
        _revert_message(message, text, keyboard, delay)
    )


async def notify_admin(bot: Bot, text: str) -> None:
    """Send a notification to the admin."""
    try:
        await bot.send_message(chat_id=settings.admin_id, text=text)
    except Exception:
        logger.exception("Failed to notify admin")
