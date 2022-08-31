
import asyncio
import argparse
import os
import logging
import aiosqlite
import sqlite3
import json
import sys
import captcha
import menus
import config
import database
from captcha import CaptchaType,CaptchaPunishment
from enum import Enum
from datetime import datetime, timedelta
from contextlib import suppress
import aiofiles
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.chat_member_updated import ChatMemberUpdated 
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import RegexpCommandsFilter
from aiogram.utils.exceptions import *
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
from aiogram.utils.exceptions import (
    MessageToEditNotFound,
    MessageCantBeEdited,
    MessageCantBeDeleted,
    MessageToDeleteNotFound,
)
from aiogram.utils.callback_data import CallbackData

parser = argparse.ArgumentParser(description="")
storage = MemoryStorage()
parser.add_argument(
    "config", type=str, help="Path to config file", default="config.json"
)
parser.add_argument("skipupdates", type=bool, help="Skip recent updates")

cmd_args = parser.parse_args()

loop = None

CONFIG = None
DATABASE = "groupbot.db"
# load config file
if not os.path.isfile(cmd_args.config):
    logging.error("Config file not found.")
    sys.exit(1)
else:
    try:
        with open(cmd_args.config, "r", encoding="UTF-8") as f:
            CONFIG = json.load(f)
    except Exception:
        logging.error("Could not parse JSON config file")
        sys.exit(1)

bot = Bot(token=CONFIG["bot_hash"])
dispatcher = Dispatcher(bot=bot, storage=storage)
cb_data = CallbackData("unmute", "action", "uid", "msg_id")
bot_config_callback = CallbackData("config", "action", "gid", "group_title")
single_callback = CallbackData("singleaction", "action")
start_keyboard_cb_data = CallbackData("forward")
set_captcha_type_cb = CallbackData("captcha", "gid", "action", "type")
set_punishment_cb = CallbackData("punishment", "gid", "punishment")

raid_mode = {}  
raid_detection = {}
log_verify = []
auto_raid_toggle_blocked = []

next_step = {}

current_config = {}

class Form(StatesGroup):
    welcome_text = State() 
    captcha_text = State() 
    captcha_button_text = State() 


class NextStep(Enum):
    CHANGE_CAPTCHA_TEXT = "CHANGE_CAPTCHA"
    CHANGE_BUTTON_TEXT = "CHANGE_BUTTON_TEXT"
    CHANGE_WELCOME_TEXT = "CHANGE_WELCOME_TEXT"


async def setup_config_sync_task(sleep):
    while True:
        print(config.get())
        loop.create_task(database.save_conf(config.get(), DATABASE))
        logging.info("Updating database")
        await asyncio.sleep(sleep)

async def increase_joins(gid):
    """Asynchronous increase join counter within last 30 seconds, used for auto raid detection"""

    now = datetime.now().replace(microsecond=0)

    if gid not in raid_detection:
        raid_detection[gid] = [1, now]
    else:

        last_timestamp = raid_detection[gid][1]
        diff = now - last_timestamp
        diff_sec = diff.seconds
        treshold = await config.get_autoraid_treshold(gid)

        if diff_sec <= 30:
            # activate raid mode if treshold is exceeded
            if raid_detection[gid][0] >= treshold and not is_in_raidmode(gid):

                raid_mode[gid] = True
                asyncio.create_task(deactivate_raidmode(gid, 180))
                raid_detection[gid] = [1, now]
                msg = await bot.send_message(
                    gid, "Der automatische Raid-Mode wurde für 3 Minuten aktiviert."
                )
                asyncio.create_task(delete_message(msg, 60))
            else:
                raid_detection[gid][0] = raid_detection[gid][0] + 1
        else:
            raid_detection[gid] = [1, now]

async def is_bot_admin(chatid):
    bot_id = await bot.get_me()
    b_user = await bot.get_chat_member(chatid, bot_id.id)
    if b_user.status == 'administrator': 
        return True

    return False

def is_in_raidmode(gid):
    """
    Returns wether a group is in raid mode

        Parameters:
            gid (int): Group ID to check

        Returns:
            res (bool): Returns a bool representing the raid modes status

    """

    res = False
    gid = int(gid)
    if raid_mode.get(gid):
        res = raid_mode[gid]

    return res


def is_user_muted(member):
    """
    Takes a ChatMember object and returns if user is muted.
    """

    if isinstance(member, ChatMemberRestricted) and not member.can_send_messages:
        return True
    return False


def user_is_admin(message):
    pass

async def set_default_user_permissions(uid, gid):
    """Set users default permission when allowed to chat"""
    perm = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_change_info=False,
        can_invite_users=False,
        can_pin_messages=False,
    )

    await bot.restrict_chat_member(gid, uid, permissions=perm)


async def mute_user(uid, gid):
    """Mute a specific user"""
    perm = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
        can_change_info=False,
        can_invite_users=False,
        can_pin_messages=False,
    )

    await bot.restrict_chat_member(gid, uid, permissions=perm)

async def time_mute_user(uid, gid, time):
    perm = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
        can_change_info=False,
        can_invite_users=False,
        can_pin_messages=False,
    )

    await bot.restrict_chat_member(gid, uid, permissions=perm, until_date = (datetime.now() + timedelta(seconds=60)))

async def update_config_file():
    """Asynchronous file write operation for config file"""
    async with aiofiles.open(cmd_args.config, mode="w") as f:
        await f.write(json.dumps(CONFIG))
        logging.info("Config file updated.")

async def activate_raidmode(gid: int):
    if not raid_mode.get(gid):
        raid_mode[gid] = True
        msg = await bot.send_message(
            gid, "Der Raid-Mode wurde aktiviert!"
        )
        asyncio.create_task(delete_message(msg, 60))

async def deactivate_raidmode(gid: int, sleep_time: int = 0):
    """Delayed deactivation of raid mode in asynchronous task"""
    await asyncio.sleep(sleep_time)

    if raid_mode.get(gid):
        raid_mode[gid] = False
        msg = await bot.send_message(
            gid, "Der automatische Raid-Mode wurde wieder deaktiviert!"
        ) 
        asyncio.create_task(delete_message(msg, 30))


async def delete_message(message: Message, sleep_time: int = 0):
    """Delayed deletion of message in asynchronous task"""
    await asyncio.sleep(sleep_time)
    with suppress(MessageToDeleteNotFound):
        await bot.delete_message(message.chat.id, message.message_id)

async def delete_greeting(message: Message, uid, sleep_time: int = 0):
    """Delayed deletion of greeting message in asynchronous task"""
    await asyncio.sleep(sleep_time)
    gid = message.chat.id

    if "Alles klar" in message.text:
        await asyncio.sleep(20)

    member = await message.chat.get_member(uid)

    if hasattr(member, "can_send_messages") and not member.can_send_messages:
        await bot.kick_chat_member(
            chat_id=gid, user_id=uid, until_date=datetime.now() + timedelta(seconds=35)
        )

    with suppress(MessageCantBeDeleted, MessageToDeleteNotFound):
        await bot.delete_message(gid, message.message_id)


@dispatcher.message_handler(content_types=ContentType.LEFT_CHAT_MEMBER)
async def on_leave(message: Message):
    """Delete all leave messages"""
    await message.delete()

async def get_captcha_type(gid):
    captcha_type = config.get_captcha_type(gid)
    return captcha_type

@dispatcher.chat_member_handler() 
async def on_join(update: types.ChatMemberUpdated, content_types=["new_chat_member"]):
    """Join handler, manages captcha and user rights on join"""
    member = update.from_user
    gid = update.chat.id
    uid = member.id
    mention = member.get_mention(as_html=True)

    if (update.new_chat_member.status == "member" or update.new_chat_member.status == "restricted") and (update.old_chat_member.status == "left"):
        if gid in config.get_groups() and not is_user_muted(member):
            # if is in raid mode kick user temporary, else send captcha
            if is_in_raidmode(gid):
                await bot.kick_chat_member(
                    chat_id=gid,
                    user_id=uid,
                    until_date=datetime.now() + timedelta(seconds=120),
                )
            else:
                with suppress(AttributeError):
                    asyncio.create_task(mute_user(uid, gid))

                keyboard_button = InlineKeyboardButton(
                    config.get_captcha_button_text(gid),
                    callback_data=cb_data.new(
                        action="unmute", uid=uid, msg_id=0
                    ),
                )
                start_keyboard = InlineKeyboardMarkup(resize_keyboard=True).add(
                    keyboard_button
                )
                mention = member.get_mention(as_html=True)
                
                captcha_type = await get_captcha_type(gid)

                ctext = None
                men = None

                if captcha_type == CaptchaType.SIMPLE:
                    men = captcha.get_simple_captcha_menu(config.get_captcha_button_text(gid), uid, cb_data)
                    ctext = config.get_captcha_text(gid)
                elif captcha_type == CaptchaType.MATH:
                    cap = captcha.get_math_captcha_menu(uid, cb_data)
                    question = cap[0]
                    men = cap[1]
                    ctext = f"Hey, {mention} please solve the following math problem:\n<b>{question}</b>"
                    
                if ctext and men:
                    msg = await bot.send_message(gid,
                        ctext,
                        reply_markup=men,
                        parse_mode=ParseMode.HTML,
                    )
                    asyncio.create_task(delete_greeting(msg, uid, 60))
                    asyncio.create_task(increase_joins(gid))

@dispatcher.message_handler(content_types=ContentType.NEW_CHAT_MEMBERS)
async def on_join_delte_msg(message : Message):
    await message.delete()


@dispatcher.callback_query_handler(cb_data.filter(action="captcha_fail"))
async def captcha_failed_handler(query: CallbackQuery, callback_data: dict):
    pass

@dispatcher.callback_query_handler(cb_data.filter(action="unmute"))
async def unmute_button_handler(query: CallbackQuery, callback_data: dict):
    """Handler managing captcha on button click"""
    uid = callback_data["uid"]
    qid = query.from_user["id"]
    msg_id = query.message.message_id
    gid = query.message.chat.id

    if int(uid) == int(qid):
        asyncio.create_task(set_default_user_permissions(uid, query.message.chat.id))

    new_buttons = InlineKeyboardMarkup().row(
        InlineKeyboardButton("Regeln", command="/rules", ),
    )

    if int(uid) == int(qid):
        with suppress(MessageCantBeEdited, MessageToEditNotFound):
            member = query["from"]
            mention = member.get_mention(as_html=True)
            await bot.edit_message_text(
                text=menus.get_welcome_message(gid).format(mention=mention),
                chat_id=query.message.chat.id,
                message_id=msg_id,
                parse_mode=ParseMode.HTML,
            )
    await query.answer()

@dispatcher.message_handler(commands=["raidmode"])
async def raid_mode_command(message: Message):
    """Command handler for raid mode command"""

    uid = message.from_user.id
    asyncio.create_task(delete_message(message, 1))

    if config.is_user_privileged(message.chat.id, uid) and message.chat.type == "supergroup":

        gid = message.chat.id
        action = None
        args = message.text.split(" ")[1:]
        status = False

        if len(args) == 0:

            if raid_mode.get(gid):
                status = raid_mode[gid]
            if status:
                raid_mode[gid] = False
                action = "deaktiviert"
            else:
                action = "aktiviert"
                raid_mode[gid] = True

        elif len(args) == 1:

            if args[0].lower() == "off":
                raid_mode[gid] = False
                action = "deaktiviert"
            elif args[0].lower() == "on":
                action = "aktiviert"
                raid_mode[gid] = True
            elif args[0].lower() == "status":
                status = "deaktiviert"

                if gid in raid_mode:

                    if raid_mode[gid] is True:
                        status = "aktiviert"

                msg = await bot.send_message(gid, "Der Raid-Mode ist aktuell " + status)
                asyncio.create_task(delete_message(msg, 30))

        if action:
            msg = await bot.send_message(gid, "Der Raid-Mode wurde " + action)
            asyncio.create_task((msg, 30))


@dispatcher.message_handler(commands=["mute"])
async def mute_command(message: Message):

    args = message.text.split(" ")[1:]
    reply_mute = False
    user_was_mentioned = False
    mention = None
    ban_id = None
    msg_txt = None
    ban_time = 0
    ban_reason = "None"

    for e in message.entities:
        if e.type == "text_mention":
            user_was_mentioned = True
            ban_id = e.user.id
            mention = e.user.get_mention(as_html=True)
            break

    if message.reply_to_message:
        reply_to_message = True
        from_u = message.reply_to_message['from']
        mention = from_u.get_mention(as_html=True)
        ban_id = from_u.id
        msg_txt = message.reply_to_message.text

    if user_was_mentioned and reply_to_message:
        await bot.send_message(message.chat.id, "Do not mention user AND reply to message for mute")
        return

    asyncio.create_task(time_mute_user(ban_id,message.chat.id, 60))
    
    asyncio.create_task(log_command(message.chat.id, message.text, message.from_user.id, message.from_user.get_mention(as_html=True), msg_txt, ban_id, mention))

@dispatcher.message_handler(commands=["setup"])
async def setup_command(message: Message):
    """Enable group for this bot, only for bot_owners"""
    args = message.text.split(" ")[1:]
    uid = message["from"]["id"]
    gid = message.chat.id

    admin_stat = await is_bot_admin(gid)
    if not admin_stat:
        await bot.send_message(gid, "Add me as an administrator in this group to setup this bot!")
        return

    if len(args) == 0:

        if config.is_bot_owner(uid):
            if message.chat.type != "supergroup":
                msg = await message.answer("Diese Gruppe ist keine SuperGroup!")
                asyncio.create_task(delete_message(msg, 30))
                return
            msg = None
            if config.is_group_registered(gid):

                await config.setup_group(gid,uid)

                #asyncio.create_task(update_config_file())
                asyncio.create_task(aconfig.dd_user_privileges(uid, gid, [captcha.AdminPermission.CAN_DELETE, captcha.AdminPermission.CAN_KICK, captcha.AdminPermission.CAN_MUTE]))
                msg = await message.answer("Die gruppe wurde erfolgreich registriert.")
            else:
                msg = await message.answer("Die gruppe wurde bereits registriert.")

            asyncio.create_task(delete_message(message, 30))
    elif len(args) == 1:

        if args[0].lower() == "log":
            log_verify.append(gid)
            await bot.send_message(gid, "Alright, please forward the verification message from your log channel within 2 minutes.")
            asyncio.create_task(disable_log_verification(gid))

    try: 
        await message.delete()
    except MessageCantBeDeleted:
        pass

async def log_command(gid, command, issuer, mention , related_msg="", related_user=0, related_mention=""):
    log_channel = config-get_log_channel(gid)

    message = "#SUPERUSER_COMMAND\nG: "+ str(gid) + "\n<b>FROM</b>: " + mention + " [" + str(issuer) + "]\n\n" + command
    if related_msg != "":
        message += "\n\n<i>Related User: </i>\n" + related_mention + " [" + str(related_user) + "]\n\nRelated message:\n<code>" + related_msg + "</code>" 
    if log_channel != 0:
        await bot.send_message(log_channel, message, parse_mode=ParseMode.HTML)

#async def log_join(gid, uid, mention):


#async def log_leave(uid, mention)


async def disable_log_verification(gid):
    await asyncio.sleep(120)
    if gid in log_verify:
        log_verify.remove(gid)

@dispatcher.message_handler(commands=["verify"])
async def verify(message: types.Message):
    gid = message.chat.id
    forwarded = message["forward_from_chat"]
    chat_id = None
    chat = None
    if forwarded:
        if gid in log_verify:
            chat_id = forwarded["id"]
            try:
                chat = await bot.get_chat(chat_id)
                admins = await bot.get_chat_administrators(chat_id)
            except ChatNotFound:
                await bot.send_message(gid, "❌ I am not member of this channel!")
            except Unauthorized:
                await bot.send_message(gid, "❌ I am not member of this channel!")

            if chat.type != "channel":
                bot.send_message(gid, "❌ Log-Channel shouldn't be a group!")
                return

            me = await bot.get_me()
            for a in admins:

                if a.user.id == me.id:
                    config.set_log_channel(chat_id)
                    await bot.send_message(gid,"✔️ Log channel successfull added!")
                    if gid in log_verify:
                        log_verify.remove(gid)
                    break
                else:
                    await bot.send_message(gid, "❌ Sorry, I am not admin of this channel!")
                    break

@dispatcher.message_handler(commands=["help"])
async def help_command(message: types.Message):
    """Handler for help command"""
    gid = message.chat.id
    if config.is_user_privileged(gid, message.from_user.id):
        help_text = """Available commands:

```/help``` -> 🔍 Display this help text

```/raidmode``` -> 🕵‍♂️ Toggle raid mode

```/priv``` add|rm <USER-ID>
    -> 🤘 Add or remove user to privileged list

        """
        msg = await bot.send_message(gid, help_text, parse_mode=ParseMode.MARKDOWN)
        asyncio.create_task(delete_message(msg, 30))
        await message.delete()

@dispatcher.message_handler(commands=['reload'])
async def reload_command(message: types.Message):
    asyncio.create_task(load_config)

@dispatcher.message_handler(commands=["priv"])
async def priv_add_command(message: Message):
    """Handler for priv command, used to add privileges to a user of a group"""

    args = message.text.split(" ")[1:]
    asyncio.create_task(delete_message(message, 1))

    if len(args) == 2:

        uid = None
        gid = message.chat.id
        arg0 = args[0].lower()
        arg1 = args[1].lower()

        try:
            uid = int(arg1)
        except ValueError:
            msg = await message.reply_to_message("/priv add <USER-ID>")
            asyncio.create_task(delete_message(message, 30))
            return

        if arg0 == "add":

            if not config.is_user_privileged(gid, uid):

                asyncio.create_task(add_user_privileges(uid, gid, [captcha.AdminPermission.CAN_DELETE, captcha.AdminPermission.CAN_KICK, captcha.AdminPermission.CAN_MUTE]))
                msg = await message.answer("Nutzerrechte wurden angepasst.")
                asyncio.create_task(delete_message(msg, 30))
            else:
                msg = await message.answer("Nutzer ist bereits privilegiert.")
                asyncio.create_task(delete_message(msg, 30))

        elif arg0 == "rm":

            if not config.is_user_privileged(gid, uid):
                msg = await message.answer("Nutzer ist nicht privilegiert.")
                asyncio.create_task(delete_message(msg, 30))
            else:

                asyncio.create_task(config.unprivilege_user(uid, gid))
                msg = await message.answer("Nutzerrechte wurden angepasst.")
                asyncio.create_task(delete_message(msg, 30))

@dispatcher.message_handler(commands=["globalgroups"])
async def global_groups_command(message: Message):
    gids = config.get_privileged_user_groups(message.from_user.id)
    chats = await get_groups_by_ids(gids)

@dispatcher.callback_query_handler(single_callback.filter(action="close"))
async def close_menu_callback(cquery: CallbackQuery, callback_data: dict) -> None:
    await cquery.message.delete()
    await cquery.answer()

async def get_groups_by_ids(group_ids):
    groups = []
    for gid in group_ids:
        try:
            chat = await bot.get_chat(gid)
            groups.append(chat)
        except BotKicked:
            config.set_bot_kicked(gid)
        except ChatNotFound:
            config.set_bot_kicked(gid)

    return groups

async def block_toggle_raidmode(gid):
    auto_raid_toggle_blocked.append(gid)
    await asyncio.sleep(5)
    auto_raid_toggle_blocked.remove(gid)

async def get_raidmode_menu(gid, title):
    menu = InlineKeyboardMarkup(resize_keyboard=True)

    raidmode_active = is_in_raidmode(gid)
    toggle_button_text = "Toggle raidmode [ " 
    if raidmode_active:
        toggle_button_text += "ON 🟢 ]"
    else:
        toggle_button_text += "OFF 🔴 ]"


    auto_raidmode_active = config.auto_raid_enabled(gid)
    toggle_raidmode_button_text = "Toggle auto raidmode [ "
    if auto_raidmode_active:
        toggle_raidmode_button_text += "ON 🟢 ]"
    else:
        toggle_raidmode_button_text += "OFF 🔴 ]"

    toggle_button = InlineKeyboardButton(
        toggle_button_text,
        callback_data=bot_config_callback.new(
            action="toggle_raidmode", gid=gid, group_title=title
        )
    )

    auto_raid_button = InlineKeyboardButton(
        toggle_raidmode_button_text,
        callback_data=bot_config_callback.new(
            action="toggle_autoraid", gid=gid, group_title=title
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

    menu = menu.row(toggle_button).row(auto_raid_button).row(back_button).row(close_button)
    return menu


async def get_captcha_time_period_menu(gid, title):
    pass

async def is_in_next_step(gid, uid):
    is_in_next_step = None
    return None

async def set_in_next_setp(gid, uid, n_step: NextStep):
    next_step[uid] = gid

@dispatcher.callback_query_handler(bot_config_callback.filter(action="toggle_weclome_message"))
async def toggle_welcome_message_callback(cquery: CallbackQuery, callback_data: dict):
    gid = int(callback_data["gid"])
    title = callback_data["group_title"]
    message = cquery.message
    msg_text = "Change Welcome text"

    welcome_active = config.is_welcome_active(gid)
    config.toggle_welcome(gid)


    menu = await menus.get_welcome_message_menu(gid, cquery.fron_user.id, title)

    await cquery.answer()
    await meesage.edit_text(msg_text, reply_markup=menu)

@dispatcher.callback_query_handler(bot_config_callback.filter(action="show_captcha_text"))
async def show_captcha_text(cquery: CallbackQuery, callback_data: dict):
    gid = int(callback_data["gid"])
    text = config.get_captcha_text(gid)
    title = "title"
    message = "Configuration of group Bot test grubbe\n\nModule: Captcha\n\n<b>Captcha  text:</b>\n" + text

    captcha_enabled = config.captcha_enabled(gid)
    menu = await menus.get_captcha_menu(gid, bot_config_callback, single_callback, captcha_enabled)
    await cquery.message.edit_text(message, reply_markup=menu, parse_mode=ParseMode.HTML)


@dispatcher.callback_query_handler(bot_config_callback.filter(action="show_captcha_button_text"))
async def show_captcha_button_text(cquery: CallbackQuery, callback_data: dict):
    gid = int(callback_data["gid"])
    text =config.get_captcha_button_text(gid)
    title = "title"
    message = "Configuration of group Bot test grubbe\n\nModule: Captcha\n\n<b>Captcha button text:</b>\n" + text
    captcha_enabled = config.captcha_enabled(gid)
    menu = await menus.get_captcha_menu(gid, bot_config_callback, single_callback, captcha_enabled)
    await cquery.message.edit_text(message, reply_markup=menu, parse_mode=ParseMode.HTML)   

@dispatcher.callback_query_handler(bot_config_callback.filter(action="change_captcha_punishment"))
async def change_punishment_callback(cquery: CallbackQuery, callback_data: dict):
    gid = int(callback_data["gid"])
    title = callback_data["group_title"]
    message = cquery.message
    msg_text = f"Configuration of group <b>{title}</b>\n\nModule: Captcha|Punishment"

    punishment = config.get_captcha_punishment(gid)
    menu = await get_captcha_punishment_menu(gid, title, punishment)
    await message.edit_text(msg_text, reply_markup=menu)
    await cquery.answer()

@dispatcher.callback_query_handler(bot_config_callback.filter(action="change_welcome_message"))
async def change_welcome_message_callback(cquery: CallbackQuery, callback_data: dict):
    gid = int(callback_data["gid"])
    title = callback_data["group_title"]
    message = cquery.message
    msg_text = "Change Welcome text"

    await Form.welcome_text.set()

    menu = await menus.get_welcome_message_menu(gid, cquery.from_user.id, title)

    await bot.send_message(cquery.from_user.id, "Alright! Please send me your new text.")

    await cquery.answer()


@dispatcher.callback_query_handler(bot_config_callback.filter(action="change_captcha_text"))
async def change_captcha_text_first_callback(cquery: CallbackQuery, callback_data: dict):
    gid = int(callback_data["gid"])
    title = callback_data["group_title"]
    message = cquery.message
    msg_text = f"Configuration of group <b>{title}</b>\n\nModule: Captcha|Symbols"

    await Form.captcha_text.set()

    menu = await menus.get_welcome_message_menu(gid, cquery.from_user.id, title)

    await bot.send_message(cquery.from_user.id, "Alright! Please send me your new text.")

    await cquery.answer()

@dispatcher.callback_query_handler(bot_config_callback.filter(action="change_captcha_button_text"))
async def change_captcha_button_text_first_callback(cquery: CallbackQuery, callback_data: dict):
    gid = int(callback_data["gid"])
    title = callback_data["group_title"]
    message = cquery.message
    msg_text = f"Configuration of group <b>{title}</b>\n\nModule: Captcha|Symbols"

    await Form.captcha_button_text.set()

    menu = await menus.get_welcome_message_menu(gid, cquery.from_user.id, title)

    await bot.send_message(cquery.from_user.id, "Alright! Please send me your new text.")

    await cquery.answer()

@dispatcher.callback_query_handler(bot_config_callback.filter(action="open_welcome_message_menu"))
async def welcome_message_menu_callback(cquery: CallbackQuery, callback_data: dict):
    gid = int(callback_data["gid"])
    title = callback_data["group_title"]
    message = cquery.message
    msg_text = "Change Welcome text"
    menu = await menus.get_welcome_message_menu(gid, cquery.from_user.id, title)
    await cquery.answer()
    await message.edit_text(msg_text, reply_markup=menu)    


@dispatcher.message_handler(state=Form.captcha_button_text)
async def change_captcha_button_text_second_callback(message: Message, state: FSMContext):
    uid = message.from_user.id
    text = message.text
    gid = current_config[message.from_user.id]

    await set_captcha_button_text(int(gid), text)
    await state.finish()
    await bot.send_message(uid, "Captcha button text has been changed!")


@dispatcher.message_handler(state=Form.captcha_text)
async def change_captcha_text_second_callback (message: Message, state: FSMContext):
    uid = message.from_user.id
    text = message.text
    gid = current_config[message.from_user.id]

    await config.set_captcha_text(int(gid), text)
    await state.finish()
    await bot.send_message(uid, "Captcha text has been changed!")

@dispatcher.callback_query_handler(set_punishment_cb.filter())
async def set_punishment_callback (cquery: CallbackQuery, callback_data: dict):
    gid = int(callback_data["gid"])
    punishment = callback_data["punishment"]    
    config.set_captcha_punishment(gid, punishment)

    punishment = config.get_captcha_punishment(gid)
    menu = await get_captcha_punishment_menu(gid, "", punishment)
    await cquery.message.edit_text(cquery.message.text, reply_markup=menu)
    await cquery.answer()


@dispatcher.callback_query_handler(set_captcha_type_cb.filter(action="set_captcha_type"))
async def set_captcha_type_callback(cquery: CallbackQuery, callback_data: dict):
    gid = int(callback_data["gid"])
    message = cquery.message

    config.set_captcha_type(gid, CaptchaType(int(callback_data["type"])))

    msg_text = "Choose a captcha method:"
    captcha_type = config.get_captcha_type(gid)
    menu = await menus.get_captcha_type_menu(gid, "", set_captcha_type_cb, bot_config_callback, single_callback, captcha_type)
    await cquery.answer()
    await message.edit_text(msg_text, reply_markup=menu)

@dispatcher.callback_query_handler(bot_config_callback.filter(action="change_captcha_type"))
async def captcha_type_menu_open(cquery: CallbackQuery, callback_data: dict) -> None:
    gid = int(callback_data["gid"])
    title = callback_data["group_title"]
    message = cquery.message
    msg_text = f"Configuration of group <b>{title}</b>\n\nModule: Captcha|Symbols"

    captcha_type = config.get_captcha_type(gid) 
    menu = await menus.get_captcha_type_menu(gid, title, set_captcha_type_cb, bot_config_callback, single_callback, captcha_type)
    await cquery.answer()

    await message.edit_text(msg_text, reply_markup=menu)

@dispatcher.callback_query_handler(bot_config_callback.filter(action="toggle_captcha"))
async def captcha_toggle_callback(cquery: CallbackQuery, callback_data: dict) -> None:

    gid = int(callback_data["gid"])
    title = callback_data["group_title"]
    message = cquery.message
    msg_text = f"Configuration of group <b>{title}</b>\n\nModule: Captcha"

    config.toggle_captcha(gid)
    menu = await menus.get_captcha_menu(gid, bot_config_callback, single_callback, CONFIG)
    await cquery.answer()

    await message.edit_text(msg_text, reply_markup=menu)

@dispatcher.callback_query_handler(bot_config_callback.filter(action="config_captcha"))
async def captcha_menu_open_callback(cquery: CallbackQuery, callback_data: dict) -> None:

    gid = int(callback_data["gid"])
    title = callback_data["group_title"]
    message = cquery.message
    msg_text = f"Configuration of group <b>{title}</b>\n\nModule: Captcha"
    captcha_enabled = config.captcha_enabled(gid)
    menu = await menus.get_captcha_menu(gid, bot_config_callback, single_callback, captcha_enabled)
    await cquery.answer()

    await message.edit_text(msg_text, reply_markup=menu, parse_mode=ParseMode.HTML)

@dispatcher.callback_query_handler(bot_config_callback.filter(action="toggle_raidmode"))
async def toggle_raidmode_callback(cquery: CallbackQuery, callback_data: dict) -> None:

    gid = int(callback_data["gid"])
    if gid not in auto_raid_toggle_blocked:
        message = cquery.message
        raidmode = is_in_raidmode(gid)

        asyncio.create_task(block_toggle_raidmode(gid))
        text = "Configuration of group " + callback_data["group_title"] 
        
        if raidmode:
            await deactivate_raidmode(gid, 0)
        else:
            await activate_raidmode(gid)
        menu = await get_raidmode_menu(gid, callback_data["group_title"])

        await message.edit_text(text, reply_markup=menu)
    await cquery.answer()


@dispatcher.callback_query_handler(bot_config_callback.filter(action="toggle_autoraid"))
async def auto_raidmode_menu_callback(cquery: CallbackQuery, callback_data: dict):
    gid = int(callback_data["gid"])

    if gid not in auto_raid_toggle_blocked:
        message = cquery.message
        auto_raid_mode = config.autoraid_enabled(gid)
        asyncio.create_task(block_toggle_raidmode(gid))
        text = "Configuration of group " + callback_data["group_title"] 

        if auto_raid_mode:
            config.disable_auto_raid(gid)
        else:
            config.enable_auto_raid(gid)

        menu = await get_raidmode_menu(gid, callback_data["group_title"])

        await message.edit_text(text, reply_markup=menu)
    await cquery.answer()

    
@dispatcher.callback_query_handler(bot_config_callback.filter(action="config_raidmode"))
async def raidmode_menu_callback(cquery: CallbackQuery, callback_data: dict) -> None:
    message = cquery.message

    text = "Configuration of group " + callback_data["group_title"] 
    menu = await get_raidmode_menu(int(callback_data['gid']), callback_data["group_title"])

    await cquery.answer()

    await message.edit_text(text, reply_markup=menu)


@dispatcher.callback_query_handler(bot_config_callback.filter(action="select_group"))
async def call_back(cquery: CallbackQuery, callback_data: dict) -> None:
    #query = update.callback_query
    #query.anwser()
    #callback_query.answer()
    
    gid = callback_data["gid"]
    chat = await bot.get_chat(gid)
    title = chat.title
    text = "Configuration of group " + title
    menu = InlineKeyboardMarkup(resize_keyboard=True)
    current_config[cquery.from_user.id] = callback_data["gid"]
    captcha_button = InlineKeyboardButton(
        "Captcha ✔",
        callback_data=bot_config_callback.new(
            action="config_captcha", gid=callback_data["gid"], group_title=""
        )
    )

    welcome_button = InlineKeyboardButton(
        "Willkommensnachricht 💬",
        callback_data=bot_config_callback.new(
            action="open_welcome_message_menu", gid=callback_data["gid"], group_title=""
        )
    )

    
    rules_button = InlineKeyboardButton(
        "Regeln 📜",
        callback_data=bot_config_callback.new(
            action="open_rules_menu", gid=callback_data["gid"], group_title=""
        )
    )

    
    warnings_button = InlineKeyboardButton(
        "Warnungen ⚠️",
        callback_data=bot_config_callback.new(
            action="open_warning_menu", gid=callback_data["gid"], group_title=""
        )
    )

    raidmode_button = InlineKeyboardButton(
        "Raid mode 🛡️ ",
        callback_data=bot_config_callback.new(
            action="config_raidmode", gid=callback_data["gid"], group_title=""
        )
    )

    log_button = InlineKeyboardButton(
        "Logging 🪵",
        callback_data=bot_config_callback.new(
            action="config_logging", gid=callback_data["gid"], group_title=""
        )
    )
    back_button = InlineKeyboardButton(
        "Close ❌",
        callback_data=single_callback.new(
            action="close"
        )
    )

    menu = menu.row(captcha_button, raidmode_button).row(welcome_button).row(warnings_button, rules_button).row(log_button).row(back_button)
    message = await cquery.message.edit_text(text, reply_markup=menu)
    await cquery.answer()


@dispatcher.message_handler(commands=["start"])
async def start_command(message: Message):
    menu = InlineKeyboardMarkup(resize_keyboard=True)

    reply = ""
    if "group" in message.chat.type:
        reply = "Das Konfigurationsmenü kannst du nur im privaten Chat öffnen!"
        chat = InlineKeyboardButton(
            "Chat öffnen",
            url=f"https://t.me/{botname}"
        )
        menu = menu.row(chat)
    else:
        reply = "Hello, %m!\n\nAdd me to your group and add me as an administrator to secure your group.\n\nNeed help? /help"

        gids =  config.get_privileged_user_groups(message.from_user.id)

        if len(gids) > 0:
            chats = await get_groups_by_ids(gids)
            buttons = []
            for chat in chats:
                chat = InlineKeyboardButton(
                    chat.title,
                    callback_data=bot_config_callback.new(action="select_group", gid=chat.id, group_title="")
                )
                #chat = InlineKeyboardButton(
                #    chat.title,
                #    callback_data=bot_config_callback.new(
                #            action="select_group", gid=chat.id, group_title=chat.title
                #        )
                #)
                menu = menu.row(chat)
        else:

            support = InlineKeyboardButton(
                        "Support 🛠",
                        url="https://t.me/"
                    )

            upgrade = InlineKeyboardButton(
                        "Upgrade 🌐",
                        url="https://t.me/"
                    )

            language = InlineKeyboardButton(
                        "Languages 🇬🇧",
                        url="https://t.me/"
                    )

            menu = InlineKeyboardMarkup(resize_keyboard=True).row(
                support, upgrade
            ).row(language)
    
    await bot.send_message(message.chat.id, reply.replace("%m", message.from_user.get_mention(as_html=True)), reply_markup=menu ,parse_mode=ParseMode.HTML)

@dispatcher.message_handler(commands=["configure"])
async def configure_command(message: Message):

    message = "<b>Group Settings</b>\n\nYou must be administrator of your group "

@dispatcher.message_handler(commands=["del"])
async def delete_command(message: Message):
    if config.is_user_privileged(message.chat.id, message['from']['id']):
        mfrom = message["from"]
        reply_msg = message["reply_to_message"]
        if reply_msg:
            message_id = reply_msg["message_id"]
            await bot.delete_message(message.chat.id, message_id)
        await message.delete()

@dispatcher.message_handler(RegexpCommandsFilter(regexp_commands=["."]))
async def remove_commands(message: Message):
    """Delete all commands"""
    await message.delete()

@dispatcher.message_handler(state=Form.welcome_text)
async def change_welcome_message(message: Message, state: FSMContext):
    uid = message.from_user.id
    text = message.text
    gid = current_config[message.from_user.id]

    await config.set_welcome_message(int(gid), text)
    await state.finish()
    await bot.send_message(uid, "Welcome message has been changed!")

if __name__ == "__main__":
    database.setup_database(DATABASE)
    conf = database.get_conf_from_db(DATABASE)

    print("1", conf)

    print("2", conf|CONFIG)
    print()
    config.setup({**conf, **CONFIG})

    loop = asyncio.get_event_loop()
    loop.create_task(setup_config_sync_task(60))
    # start polling
    executor.start_polling(dispatcher, skip_updates=cmd_args.skipupdates,allowed_updates=types.AllowedUpdates.all())
