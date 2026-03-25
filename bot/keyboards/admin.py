from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_admin_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔑 Generate Key", callback_data="admin:generate_key")],
        [InlineKeyboardButton("📋 Team Management", callback_data="admin:team_management")],
        [InlineKeyboardButton("◀️ Back", callback_data="admin:back")],
    ]
    return InlineKeyboardMarkup(keyboard)
