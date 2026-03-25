from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

# Button text constants
BTN_TEAM = "👥 Team Members"
BTN_MY_STATUS = "📊 My Status"
BTN_CHANGE_STATUS = "🔄 Change Status"
BTN_ADMIN = "⚙️ Admin Panel"
BTN_LEAVE_WORKSPACE = "🚪 Leave Workspace"
BTN_DELETE_WORKSPACE = "🗑 Delete Workspace"

# Start flow buttons
BTN_CREATE_WORKSPACE = "🏢 Create Workspace"
BTN_JOIN_WORKSPACE = "🔑 Join Workspace"


def get_start_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(BTN_CREATE_WORKSPACE)],
        [KeyboardButton(BTN_JOIN_WORKSPACE)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_main_menu_keyboard(
    is_admin: bool = False,
    is_owner: bool = False,
) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(BTN_TEAM)],
        [KeyboardButton(BTN_MY_STATUS)],
        [KeyboardButton(BTN_CHANGE_STATUS)],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(BTN_ADMIN)])
    if is_owner:
        keyboard.append([KeyboardButton(BTN_DELETE_WORKSPACE)])
    else:
        keyboard.append([KeyboardButton(BTN_LEAVE_WORKSPACE)])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


REMOVE_KEYBOARD = ReplyKeyboardRemove()
