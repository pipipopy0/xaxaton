import asyncio
import os
import aiohttp

from forms.calendar_fsm import CalendarStates

from maxapi import Router, F
from maxapi.context import MemoryContext
from maxapi.types import MessageCallback, CallbackButton, InputMedia
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from handlers.answer_texts.TEXT import get_text
from handlers.router import ADMINS
from services.payment_service import (
    create_first_payment,
    create_auto_payment
)
from services.access import is_pro_user
from logger_config import logger
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from services.google_calendar_service import request_device_code
#from monitor.status import get_full_status, format_status
from handlers.keyboards import (get_admin_inline_keyboard, 
                                get_calendars_inline_keyboard, 
                                get_time_inline_keyboard,
                                get_support_inline_keyboard,
                                get_update_notifications_inline_keyboard,
                                get_inline_google_authorization,
                                get_inline_language_keyborad,
                                get_recconect_disconnect_calendar_keyboard,
                                get_settings_inline_keyboard,
                                get_documents_inline_keyboard,
                                get_register_inline_keyboard,
                                get_time_inline_keyboard_with_back,
                                add_back_button)

WORLD_TIMEZONES = {
    -12: "Pacific/Kwajalein",
    -11: "Pacific/Niue",
    -10: "Pacific/Honolulu",
    -9: "America/Anchorage",
    -8: "America/Los_Angeles",
    -7: "America/Phoenix",
    -6: "America/Guatemala",
    -5: "America/Bogota",
    -4: "America/Caracas",
    -3: "America/Buenos_Aires",
    -2: "America/Noronha",
    -1: "Atlantic/Cape_Verde",
    0: "Etc/UTC",
    1: "Africa/Lagos",
    2: "Europe/Kaliningrad",
    3: "Europe/Moscow",
    4: "Europe/Samara",
    5: "Asia/Yekaterinburg",
    6: "Asia/Omsk",
    7: "Asia/Krasnoyarsk",
    8: "Asia/Irkutsk",
    9: "Asia/Yakutsk",
    10: "Asia/Vladivostok",
    11: "Asia/Magadan",
    12: "Asia/Kamchatka"
}

CLIENT_GOOGLE_ID = os.getenv("CLIENT_GOOGLE_ID")
CLIENT_GOOGLE_SECRET = os.getenv("CLIENT_GOOGLE_SECRET")
TOKEN_URI = os.getenv("TOKEN_URI")

waiting_for_time_message = {}

callback_router = Router()
db = None

async def push_menu(context: MemoryContext, menu_name: str):
    data = await context.get_data()
    history = data.get("history", [])
    history.append(menu_name)
    await context.update_data(history=history)

async def pop_menu(context: MemoryContext) -> str | None:

    data = await context.get_data()
    history = data.get("history", [])
    if not history:
        return None
    return history.pop()

async def poll_device_token(device_code_data, user_id, max_id, callback):
    device_code = device_code_data["device_code"]
    interval = device_code_data["interval"]
    expires_at = datetime.utcnow() + timedelta(
        seconds=device_code_data["expires_in"]
    )

    async with aiohttp.ClientSession() as session:
        while datetime.utcnow() < expires_at:
            await asyncio.sleep(interval)

            data = {
                "client_id": CLIENT_GOOGLE_ID,
                "client_secret": CLIENT_GOOGLE_SECRET,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            }

            try:
                async with session.post(TOKEN_URI, data=data) as response:
                    tokens = await response.json()

            except aiohttp.ClientError as e:
                logger.error(f"Google OAuth request error: {e}")
                return

            error = tokens.get("error")

            if error == "authorization_pending":
                continue

            elif error == "slow_down":
                interval += 5
                continue

            elif error == "access_denied":
                text = get_text(key="google_calendar_access_denied", max_id=max_id, db=db )
                await callback.message.answer(text=text)
                return

            elif error == "expired_token":
                text = get_text(key="google_calendar_expired_token", max_id=max_id, db=db)
                await callback.message.answer(text=text)
                return

            elif error:
                logger.error(f"Device flow error: {tokens}")
                return

            refresh_token = tokens.get("refresh_token")

            if refresh_token:
                existing = db.select_data(
                    "users_authorizations",
                    columns=["id"],
                    where_conditions={"user_id": user_id},
                )

                if existing:
                    db.update_data(
                        "users_authorizations",
                        {"google_calendar_refresh_token": refresh_token},
                        where_conditions={"user_id": user_id},
                    )
                else:
                    db.insert_data(
                        "users_authorizations",
                        {
                            "user_id": user_id,
                            "google_calendar_refresh_token": refresh_token,
                        },
                    )

                await callback.message.answer("Google Calendar подключён!")

            return

async def show_menu(menu_name: str, callback: MessageCallback, context: MemoryContext):
    max_id = callback.from_user.user_id

    # ========== ГЛАВНОЕ МЕНЮ ==========
    if menu_name == "main":
        text = get_text(key="start_registered", max_id=max_id, db=db)
        keyboard = get_register_inline_keyboard(
            is_admin=callback.from_user.user_id in ADMINS,
            max_id=max_id
        )
        await replace_menu(callback, text, keyboard)

    # ========== НАСТРОЙКИ ==========
    elif menu_name == "settings":
        text = get_text(key="settings_menu", max_id=max_id, db=db)
        keyboard = get_settings_inline_keyboard(max_id=max_id)
        await replace_menu(callback, text, keyboard)

    # ========== ДОКУМЕНТЫ ==========
    elif menu_name == "documents":
        text = get_text(key="documents_menu", max_id=max_id, db=db)
        keyboard = get_documents_inline_keyboard(max_id=max_id)
        await replace_menu(callback, text, keyboard)

    # ========== ПОДКЛЮЧЕНИЕ КАЛЕНДАРЕЙ ==========
    elif menu_name == "calendars_setup":
        text = get_text(key="calendars_setup", max_id=max_id, db=db)
        keyboard = get_calendars_inline_keyboard(max_id=max_id)
        await replace_menu(callback, text, keyboard)

    # ========== APPLE КАЛЕНДАРЬ (с проверкой) ==========
    elif menu_name == "apple_calendar":
        users = db.select_data("users", where_conditions={"user_id":max_id})
        if not users:
            text = get_text(key="user_not_found", max_id=max_id, db=db)
            await callback.message.edit(text=text)
            return

        user_id = users[0][0]
        auth = db.select_data("users_authorizations", where_conditions={"user_id" : user_id})
        is_connected = False
        if auth:
            row = auth[0]
            if len(row) > 4 and row[2] and row[4]:
                is_connected = True

        if is_connected:
            text = get_text(key="apple_calendar_activated_already", max_id=max_id, db=db)
            keyboard = get_recconect_disconnect_calendar_keyboard(provider="apple", max_id=max_id)
            await replace_menu(callback, text, keyboard)
        else:
            await callback.message.delete()
            text = get_text(key="apple_email_prompt", max_id=max_id, db=db)
            apple_instruction_text = get_text(
                            key="apple_calendar_instructions",
                            max_id=max_id,
                            db=db
                        )
            media = [
                InputMedia(path=("media/instructions/apple/1.png")),
                InputMedia(path=("media/instructions/apple/2.png")),
                InputMedia(path=("media/instructions/apple/3.png")),
                InputMedia(path=("media/instructions/apple/4.png")),
                InputMedia(path=("media/instructions/apple/5.png")),
                InputMedia(path=("media/instructions/apple/6.png"))
            ]
            await callback.message.answer(text=apple_instruction_text, attachments=media)

            await context.update_data(provider="apple")
            await callback.message.answer(text)
            await context.set_state(CalendarStates.waiting_email)

    # ========== GOOGLE КАЛЕНДАРЬ (с проверкой) ==========
    elif menu_name == "google_calendar":
        users = db.select_data("users", where_conditions={"user_id":max_id})
        if not users:
            text = get_text(key="user_not_found", max_id=max_id, db=db)
            await callback.message.edit(text=text)
            return

        user_id = users[0][0]
        authorizations = db.select_data("users_authorizations", where_conditions={"user_id" : user_id})
        is_connected = False
        if authorizations:
            row = authorizations[0]
            if len(row) > 8 and row[8] is not None:
                is_connected = True

        if is_connected:
            text = get_text(key="google_calendar_activated_already", max_id=max_id, db=db)
            keyboard = get_recconect_disconnect_calendar_keyboard(provider="google", max_id=max_id)
            await replace_menu(callback, text, keyboard)
        else:
            await callback.message.delete()
            text = get_text(
                            key="google_calendar_oauth",
                            max_id=max_id,
                            db=db
                        )
            google_instruction_text = get_text(
                key="google_calendar_instructions",
                max_id=max_id,
                db=db
            )
            media = [
                InputMedia(path=("media/instructions/google/1.png")),
                InputMedia(path=("media/instructions/google/2.png")),
                InputMedia(path=("media/instructions/google/3.png")), 
            ]
            await callback.message.answer(text=google_instruction_text, attachments=media)

            device_code_data = request_device_code(user_id=user_id)
            db.insert_data(
                "oauth_devices",
                {
                    "device_code": device_code_data.get("device_code"),
                    "user_code": device_code_data.get("user_code"),
                    "user_id": user_id,
                    "provider": "google"
                }
            )

            text = get_text(key="google_calendar_oauth", max_id=max_id, db=db)
            text = text.format(
                url=device_code_data["verification_url"],
                code=device_code_data["user_code"],
            )

            keyboard = get_inline_google_authorization(
                user_id=user_id,
                max_id=max_id
            )

            await callback.message.answer(text, attachments=[keyboard])

            asyncio.create_task(poll_device_token(device_code_data, user_id, max_id, callback))


    # ========== ВЫБОР ЧАСОВОГО ПОЯСА ==========
    elif menu_name == "timezone":
        text = get_text(key="timezone_setup", max_id=max_id, db=db)
        keyboard = get_time_inline_keyboard_with_back(max_id=max_id)   # с кнопкой «Назад»
        await replace_menu(callback, text, keyboard)

    # ========== ПОДДЕРЖКА ==========
    elif menu_name == "support":
        text = get_text(key="support", max_id=max_id, db=db)
        keyboard = get_support_inline_keyboard(max_id=max_id)
        await replace_menu(callback, text, keyboard)

    # ========== АДМИН-ПАНЕЛЬ ==========
    elif menu_name == "admin_panel":
        text = get_text(key="admin_panel", max_id=max_id, db=db)
        keyboard = get_admin_inline_keyboard(max_id=max_id)
        await replace_menu(callback, text, keyboard)

    # ========== УВЕДОМЛЕНИЯ (настройка) ==========
    elif menu_name == "update_notifications":
        text = get_text(key="update_notifications", max_id=max_id, db=db)
        keyboard = get_update_notifications_inline_keyboard(max_id=max_id)
        await replace_menu(callback, text, keyboard)

    # ========== СМЕНА ЯЗЫКА ==========
    elif menu_name == "change_language":
        text = get_text(key="select_language", max_id=max_id, db=db)
        keyboard = get_inline_language_keyborad(max_id=max_id)
        await replace_menu(callback, text, keyboard)

    # ========== ПЕРВАЯ ИНФОРМАЦИЯ (что такое Календатор) ==========
    elif menu_name == "first_info":
        text = get_text(key="first_info", max_id=max_id, db=db)
        keyboard = get_support_inline_keyboard(max_id=max_id)
        await replace_menu(callback, text, keyboard)


    # ========== ЕСЛИ ИМЯ НЕ РАСПОЗНАНО – ПОКАЗЫВАЕМ ГЛАВНОЕ ==========
    else:
        text = get_text(key="say_hello", max_id=max_id, db=db)
        await callback.message.answer(text=text)
        # text = get_text(key="start_registered", max_id=max_id, db=db)
        # keyboard = get_register_inline_keyboard(
        #     is_admin=callback.from_user.user_id in ADMINS,
        #     max_id=max_id
        # )
        # await replace_menu(callback, text, keyboard)



@callback_router.message_callback(F.callback.payload == "first_info")
async def process_first_info(callback: MessageCallback, context: MemoryContext):
    await push_menu(context, "main")
    await show_menu("first_info", callback, context)

@callback_router.message_callback(F.callback.payload == "support")
async def process_support(callback: MessageCallback, context: MemoryContext):
    await push_menu(context, "main") 
    await show_menu("support", callback, context)

@callback_router.message_callback(F.callback.payload == "update_time")
async def process_update_time(callback: MessageCallback, context: MemoryContext):
    await push_menu(context, "settings")
    await context.update_data(from_settings=True)
    await show_menu("timezone", callback, context)
    
@callback_router.message_callback(F.callback.payload == "delete_data")
async def process_delete_data(callback: MessageCallback):
    max_id = callback.from_user.user_id
    
    user = db.select_data("users", where_conditions={"user_id":max_id})
    if user[0][0]:
        user_id = user[0][0]
        db.delete_data("users_costs", where_conditions={"user_id" : user_id})
        db.delete_data("users", where_conditions={"user_id":max_id})

    text = get_text(key = "delete_success", max_id = callback.from_user.user_id, db=db)
    await callback.message.answer(text)

@callback_router.message_callback(F.callback.payload == "cancel_delete")
async def process_cancel_delete(callback: MessageCallback):
    text = get_text(key = "delete_cancel", max_id = callback.from_user.user_id, db=db)
    await callback.message.answer(text)

@callback_router.message_callback(F.callback.payload.startswith("timezone:"))
async def process_timezone_page(callback: MessageCallback, context: MemoryContext):
    offset = int(callback.callback.payload.split(":")[1])
    offset_string = WORLD_TIMEZONES[offset]
    max_id = callback.from_user.user_id

    db.update_data(
        table_name="users",
        data={"timezone_offset": offset_string},
        where_conditions={"user_id": max_id}
    )

    await context.update_data(from_settings=False)

    text = get_text(key="timezone_set", max_id=max_id, db=db)
    text = text.format(offset=offset)

    await callback.message.answer(text)

    

@callback_router.message_callback(F.callback.payload.startswith("page:"))
async def process_time_page(callback: MessageCallback, context: MemoryContext):
    page = int(callback.callback.payload.split(":")[1])
    max_id = callback.from_user.user_id
    data = await context.get_data()
    if data.get("from_settings"):
        new_markup = get_time_inline_keyboard_with_back(page=page, max_id=max_id)
    else:
        new_markup = get_time_inline_keyboard(page=page,max_id=max_id)
    try:
        await callback.answer(attachments=[new_markup])
    except Exception as e:
        logger.error(f"Error updating inline keyboard: {e}")
    # 

@callback_router.message_callback(F.callback.payload == "update_notifications")
async def process_update_notifications(callback: MessageCallback, context: MemoryContext):
    await push_menu(context, "settings")
    await show_menu("update_notifications", callback, context)

@callback_router.message_callback(F.callback.payload == "yes_update_notifications")
async def process_yes_update_notifications(callback: MessageCallback):
    waiting_for_time_message[callback.from_user.user_id] = True
    text = get_text(key = "notification_time_prompt", max_id = callback.from_user.user_id, db=db)
    await callback.message.answer(text)

@callback_router.message_callback(F.callback.payload == "no_update_notifications")
async def process_no_update_notifications(callback: MessageCallback):
    max_id = callback.from_user.user_id
    db.update_data(
        table_name="users",
        data={"notification_time": None},
        where_conditions={"user_id":max_id}
    )
    text = get_text(key = "notification_time_set", max_id = callback.from_user.user_id, db=db)
    await callback.message.answer(text)
    

@callback_router.message_callback(F.callback.payload == "settings")
async def process_settings_menu(callback: MessageCallback, context: MemoryContext):
    await push_menu(context, "main")
    await show_menu("settings", callback, context)

@callback_router.message_callback(F.callback.payload == "documents")
async def process_documents_menu(callback: MessageCallback, context: MemoryContext):
    await push_menu(context, "main")
    await show_menu("documents", callback, context)

@callback_router.message_callback(F.callback.payload == "admin_panel")
async def process_admin_panel(callback: MessageCallback, context: MemoryContext):
    await push_menu(context, "main") 
    await show_menu("admin_panel", callback, context)

@callback_router.message_callback(F.callback.payload == "admin_update_notification")
async def process_admin_update_notification(callback: MessageCallback):
    if callback.from_user.user_id not in ADMINS:
        text = get_text(key = "admin_no_permission", max_id = callback.from_user.user_id, db=db)
        await callback.message.answer(text)
        
        return
    waiting_for_broadcast.add(callback.from_user.user_id)
    text = get_text(key = "admin_broadcast_prompt", max_id = callback.from_user.user_id, db=db)
    await callback.message.answer(text)
    
#@callback_router.message_callback(F.callback.payload == "services_status")
#async def process_admin_status_services(callback: MessageCallback):
    # status = get_full_status()
    # text = format_status(status)
    #await callback.message.answer(text)
    
    #return
@callback_router.message_callback(F.callback.payload == "calendars_setup")
async def process_calendars_setup(callback: MessageCallback, context: MemoryContext):
    max_id = callback.from_user.user_id

    user = db.select_data(
        "users",
        where_conditions={"user_id": max_id}
    )

    if not user:
        await callback.answer(
            "Ошибка: пользователь не найден",
            
        )
        return

    await push_menu(context, "main")
    await show_menu("calendars_setup", callback, context)
@callback_router.message_callback(F.callback.payload == "apple_calendar")
async def process_apple_calendar(callback: MessageCallback, context: MemoryContext):
    await push_menu(context, "calendars_setup")
    await show_menu("apple_calendar", callback, context)
@callback_router.message_callback(F.callback.payload.startswith("google_specific_password_auth"))
async def process_google_calendar_spec_pass_setup(callback: MessageCallback, context: MemoryContext):
    text = get_text(key = "google_email_prompt", max_id = callback.from_user.user_id, db=db)
    await context.update_data(provider="google")
    await callback.message.answer(text)
    await context.set_state(CalendarStates.waiting_email)
    
@callback_router.message_callback(F.callback.payload.startswith("google_calendar"))
async def process_google_calendar_setup(callback: MessageCallback, context: MemoryContext):
    await push_menu(context, "calendars_setup")
    await show_menu("google_calendar", callback, context)
@callback_router.message_callback(F.callback.payload.startswith("change_language"))
async def process_change_language(callback: MessageCallback, context: MemoryContext):
    await push_menu(context, "settings")
    await show_menu("change_language", callback, context)
@callback_router.message_callback(F.callback.payload.startswith("russian_language"))
async def process_russian_language(callback: MessageCallback):
    max_id = callback.from_user.user_id
    try:
        db.update_data(
            table_name="users",
            data={"language": "ru"},
            where_conditions={"user_id":max_id}
        )
        text = get_text(key = "language_changed_ru", max_id = callback.from_user.user_id, db=db)
        await callback.message.answer(text)
    except Exception as e:
        logger.error(f"Error updating language for user {max_id}: {e}")
        text = get_text(key = "language_change_error", max_id = callback.from_user.user_id, db=db)
        await callback.message.answer(text)
    
@callback_router.message_callback(F.callback.payload.startswith("english_language"))
async def process_english_language(callback: MessageCallback):

    max_id = callback.from_user.user_id

    try:
        db.update_data(
            table_name="users",
            data={"language": "en"},
            where_conditions={"user_id":max_id}
        )
        text = get_text(key = "language_changed_en", max_id = callback.from_user.user_id, db=db)
        await callback.message.answer(text)
    except Exception as e:
        logger.error(f"Error updating language for user {max_id}: {e}")
        text = get_text(key = "language_change_error", max_id = callback.from_user.user_id, db=db)
        await callback.message.answer(text)
    
@callback_router.message_callback(F.callback.payload.startswith("reconnect_google_calendar"))
async def reconnect_google_calendar(callback: MessageCallback, context: MemoryContext):
    await push_menu(context, "google_calendar")
    max_id = callback.from_user.user_id
    user = db.select_data("users", where_conditions={"user_id":max_id})
    user_id = user[0][0]

    text = get_text(
    key="google_calendar_oauth",
    max_id=max_id,
    db=db
)

    keyboard = get_inline_google_authorization(
        user_id=user_id,
        max_id=max_id
    )

    google_url = keyboard.inline_keyboard[0][0].url

    text = text.format(url=google_url)

    await callback.message.edit(text)
    
@callback_router.message_callback(F.callback.payload == "disconnect_google_calendar")
async def disconnect_google_calendar(callback: MessageCallback):
    max_id = callback.from_user.user_id
    user = db.select_data("users", where_conditions={"user_id" : max_id})
    if not user:
        await callback.answer("Ошибка: пользователь не найден")
        return
    user_id = user[0][0]

    db.update_data(
        table_name="users_authorizations",
        data={
            "google_calendar_email": None,
            "google_calendar_password": None,
            "google_calendar_url": None,
            "google_calendar_refresh_token": None
        },
        where_conditions={"user_id" : user_id}
    )

    text = get_text(key="calendar_disconnected", max_id=max_id, db=db)
    await callback.message.answer(text)
    
@callback_router.message_callback(F.callback.payload == "reconnect_apple_calendar")
async def reconnect_apple_calendar(callback: MessageCallback, context: MemoryContext):
    await push_menu(context, "apple_calendar")  
    max_id = callback.from_user.user_id
    user = db.select_data("users", where_conditions={"user_id":max_id})
    if not user:
        await callback.answer("Ошибка")
        return
    user_id = user[0][0]
    db.update_data(
        table_name="users_authorizations",
        data={
            "apple_calendar_email": None,
            "apple_calendar_password": None,
            "apple_calendar_url": None
        },
        where_conditions={"user_id" : user_id}
    )
    text = get_text(key="apple_email_prompt", max_id=max_id, db=db)
    await context.update_data(provider="apple")
    await callback.message.edit(text)
    await context.set_state(CalendarStates.waiting_email)
    
    
@callback_router.message_callback(F.callback.payload.startswith("disconnect_apple_calendar"))
async def disconnect_apple_calendar(callback: MessageCallback):
    max_id = callback.from_user.user_id
    user = db.select_data("users", where_conditions={"user_id":max_id})
    user_id = user[0][0]
    db.update_data(table_name="users_authorizations",
    
    data={
        "apple_calendar_email": None,
        "apple_calendar_password": None,
        "apple_calendar_url": None
    },
    where_conditions={"user_id" : user_id}
    )
    text = get_text(key = "calendar_disconnected", max_id = callback.from_user.user_id, db=db)
    
    await callback.message.answer(text)
    

@callback_router.message_callback(F.callback.payload == "back")
async def process_back(callback: MessageCallback, context: MemoryContext):
    current_state = await context.get_state()
    if current_state in (CalendarStates.waiting_email, CalendarStates.waiting_password):
        await context.clear()
        prev = await pop_menu(context)
        if prev:
            await show_menu(prev, callback, context)
        else:
            await show_menu("main", callback, context)
        
        return

    prev = await pop_menu(context)
    if prev is None:
        prev = "main"
    await show_menu(prev, callback, context)

@callback_router.message_callback(F.callback.payload == "manage_subscription")
async def process_manage_subscription(callback: MessageCallback, context: MemoryContext):
    max_id = callback.from_user.user_id

    user = db.select_data("users", where_conditions={"user_id": max_id})
    if not user:
        text = get_text(key="user_not_found", max_id=max_id, db=db)
        await callback.answer(text, )
        return

    user_id = user[0][0]

    subs = db.select_data(
        "subscriptions",
        where_conditions={"user_id": user_id, "status": "active"}
    )

    active_sub = None
    for sub in subs:
        if active_sub is None or sub[0] > active_sub[0]:
            active_sub = sub

    plan_name = "free"
    expires_at_str = get_text(
        key="subscription_lifetime",
        max_id=max_id,
        db=db
    )

    if active_sub:
        plan_id = active_sub[2]

        plan = db.select_data(
            "plans",
            where_conditions={"id": plan_id}
        )

        if plan:
            plan_name = plan[0][1]

        expires_at = active_sub[5]

        if expires_at:
            user_offset = user[0][4] or "UTC"
            user_tz = ZoneInfo(user_offset)

            now_user = datetime.now(user_tz)

            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=user_tz)

            remaining = (expires_at - now_user).total_seconds()
            remaining_days = int(remaining // 86400) + (1 if remaining % 86400 > 0 else 0)

            if remaining > 0:
                expires_at_str = get_text(
                    key="subscription_expires_with_days",
                    max_id=max_id,
                    db=db,
                    date=expires_at.strftime("%d.%m.%Y"),
                    days=remaining_days
                )
            else:
                expires_at_str = get_text(
                    key="subscription_expired",
                    max_id=max_id,
                    db=db
                )
                plan_name = "free"


    if plan_name == "pro":
        status_text = get_text(
            key="subscription_status_pro",
            max_id=max_id,
            db=db,
            expires_at=expires_at_str
        )

        auto_renewal = active_sub[7] if len(active_sub) > 7 else False

        builder = InlineKeyboardBuilder()

        if auto_renewal:
            builder.row(
                CallbackButton(
                    text=get_text(
                        key="disable_auto_renewal_btn",
                        max_id=max_id,
                        db=db
                    ),
                    payload="disable_auto_renewal"
                )
    )
        builder.row(
            CallbackButton(
                text=get_text(
                    key="back_btn",
                    max_id=max_id,
                    db=db
                ),
                payload="back"
            )
        )

        keyboard = builder.as_markup()

    else:
        status_text = get_text(
            key="subscription_status_free",
            max_id=max_id,
            db=db
        )

        builder = InlineKeyboardBuilder()

        builder.row(
            CallbackButton(
                text=get_text(
                    key="subscription_buy_pro_btn",
                    max_id=max_id,
                    db=db
                ),
                payload="buy_pro"
            )
        )

        builder.row(
            CallbackButton(
                text=get_text(
                    key="back_btn",
                    max_id=max_id,
                    db=db
                ),
                payload="back"
            )
        )

        keyboard = builder.as_markup()

    await push_menu(context, "main")
    await callback.message.edit(
        status_text,
        attachments=[keyboard]
    )
    


@callback_router.message_callback(F.callback.payload == "buy_pro")
async def process_buy_pro(callback: MessageCallback, context: MemoryContext):
    max_id = callback.from_user.user_id

    user = db.select_data(
        "users",
        where_conditions={"user_id": max_id}
    )

    if not user:
        await callback.answer(
            get_text(
                key="user_not_found",
                max_id=max_id,
                db=db
            ),
            
        )
        return


    builder = InlineKeyboardBuilder()

    builder.row(
        CallbackButton(
            text=get_text(
                key="subscription_one_time_btn",
                max_id=max_id,
                db=db
            ),
            payload="buy_pro_once"
        )
    )

    builder.row(
        CallbackButton(
            text=get_text(
                key="subscription_auto_payment_btn",
                max_id=max_id,
                db=db
            ),
            payload="buy_pro_auto"
        )
    )

    builder.row(
        CallbackButton(
            text=get_text(
                key="back_btn",
                max_id=max_id,
                db=db
            ),
            payload="back"
        )
    )

    keyboard = builder.as_markup()

    text = get_text(
        key="subscription_payment_method",
        max_id=max_id,
        db=db
    )

    await callback.message.edit(
        text,
        attachments=[keyboard]
    )

    


@callback_router.message_callback(F.callback.payload == "buy_pro_once")
async def process_buy_pro_once(
    callback: MessageCallback,
    context: MemoryContext
):
    max_id = callback.from_user.user_id

    user = db.select_data(
        "users",
        where_conditions={"user_id": max_id}
    )

    if not user:
        await callback.answer(
            get_text(
                key="user_not_found",
                max_id=max_id,
                db=db
            ),
            
        )
        return

    user_id = user[0][0]
            
    try:
        payment = create_first_payment(
            user_id,
            max_id
        )

        payment_url = payment.confirmation.confirmation_url

        text = get_text(
            key="subscription_payment_link",
            max_id=max_id,
            db=db,
            payment_url=payment_url
        )

        await callback.message.edit(text)

    except Exception as e:
        logger.exception(
            f"Error creating one-time payment for user {max_id}: {e}"
        )

        await callback.answer(
            get_text(
                key="subscription_payment_error",
                max_id=max_id,
                db=db
            ),
            
        )
        return

    


@callback_router.message_callback(F.callback.payload == "buy_pro_auto")
async def process_buy_pro_auto(
    callback: MessageCallback,
    context: MemoryContext
):
    max_id = callback.from_user.user_id

    user = db.select_data(
        "users",
        where_conditions={"user_id": max_id}
    )

    if not user:
        await callback.answer(
            get_text(
                key="user_not_found",
                max_id=max_id,
                db=db
            ),
            
        )
        return

    user_id = user[0][0]

    try:
        payment = create_auto_payment(
            user_id,
            max_id
        )

        payment_url = payment.confirmation.confirmation_url

        text = get_text(
            key="subscription_auto_payment_link",
            max_id=max_id,
            db=db,
            payment_url=payment_url
        )

        await callback.message.edit(text)

    except Exception as e:
        logger.exception(
            f"Error creating auto payment for user {max_id}: {e}"
        )

        await callback.answer(
            get_text(
                key="subscription_payment_error",
                max_id=max_id,
                db=db
            ),
            
        )
        return

    

@callback_router.message_callback(F.callback.payload == "disable_auto_renewal")
async def process_disable_auto_renewal(callback: MessageCallback, context: MemoryContext):
    max_id = callback.from_user.user_id

    user = db.select_data("users", where_conditions={"user_id": max_id})
    if not user:
        await callback.answer("Пользователь не найден", )
        return

    user_id = user[0][0]

    subs = db.select_data(
        "subscriptions",
        where_conditions={"user_id": user_id, "status": "active"}
    )
    active_sub = None
    for sub in subs:
        if active_sub is None or sub[0] > active_sub[0]:
            active_sub = sub

    if not active_sub:
        await callback.answer("Нет активной подписки", )
        return

    db.update_data(
        "subscriptions",
        {"auto_renewal": False},
        where_conditions={"id": active_sub[0]}
    )

    # db.update_data(
    #     "users",
    #     {"yookassa_payment_method_id": None},
    #     where_conditions={"id": max_id}
    # )

    text = get_text(key="auto_renewal_disabled", max_id=max_id, db=db)
    await callback.answer(text, )

    await process_manage_subscription(callback, context)

async def replace_menu(callback, text, keyboard):
    await callback.message.delete()

    await callback.message.answer(
        text=text,
        attachments=[keyboard]
    )