
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
import random
from enum import Enum


class CaptchaType(Enum):
    SIMPLE = 1
    MATH = 2
    SYMBOLS = 3


class CaptchaPunishment(Enum):
    KICK = 1
    BAN = 2
    MUTE = 3

async def is_captcha_active(conf, gid):
    return conf["groups"][gid]["captcha_active"]

def get_simple_captcha_menu(button_text, uid, callback_dat):

    keyboard_button = InlineKeyboardButton(
        button_text,
        callback_data=callback_dat.new(
            action="unmute", uid=uid, msg_id=0
        ),
    )
    start_keyboard = InlineKeyboardMarkup(resize_keyboard=True).add(
        keyboard_button
    )   

    return start_keyboard

def get_math_captcha_menu( uid, callback_dat):

    x = random.randint(0,15)
    y = random.randint(0,15)

    finres = x + y

    firstres = random.randint(0,30)
    secondres = random.randint(0,30)

    option1_button = InlineKeyboardButton(
    str(firstres),
    callback_data=callback_dat.new(
        action="captcha_fail", uid=uid, msg_id=0
    ),
    )
    option2_button = InlineKeyboardButton(
    str(secondres),
    callback_data=callback_dat.new(
        action="captcha_fail", uid=uid, msg_id=0
    ),
    )  
    finoption_button = InlineKeyboardButton(
    str(finres),
    callback_data=callback_dat.new(
        action="unmute", uid=uid, msg_id=0
    ),
    )

    button_list = [option1_button, option2_button, finoption_button]
    random.shuffle(button_list)
    menu = InlineKeyboardMarkup(resize_keyboard=True)

    menu = menu.row(button_list[0], button_list[1], button_list[2])

    question = f"What is {x} + {y}?"

    return (question,menu)

def get_symbols_captcha_menu():
    pass