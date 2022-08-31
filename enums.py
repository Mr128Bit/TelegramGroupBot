from enum import Enum

class MessageTemplate(Enum):
    CAPTCHA_TEMPLATE = "captcha_template"
    BUTTON_TEXT_TEMPLATE = "button_text_template"
    WELCOME_TEMPLATE = "welcome_template"
    WELCOME_CHANGED_TEMPLATE = "welcome_changed_template"
    ADD_BOT_AS_ADMIN_TEMPLATE = "add_bot_as_admin_template"
    OPEN_MENU_IN_PRIVATE_TEMPLATE = "open_menu_in_private_template"
    CAPTCHA_MENU_TEMPLTE = "captcha_menu_template"
    WELCOME_MSG_MENU_TEMPLATE = "welcome_msg_menu_template"
    RULES_MENU_TEMPLATE = "rules_menu_template"
    WARNINGS_MENU_TEMPLATE = "warnings_menu_template"
    FLOOD_MODE_MENU_TEMPLATE = "flood_mode_menu_template"
    LOGGING_MENU_TEMPLATE = "logging_menu_template"
    OPEN_CHAT_BUTTON_TEMPLATE = "open_chat_button_template"
    CLOSE_BUTTON_TEMPLATE = "close_button_template"
    CONFIG_MENU_HEADER_TEMPLATE = "config_menu_header_template"
    CONFIG_MENU_MODULE_HEADER_TEMPLATE = "config_menu_module_header_template"
    CONFIG_CAPTCHA_TYPE_HEADER_TEMPLATE = "config_captcha_type_header_template"
    CAPTCHA_TEXT_CHANGED_TEMPALTE = "captcha_text_changed_template"
    CAPTCHA_BUTTON_TEXT_CHANGED_TEMPALTE = "captcha_button_text_changed_template"


class Language(Enum):
    ENGLISH = "en"

class NextStep(Enum):
    CHANGE_CAPTCHA_TEXT = "CHANGE_CAPTCHA"
    CHANGE_BUTTON_TEXT = "CHANGE_BUTTON_TEXT"
    CHANGE_WELCOME_TEXT = "CHANGE_WELCOME_TEXT"
