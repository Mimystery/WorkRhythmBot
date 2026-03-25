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
    """Load user from DB into context.user_data. Returns True if found and in workspace."""
    telegram_id = update.effective_user.id
    async with get_session() as session:
        user = await UserRepository(session=session).get_by_telegram_id(telegram_id)
        if not user or not user.workspace_id:
            return False
        context.user_data["db_user_id"] = user.id
        context.user_data["db_user_is_admin"] = user.is_admin
        context.user_data["db_user_is_superadmin"] = user.is_superadmin
        context.user_data["db_user_role"] = user.role
        context.user_data["db_user_status"] = user.status
        context.user_data["db_workspace_id"] = user.workspace_id
        context.user_data["db_user_telegram_id"] = user.telegram_id
    return True


def _deny(msg: str):
    async def _send(update: Update):
        if update.callback_query:
            await update.callback_query.answer(msg, show_alert=True)
        elif update.message:
            await update.message.reply_text(msg)
    return _send


def require_auth(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await _load_user(update, context):
            await _deny("Please use /start first")(update)
            return
        return await func(update, context)
    return wrapper


def require_admin(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await _load_user(update, context):
            await _deny("Please use /start first")(update)
            return
        if not context.user_data.get("db_user_is_admin"):
            await _deny("Admin access required")(update)
            return
        return await func(update, context)
    return wrapper
