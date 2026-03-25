import logging
from contextlib import asynccontextmanager
from functools import wraps
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Update
from telegram.ext import ContextTypes

from bot.database.engine import session_factory
from bot.database.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _load_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Load user from DB into context.user_data. Returns True if found."""
    telegram_id = update.effective_user.id
    async with get_session() as session:
        user = await UserRepository(session=session).get_by_telegram_id(telegram_id)
        if not user:
            return False
        context.user_data["db_user_id"] = user.id
        context.user_data["db_user_is_admin"] = user.is_admin
        context.user_data["db_user_is_superadmin"] = user.is_superadmin
        context.user_data["db_user_role"] = user.role
        context.user_data["db_user_status"] = user.status
    return True


def require_auth(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await _load_user(update, context):
            # Works for both callback queries and messages
            if update.callback_query:
                await update.callback_query.answer(
                    "Please register first using /start", show_alert=True
                )
            elif update.message:
                await update.message.reply_text(
                    "Please register first using /start"
                )
            return
        return await func(update, context)

    return wrapper


def require_admin(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await _load_user(update, context):
            if update.callback_query:
                await update.callback_query.answer(
                    "Please register first using /start", show_alert=True
                )
            elif update.message:
                await update.message.reply_text(
                    "Please register first using /start"
                )
            return
        if not context.user_data.get("db_user_is_admin"):
            if update.callback_query:
                await update.callback_query.answer(
                    "Admin access required", show_alert=True
                )
            elif update.message:
                await update.message.reply_text("Admin access required")
            return
        return await func(update, context)

    return wrapper
