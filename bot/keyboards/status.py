from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.enums import UserStatus


def get_status_keyboard(current_status: UserStatus) -> InlineKeyboardMarkup:
    keyboard = []

    if current_status == UserStatus.OFFLINE:
        keyboard.append(
            [InlineKeyboardButton("▶️ Start Work", callback_data="status:start")]
        )
    elif current_status == UserStatus.WORKING:
        keyboard.append(
            [InlineKeyboardButton("⏸ Pause Work", callback_data="status:pause")]
        )
        keyboard.append(
            [InlineKeyboardButton("⏹ Stop Work", callback_data="status:stop")]
        )
    elif current_status == UserStatus.PAUSED:
        keyboard.append(
            [InlineKeyboardButton("▶️ Resume Work", callback_data="status:start")]
        )
        keyboard.append(
            [InlineKeyboardButton("⏹ Stop Work", callback_data="status:stop")]
        )

    keyboard.append(
        [InlineKeyboardButton("◀️ Back", callback_data="status:back")]
    )
    return InlineKeyboardMarkup(keyboard)
