
from aiogram.types import (
    ChatMemberRestricted,
    ChatPermissions,
    Message,
    ContentType,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ParseMode,
)
import captcha
from captcha import CaptchaType
import config

async def get_group_title(bot, gid):
    chat = await bot.get_chat(gid)
    title = chat.title
    return title

async def get_captcha_menu(gid, callback_dat, single_callback, enabled):
    menu = InlineKeyboardMarkup(resize_keyboard=True)
    captcha_active = enabled
    toggle_button_text = None
    if captcha_active:
        toggle_button_text = "[ ON 🟢 ]"
    else:
        toggle_button_text = "[ OFF 🔴 ]"
    
    toggle_button = InlineKeyboardButton(
        toggle_button_text,
        callback_data=callback_dat.new(
            action="toggle_captcha", gid=gid, group_title=""
        )
    )

    type_button = InlineKeyboardButton(
        "Type 💡",
        callback_data=callback_dat.new(
            action="change_captcha_type", gid=gid, group_title=""
        )
    )

    chage_button_text_button = InlineKeyboardButton(
        "Edit captcha button text ✍🏻",
        callback_data=callback_dat.new(
            action="change_captcha_button_text", gid=gid, group_title=""
        )
    )
    change_captcha_text_button = InlineKeyboardButton(
        "Edit captcha text ✍🏻",
        callback_data=callback_dat.new(
            action="change_captcha_text", gid=gid, group_title=""
        )
    )
    show_button_text = InlineKeyboardButton(
        "Show button text 📝",
        callback_data=callback_dat.new(
            action="show_captcha_button_text", gid=gid, group_title=""
        )
    )
    show_captcha_text = InlineKeyboardButton(
        "Show captcha text 📝",
        callback_data=callback_dat.new(
            action="show_captcha_text", gid=gid, group_title=""
        )
    )
    punishment_button = InlineKeyboardButton(
        "Punishment 💢",
        callback_data=callback_dat.new(
            action="change_captcha_punishment", gid=gid, group_title=""
        )
    )

    punishment_time = InlineKeyboardButton(
        "Time period ⏲️ ",
        callback_data=callback_dat.new(
            action="toggle_captcha_punishment", gid=gid, group_title=""
        )
    )

    back_button = InlineKeyboardButton(
        "👈 Back",
        callback_data=callback_dat.new(
            action="select_group", gid=gid, group_title=""
        )
    )
    close_button = InlineKeyboardButton(
        "Close ❌",
        callback_data=single_callback.new(
            action="close"
        )
    )

    menu = menu.row(toggle_button).row(type_button).row(chage_button_text_button).row(change_captcha_text_button).row(show_button_text, show_captcha_text).row(punishment_button, punishment_time).row(back_button).row(close_button)
    return menu


async def get_welcome_message_menu(gid, uid, callback_dat, single_callback, config):
    menu = InlineKeyboardMarkup(resize_keyboard=True)

    toggle_active = await is_welcome_active(gid)
    toggle_button_text = None
    if toggle_active:
        toggle_button_text = "[ ON 🟢 ]"
    else:
        toggle_button_text = "[ OFF 🔴 ]"

    toggle_button = InlineKeyboardButton(
        toggle_button_text,
        callback_data=bot_config_callback.new(
            action="toggle_weclome_message", gid=gid, group_title=title
        )
    )   

    change_text_button = InlineKeyboardButton(
        "Change message ✍🏻",
        callback_data=bot_config_callback.new(
            action="change_welcome_message", gid=gid, group_title=title
        )
    )   
    help_button = InlineKeyboardButton(
        "Help ℹ️",
        callback_data=bot_config_callback.new(
            action="select_group", gid=gid, group_title=title
        )
    )
    back_button = InlineKeyboardButton(
        "👈 Back",
        callback_data=bot_config_callback.new(
            action="select_group", gid=gid, group_title=title
        )
    )
    close_button = InlineKeyboardButton(
        "Close ❌",
        callback_data=single_callback.new(
            action="close"
        )
    )

    menu = menu.row(toggle_button).row(change_text_button).row(help_button, back_button).row(close_button)

    return menu

async def get_captcha_type_menu(gid, title, callback_dat, bot_config_callback, single_callback, captcha_type):
    menu = InlineKeyboardMarkup(resize_keyboard=True)

    simple_button_text = "{} Simple 🖱️ {}"
    math_button_text = "{} Math ➗ {}"
    symbols_button_text = "{} Symbols 🔣 {}"

    if captcha_type == CaptchaType.SIMPLE:
        simple_button_text = simple_button_text.format(">>", "<<")
        math_button_text = math_button_text.format("","")
        symbols_button_text = symbols_button_text.format("","")
    elif captcha_type == CaptchaType.MATH:
        simple_button_text = simple_button_text.format("","")
        math_button_text = math_button_text.format(">>", "<<")
        symbols_button_text = symbols_button_text.format("","")
    elif captcha_type == CaptchaType.SYMBOLS:
        simple_button_text = simple_button_text.format("","")
        math_button_text = math_button_text.format("","")
        symbols_button_text = symbols_button_text.format(">>", "<<")

    simple_button = InlineKeyboardButton(
        simple_button_text,
        callback_data=callback_dat.new(
            action="set_captcha_type", type=CaptchaType.SIMPLE.value, gid=gid
        )
    )

    math_button = InlineKeyboardButton(
        math_button_text,
        callback_data=callback_dat.new(
            action="set_captcha_type", type=CaptchaType.MATH.value, gid=gid
        )
    )
    symbols_button = InlineKeyboardButton(
        symbols_button_text,
        callback_data=callback_dat.new(
            action="set_captcha_type", type=CaptchaType.SYMBOLS.value, gid=gid
        )
    )
    help_button = InlineKeyboardButton(
        "Help ℹ️",
        callback_data=bot_config_callback.new(
            action="select_group", gid=gid, group_title=title
        )
    )
    back_button = InlineKeyboardButton(
        "👈 Back",
        callback_data=bot_config_callback.new(
            action="select_group", gid=gid, group_title=title
        )
    )
    close_button = InlineKeyboardButton(
        "Close ❌",
        callback_data=single_callback.new(
            action="close"
        )
    )
    menu = menu.row(simple_button, math_button, symbols_button).row(help_button, back_button).row(close_button)
    return menu


async def get_captcha_punishment_menu(gid, title, punishment):

    menu = InlineKeyboardMarkup(resize_keyboard=True)

    mute_button_text = "{} Mute 🔇 {}"
    kick_button_text = "{} Kick 🦵🏼 {}"
    ban_button_text = "{} Ban 🚧 {}"

    if punishment == CaptchaPunishment.MUTE:
        mute_button_text = mute_button_text.format(">>", "<<")
        kick_button_text = kick_button_text.format("", "")
        ban_button_text = ban_button_text.format("","")
    elif punishment == CaptchaPunishment.KICK:
        mute_button_text = mute_button_text.format("", "")
        kick_button_text = kick_button_text.format(">>", "<<")
        ban_button_text = ban_button_text.format("","")
    elif punishment == CaptchaPunishment.BAN:
        mute_button_text = mute_button_text.format("", "")
        kick_button_text = kick_button_text.format("", "")
        ban_button_text = ban_button_text.format(">>","<<")

    mute_button = InlineKeyboardButton(
        mute_button_text,
        callback_data=set_punishment_cb.new(
            punishment=CaptchaPunishment.MUTE.value, gid=gid
        )
    )

    kick_button = InlineKeyboardButton(
        kick_button_text,
        callback_data=set_punishment_cb.new(
            punishment=CaptchaPunishment.KICK.value, gid=gid
        )
    )

    ban_button = InlineKeyboardButton(
        ban_button_text,
        callback_data=set_punishment_cb.new(
            punishment=CaptchaPunishment.BAN.value, gid=gid
        )
    )

    back_button = InlineKeyboardButton(
        "👈 Back",
        callback_data=bot_config_callback.new(
            action="select_group", gid=gid, group_title=title
        )
    )
    close_button = InlineKeyboardButton(
        "Close ❌",
        callback_data=single_callback.new(
            action="close"
        )
    )
    menu = menu.row(mute_button, kick_button, ban_button).row(back_button, close_button)
    return menu