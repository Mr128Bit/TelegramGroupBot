from captcha import CaptchaType,CaptchaPunishment
from permissions import AdminPermission
from enums import *
from aiogram.utils.exceptions import (
    BotKicked,
    ChatNotFound
)

CONFIG = {}

def setup(config):
    global CONFIG
    CONFIG = config

def get():
    return CONFIG

def get_bot_hash():
    return CONFIG["bot_hash"]

def is_bot_owner(uid):
    if uid in CONFIG["bot_owner"]:
        return True

    return False

async def get_autoraid_treshold(gid):
    return CONFIG["groups"][gid]["auto_raid_treshold"]

async def setup_group(gid, uid):
    print(CONFIG)

    lang = Language.ENGLISH.value

    CONFIG["groups"][gid] = {
            "is_pro" : False,
            "privileged": [uid],
            "auto_raid_treshold": 20,
            "auto_raid_detection": True,
            "log_channel" : 0,
            "log_commands": False,
            "log_raid_status": False,
            "log_active": False,
            "log_join": False,
            "log_leave": False,
            "updated" : False,
            "created" : True,
            "captcha_active": True,
            "captcha_type": CaptchaType.SIMPLE,
            "captcha_punishment": CaptchaPunishment.KICK.value,
            "captcha_punishment_time": 0,
            "welcome_active": True,
            "captcha_text": CONFIG["message_templates"][lang]["captcha_template"],
            "captcha_button_text": CONFIG["message_templates"][lang]["button_text_template"],
            "welcome_text": CONFIG["message_templates"][lang]["welcome_template"],
            "privileges_updated" : False,
            "bot_kicked": False
    }

async def is_group_registered(gid):
    if CONFIG["groups"].get(gid):
        return True

    return False

def is_user_privileged(gid, uid):
    """
    Returns wether a user is privileged for this bot in a specific group

        Parameters:
            gid (int): Group ID
            uid (int): User ID

        Returns:
            (bool)
    """
    if gid in CONFIG["groups"] and uid in CONFIG["groups"][gid]["privileged"]:
        return True
    is_owner = is_bot_owner(uid)
    if is_owner:
        return True    
    
    return False

def get_groups():
    return CONFIG["groups"]

def get_log_channel(gid):
    return CONFIG["groups"][gid]["log_channel"]

def set_log_channel(gid, chat_id):
    CONFIG["groups"][gid]["log_channel"] = chat_id

def toggle_captcha(gid):
    captcha_active = CONFIG["groups"][gid]["captcha_active"]
    if captcha_active:
        CONFIG["groups"][gid]["captcha_active"] = False
    else:
        CONFIG["groups"][gid]["captcha_active"] = True

def set_captcha_type(gid, captcha_type):
    CONFIG["groups"][gid]["captcha_type"] = captcha_type

def set_captcha_punishment(gid, punishment):
    CONFIG["groups"][gid]["captcha_punishment"] = punishment

def captcha_enabled(gid):
    return CONFIG["groups"][gid]["captcha_active"]


def get_captcha_text(gid):
    return CONFIG["groups"][gid]["captcha_type"]

def get_captcha_type(gid):
    return CONFIG["groups"][gid]["captcha_type"]

def get_captcha_button_text(gid):
    return CONFIG["groups"][gid]["captcha_button_text"]

def get_captcha_punishment(gid):
    return CaptchaPunishment(int(CONFIG["groups"][gid]["captcha_punishment"]))


def get_privileged_user_groups(uid):
    groups = []
    for group in get_groups():
        if uid in CONFIG["groups"][group]["privileged"]:
            groups.append(group)
    return groups

async def get_welcome_message(gid):
    return CONFIG["groups"][gid]["welcome_text"]

async def set_welcome_message(gid, text):
    CONFIG["groups"][gid]["welcome_text"] = text
    await update_config_change(gid)

async def set_captcha_text(gid, text):
    CONFIG["groups"][gid]["captcha_text"] = text
    await update_config_change(gid)

async def set_captcha_button_text(gid, text):
    CONFIG["groups"][gid]["captcha_button_text"] = text
    await update_config_change(gid)

async def update_config_change(gid):
    CONFIG["groups"][gid]["updated"] = True

def privilege_user(gid, uid):
    pass

async def unprivilege_user(gid, uid):
    privileged = CONFIG["groups"][gid]["privileged"]
    if userid in privileged:
        del privileged[userid]
        CONFIG["groups"][gid]["privileges_updated"] = True

async def add_user_privileges(userid, gid, permissions):
    privileged = CONFIG["groups"][gid]["privileged"]

    if userid not in privileged:
        privileged[userid] = []
    for per in permissions:
        try:
            permission = None
            if isinstance(per, str):
                permission = AdminPermission(per)
            elif isinstance(per, AdminPermission):
                permission = per
            else:
                return
            privileged[userid].append(permission)
            CONFIG["groups"][gid]["privileges_updated"] = True
            print(CONFIG["groups"][gid])
        except ValueError:
            pass


async def remove_privilege(userid, gid, permission: AdminPermission):
    privileged = CONFIG["groups"][gid]["privileged"]
    if permission in privileged[userid]:
        privileged[userid].remove(permission)


def is_pro(gid):
    pass

def enable_auto_raid(gid):
    CONFIG["groups"][gid]["auto_raid_detection"] = True

def disable_auto_raid(gid):
    CONFIG["groups"][gid]["auto_raid_detection"] = False

def autoraid_enabled(gid):
    return CONFIG["groups"][gid]["auto_raid_detection"]

def get_log_channel(gid):
    pass

def get_welcome_message(gid):
    pass

def is_welcome_active(gid):
    return CONFIG["groups"][gid]["welcome_active"]

def set_bot_kicked(gid):
    CONFIG["groups"][gid]["bot_kicked"] = True

def auto_raid_enabled(gid):
    if CONFIG["groups"][int(gid)]["auto_raid_detection"]:
        return True
    return False

def toggle_welcome(gid):
    if CONFIG["groups"][gid]["welcome_active"]:
        CONFIG["groups"][gid]["welcome_active"] = False
    else:
        CONFIG["groups"][gid]["welcome_active"] = True
