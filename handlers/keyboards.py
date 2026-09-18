from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from services.get_correct_time import get_correct_time
from services.google_calendar_service import build_google_auth_url
from handlers.answer_texts.TEXT import get_text
from logger_config import logger

db = None

def add_back_button(keyboard: InlineKeyboardMarkup, tg_id=None) -> InlineKeyboardMarkup:
    text_back = get_text(key="back_btn", tg_id=tg_id, db=db)  # используй свой ключ
    # Преобразуем в список списков
    new_inline_keyboard = keyboard.inline_keyboard.copy()
    new_inline_keyboard.append([InlineKeyboardButton(text=text_back, callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=new_inline_keyboard)

def get_support_inline_keyboard(tg_id = None):
    text_support_btn = get_text(key = "support_btn", tg_id = tg_id, db=db)
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text_support_btn,url = "https://t.me/pipipopy2")]
        ]
    )
    return add_back_button(inline_keyboard, tg_id=tg_id)

def get_documents_inline_keyboard(tg_id = None):
    text_terms_of_service = get_text(key = "terms_of_service_text", tg_id = tg_id, db=db)
    text_privacy_policy = get_text(key = "privacy_policy_text", tg_id = tg_id, db=db)
    link_terms_of_service = get_text(key = "terms_of_service_link", tg_id = tg_id, db=db)
    link_privacy_policy = get_text(key = "privacy_policy_link", tg_id = tg_id, db=db)

    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
        [InlineKeyboardButton(text=text_terms_of_service, url=link_terms_of_service), 
         InlineKeyboardButton(text=text_privacy_policy, url=link_privacy_policy)]
        ]
    )
    return add_back_button(inline_keyboard, tg_id=tg_id)
def get_settings_inline_keyboard(tg_id = None):
    text_change_language = get_text(key = "change_language", tg_id = tg_id, db=db)
    text_update_notifications_btn = get_text(key = "update_notifications_btn", tg_id = tg_id, db=db)
    text_update_time_btn = get_text(key = "update_time_btn", tg_id = tg_id, db=db)
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text_update_time_btn, callback_data="update_time")],
            [InlineKeyboardButton(text=text_update_notifications_btn, callback_data="update_notifications")],
            [InlineKeyboardButton(text=text_change_language, callback_data="change_language")]
        ]
    )
    return add_back_button(inline_keyboard, tg_id=tg_id)
def get_register_inline_keyboard(is_admin=False, tg_id=None):
    text_what_is_kalendator = get_text(key="what_is_kalendator", tg_id=tg_id, db=db)
    text_connect_calendars = get_text(key="connect_calendars", tg_id=tg_id, db=db)
    text_support_btn = get_text(key="support_btn", tg_id=tg_id, db=db)
    text_admin_panel_btn = get_text(key="admin_panel_btn", tg_id=tg_id, db=db)
    text_settings_btn = get_text(key="settings_btn", tg_id=tg_id, db=db)
    text_documents_btn = get_text(key="documents_btn", tg_id=tg_id, db=db)
    text_manage_subscription = get_text(key="manage_subscription", tg_id=tg_id, db=db)

    buttons = [
        [InlineKeyboardButton(text=text_what_is_kalendator, callback_data="first_info")],
        [InlineKeyboardButton(text=text_manage_subscription, callback_data="manage_subscription")],
        [InlineKeyboardButton(text=text_settings_btn, callback_data="settings")],
        [InlineKeyboardButton(text=text_documents_btn, callback_data="documents")],
        [InlineKeyboardButton(text=text_connect_calendars, callback_data="calendars_setup")],
        [InlineKeyboardButton(text=text_support_btn, callback_data="support")],
        
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text=text_admin_panel_btn, callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_time_inline_keyboard(page=3, tg_id=None):
    ITEMS_PER_PAGE = 5

    times = get_correct_time()

    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE

    current_times = times[start:end]
    text_back_btn = get_text(key="prev_page_btn", tg_id=tg_id, db=db)
    text_forward_btn = get_text(key="next_page_btn", tg_id=tg_id, db=db)

    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=o["local_time"],
                callback_data=f"timezone:{o['offset']}"
            )
        ]
        for o in current_times
    ]

    nav_buttons = []

    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text=text_back_btn,
                callback_data=f"page:{page-1}"
            )
        )
    if end < len(times):
        nav_buttons.append(
            InlineKeyboardButton(
                text=text_forward_btn,
                callback_data=f"page:{page+1}"
            )
        )

    if nav_buttons:
        inline_keyboard.append(nav_buttons)

    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    return keyboard
def get_time_inline_keyboard_with_back(page=3, tg_id=None):
    keyboard = get_time_inline_keyboard(page=page, tg_id=tg_id)
    return add_back_button(keyboard, tg_id=tg_id)

def get_delete_inline_keyboard(tg_id=None):
    text_delete_data_btn = get_text(key = "delete_data_btn", tg_id = tg_id, db=db)
    text_cancel_delete_btn = get_text(key = "cancel_delete_btn", tg_id = tg_id, db=db)
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text_delete_data_btn, callback_data="delete_data")],
            [InlineKeyboardButton(text=text_cancel_delete_btn, callback_data="cancel_delete")],
        ]
    )
    return inline_keyboard

def get_update_notifications_inline_keyboard(tg_id=None):
    text_yes_btn = get_text(key = "yes_btn", tg_id = tg_id, db=db)
    text_no_btn = get_text(key = "no_btn", tg_id = tg_id, db=db)
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text_yes_btn, callback_data="yes_update_notifications"), InlineKeyboardButton(text=text_no_btn, callback_data="no_update_notifications")]
        ]
    )
    return add_back_button(inline_keyboard, tg_id=tg_id)

def get_admin_inline_keyboard(tg_id=None):
    text_admin_broadcast_btn = get_text(key = "admin_broadcast_btn", tg_id = tg_id, db=db)
    text_admin_status_services = get_text(key = "admin_status_services", tg_id = tg_id, db=db)
    text_admin_future_btn = get_text(key = "admin_future_btn", tg_id = tg_id, db=db)


    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text_admin_broadcast_btn, callback_data="admin_update_notification")],
            [InlineKeyboardButton(text=text_admin_status_services, callback_data="services_status")],
            [InlineKeyboardButton(text=text_admin_future_btn, callback_data="passing")]
             
        ]
    )
    return add_back_button(inline_keyboard, tg_id=tg_id)

def get_calendars_inline_keyboard(tg_id=None):
    text_google_calendar_btn = get_text(key = "google_calendar_btn", tg_id = tg_id, db=db)
    text_apple_calendar_btn = get_text(key = "apple_calendar_btn", tg_id = tg_id, db=db)

    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text_google_calendar_btn, callback_data="google_calendar"), 
             InlineKeyboardButton(text=text_apple_calendar_btn, callback_data="apple_calendar")]
             ]
    )
    return add_back_button(inline_keyboard, tg_id=tg_id)

def get_inline_apple_app_specific_password_link(tg_id=None):
    text_app_specific_password_link = get_text(key = "apple_password_link", tg_id = tg_id, db=db)
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text_app_specific_password_link, url="https://account.apple.com")]
        ]
    )
    return add_back_button(inline_keyboard, tg_id=tg_id)

def get_inline_google_app_specific_password_link(tg_id=None):
    text_app_specific_password_link = get_text(key="google_password_link", tg_id=tg_id, db=db)  
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text_app_specific_password_link, url="https://myaccount.google.com/apppasswords")]
        ]
    )
    return add_back_button(inline_keyboard, tg_id=tg_id)

def get_inline_google_authorization(user_id, tg_id=None):
    
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[ 
            #[InlineKeyboardButton(text=text_google_specific_password_auth, callback_data="google_specific_password_auth")]-app-specific-passwoed
        ]
    )
    return add_back_button(inline_keyboard, tg_id=tg_id)

def get_inline_language_keyborad(tg_id=None):
    text_russian = get_text(key = "russian_language", tg_id = tg_id, db=db)
    text_english = get_text(key = "english_language", tg_id = tg_id, db=db)
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text_russian, callback_data="russian_language"), 
             InlineKeyboardButton(text=text_english, callback_data="english_language")]
             ]
    )
    return add_back_button(inline_keyboard, tg_id=tg_id)
def get_recconect_disconnect_calendar_keyboard(provider, tg_id=None):
    text_reconnect = get_text(key = "reconnect_calendar", tg_id = tg_id, db=db)
    text_disconnect = get_text(key = "disconnect_calendar", tg_id = tg_id, db=db)
    if provider == "google":
        inline_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=text_reconnect, callback_data="reconnect_google_calendar"), 
                InlineKeyboardButton(text=text_disconnect, callback_data="disconnect_google_calendar")]
                ]
        )
    elif provider == "apple":
        inline_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=text_reconnect, callback_data="reconnect_apple_calendar"), 
                InlineKeyboardButton(text=text_disconnect, callback_data="disconnect_apple_calendar")]
                ]
        )
    return add_back_button(inline_keyboard, tg_id=tg_id)