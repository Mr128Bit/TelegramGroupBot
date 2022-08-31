from enum import Enum

class AdminPermission(Enum):
    CAN_MUTE = "CAN_MUTE"
    CAN_KICK = "CAN_KICK"
    CAN_DELETE = "CAN_DELETE"
    CAN_MODIFY_BOT = "CAN_MODIFY_BOT"
    CAN_PRIVILEGE_USER = "CAN_PRIVILEGE_USER"
