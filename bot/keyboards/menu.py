from telegram import KeyboardButton, ReplyKeyboardMarkup

# Button text constants — used for both keyboard and message filters
BTN_TEAM = "👥 Team Members"
BTN_MY_STATUS = "📊 My Status"
BTN_CHANGE_STATUS = "🔄 Change Status"
BTN_ADMIN = "⚙️ Admin Panel"


def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(BTN_TEAM)],
        [KeyboardButton(BTN_MY_STATUS)],
        [KeyboardButton(BTN_CHANGE_STATUS)],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
