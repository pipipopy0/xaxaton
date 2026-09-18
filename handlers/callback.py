import asyncio

from aiogram import Router
from forms.calendar_fsm import CalendarStates

from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile, InputMediaPhoto
from aiogram.fsm.context import FSMContext

from handlers.answer_texts.TEXT import get_text
from handlers.router import ADMINS, waiting_for_broadcast
from services.metrika import send_metrika_event
from services.payment_service import (
    create_first_payment,
    create_auto_payment
)
from services.access import is_pro_user
from logger_config import logger
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from services.google_calendar_service import build_google_auth_url
from monitor.status import get_full_status, format_status
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

waiting_for_time_message = {}

callback_router = Router()
db = None

async def push_menu(state: FSMContext, menu_name: str):
    """Сохраняет текущее меню в историю."""
    data = await state.get_data()
    history = data.get("history", [])
    history.append(menu_name)
    await state.update_data(history=history)

async def pop_menu(state: FSMContext) -> str | None:
    """Удаляет последнее меню из истории и возвращает его."""
    data = await state.get_data()
    history = data.get("history", [])
    if not history:
        return None
    return history.pop()

async def show_menu(menu_name: str, callback: CallbackQuery, state: FSMContext):
    """
    Отображает меню по его имени, заменяя текущее сообщение (edit_text).
    Для меню с логикой (Apple/Google) вызывает отдельные функции.
    """
    tg_id = callback.from_user.id

    # ========== ГЛАВНОЕ МЕНЮ ==========
    if menu_name == "main":
        text = get_text(key="start_registered", tg_id=tg_id, db=db)
        keyboard = get_register_inline_keyboard(
            is_admin=callback.from_user.id in ADMINS,
            tg_id=tg_id
        )
        await callback.message.edit_text(text, reply_markup=keyboard)

    # ========== НАСТРОЙКИ ==========
    elif menu_name == "settings":
        # В вашем коде используется ключ "notification_time_set" – возможно, это ошибка.
        # Я оставлю как есть, но рекомендую создать отдельный ключ "settings".
        text = get_text(key="settings_menu", tg_id=tg_id, db=db)
        keyboard = get_settings_inline_keyboard(tg_id=tg_id)
        await callback.message.edit_text(text, reply_markup=keyboard)

    # ========== ДОКУМЕНТЫ ==========
    elif menu_name == "documents":
        # В вашем коде тоже используется "notification_time_set" – замените на "documents", если создадите
        text = get_text(key="documents_menu", tg_id=tg_id, db=db)
        keyboard = get_documents_inline_keyboard(tg_id=tg_id)
        await callback.message.edit_text(text, reply_markup=keyboard)

    # ========== ПОДКЛЮЧЕНИЕ КАЛЕНДАРЕЙ ==========
    elif menu_name == "calendars_setup":
        text = get_text(key="calendars_setup", tg_id=tg_id, db=db)
        keyboard = get_calendars_inline_keyboard(tg_id=tg_id)
        await callback.message.edit_text(text, reply_markup=keyboard)

    # ========== APPLE КАЛЕНДАРЬ (с проверкой) ==========
    elif menu_name == "apple_calendar":
        # Проверяем пользователя
        users = db.select_data("users", where_conditions={"tg_id":tg_id})
        if not users:
            text = get_text(key="user_not_found", tg_id=tg_id, db=db)
            await callback.message.edit_text(text)
            await callback.answer()
            return

        user_id = users[0][0]
        auth = db.select_data("users_authorizations", where_conditions={"user_id" : user_id})
        is_connected = False
        if auth:
            row = auth[0]
            if len(row) > 4 and row[2] and row[4]:
                is_connected = True

        if is_connected:
            text = get_text(key="apple_calendar_activated_already", tg_id=tg_id, db=db)
            keyboard = get_recconect_disconnect_calendar_keyboard(provider="apple", tg_id=tg_id)
            await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.message.delete()
            text = get_text(key="apple_email_prompt", tg_id=tg_id, db=db)
            apple_instruction_text = get_text(
                            key="apple_calendar_instructions",
                            tg_id=tg_id,
                            db=db
                        )
            media = [
                InputMediaPhoto(media=FSInputFile("media/instructions/apple/1.png"), caption=apple_instruction_text),
                InputMediaPhoto(media=FSInputFile("media/instructions/apple/2.png")),
                InputMediaPhoto(media=FSInputFile("media/instructions/apple/3.png")),
                InputMediaPhoto(media=FSInputFile("media/instructions/apple/4.png")),
                InputMediaPhoto(media=FSInputFile("media/instructions/apple/5.png")),
                InputMediaPhoto(media=FSInputFile("media/instructions/apple/6.png"))
            ]
            await callback.message.answer_media_group(media)

            await state.update_data(provider="apple")
            await callback.message.answer(text)
            await state.set_state(CalendarStates.waiting_email)

    # ========== GOOGLE КАЛЕНДАРЬ (с проверкой) ==========
    elif menu_name == "google_calendar":
        users = db.select_data("users", where_conditions={"tg_id":tg_id})
        if not users:
            text = get_text(key="user_not_found", tg_id=tg_id, db=db)
            await callback.message.edit_text(text)
            await callback.answer()
            return

        user_id = users[0][0]
        authorizations = db.select_data("users_authorizations", where_conditions={"user_id" : user_id})
        is_connected = False
        if authorizations:
            row = authorizations[0]
            if len(row) > 8 and row[8] is not None:
                is_connected = True

        if is_connected:
            text = get_text(key="google_calendar_activated_already", tg_id=tg_id, db=db)
            keyboard = get_recconect_disconnect_calendar_keyboard(provider="google", tg_id=tg_id)
            await callback.message.edit_text(text, reply_markup=keyboard)
        else:

            await callback.message.delete()
            text = get_text(
                            key="google_calendar_oauth",
                            tg_id=tg_id,
                            db=db
                        )
            google_instruction_text = get_text(
                key="google_calendar_instructions",
                tg_id=tg_id,
                db=db
            )
            media = [
                InputMediaPhoto(media=FSInputFile("media/instructions/google/1.png"), caption=google_instruction_text),
                InputMediaPhoto(media=FSInputFile("media/instructions/google/2.png")),
                InputMediaPhoto(media=FSInputFile("media/instructions/google/3.png"))
            ]
            await callback.message.answer_media_group(media=media)

            google_url = build_google_auth_url(user_id=user_id)

            # Вставляем ссылку в текст
            text = text.format(url=google_url)

            # Клавиатура — только кнопка «Назад» (если она нужна)
            keyboard = get_inline_google_authorization(
                user_id=user_id,
                tg_id=tg_id
            )

            await callback.message.answer(text, reply_markup=keyboard)

    # ========== ВЫБОР ЧАСОВОГО ПОЯСА ==========
    elif menu_name == "timezone":
        text = get_text(key="timezone_setup", tg_id=tg_id, db=db)
        keyboard = get_time_inline_keyboard_with_back(tg_id=tg_id)   # с кнопкой «Назад»
        await callback.message.edit_text(text, reply_markup=keyboard)

    # ========== ПОДДЕРЖКА ==========
    elif menu_name == "support":
        text = get_text(key="support", tg_id=tg_id, db=db)
        keyboard = get_support_inline_keyboard(tg_id=tg_id)
        await callback.message.edit_text(text, reply_markup=keyboard)

    # ========== АДМИН-ПАНЕЛЬ ==========
    elif menu_name == "admin_panel":
        text = get_text(key="admin_panel", tg_id=tg_id, db=db)
        keyboard = get_admin_inline_keyboard(tg_id=tg_id)
        await callback.message.edit_text(text, reply_markup=keyboard)

    # ========== УВЕДОМЛЕНИЯ (настройка) ==========
    elif menu_name == "update_notifications":
        text = get_text(key="update_notifications", tg_id=tg_id, db=db)
        keyboard = get_update_notifications_inline_keyboard(tg_id=tg_id)
        await callback.message.edit_text(text, reply_markup=keyboard)

    # ========== СМЕНА ЯЗЫКА ==========
    elif menu_name == "change_language":
        text = get_text(key="select_language", tg_id=tg_id, db=db)
        keyboard = get_inline_language_keyborad(tg_id=tg_id)
        await callback.message.edit_text(text, reply_markup=keyboard)

    # ========== ПЕРВАЯ ИНФОРМАЦИЯ (что такое Календатор) ==========
    elif menu_name == "first_info":
        text = get_text(key="first_info", tg_id=tg_id, db=db)
        keyboard = get_support_inline_keyboard(tg_id=tg_id)
        await callback.message.edit_text(text, reply_markup=keyboard)

    # ========== ЕСЛИ ИМЯ НЕ РАСПОЗНАНО – ПОКАЗЫВАЕМ ГЛАВНОЕ ==========
    else:
        text = get_text(key="start_registered", tg_id=tg_id, db=db)
        keyboard = get_register_inline_keyboard(
            is_admin=callback.from_user.id in ADMINS,
            tg_id=tg_id
        )
        await callback.message.edit_text(text, reply_markup=keyboard)

    # Подтверждаем callback (убираем часики)
    await callback.answer()


@callback_router.callback_query(lambda c: c.data == "first_info")
async def process_first_info(callback: CallbackQuery, state: FSMContext):
    await push_menu(state, "main")   # запоминаем главное меню
    await show_menu("first_info", callback, state)

@callback_router.callback_query(lambda c: c.data == "support")
async def process_support(callback: CallbackQuery, state: FSMContext):
    await push_menu(state, "main")   # запоминаем, что были в главном меню
    await show_menu("support", callback, state)

@callback_router.callback_query(lambda c: c.data == "update_time")
async def process_update_time(callback: CallbackQuery, state: FSMContext):
    await push_menu(state, "settings")
    await state.update_data(from_settings=True)   # новый флаг
    await show_menu("timezone", callback, state)
    
@callback_router.callback_query(lambda c: c.data == "delete_data")
async def process_delete_data(callback: CallbackQuery):
    tg_id = callback.from_user.id
    
    user = db.select_data("users", where_conditions={"tg_id":tg_id})
    if user[0][0]:
        user_id = user[0][0]
        db.delete_data("users_costs", where_conditions={"user_id" : user_id})
        db.delete_data("users", where_conditions={"tg_id":tg_id})

    text = get_text(key = "delete_success", tg_id = callback.from_user.id, db=db)
    await callback.message.answer(text)
    await callback.answer()

@callback_router.callback_query(lambda c: c.data == "cancel_delete")
async def process_cancel_delete(callback: CallbackQuery):
    text = get_text(key = "delete_cancel", tg_id = callback.from_user.id, db=db)
    await callback.message.answer(text)
    await callback.answer()

@callback_router.callback_query(lambda c: c.data.startswith("timezone:"))
async def process_timezone_page(callback: CallbackQuery, state: FSMContext):
    offset = int(callback.data.split(":")[1])
    offset_string = WORLD_TIMEZONES[offset]
    tg_id = callback.from_user.id

    db.update_data(
        table_name="users",
        data={"timezone_offset": offset_string},
        where_conditions={"tg_id": tg_id}
    )

    # Сбрасываем флаг, чтобы кнопка «Назад» не появлялась при следующем входе
    await state.update_data(from_settings=False)

    text = get_text(key="timezone_set", tg_id=callback.from_user.id, db=db)
    text = text.format(offset=offset)
    await callback.message.answer(text)
    await callback.answer()

@callback_router.callback_query(lambda c: c.data.startswith("page:"))
async def process_time_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    tg_id = callback.from_user.id
    data = await state.get_data()
    if data.get("from_settings"):
        new_markup = get_time_inline_keyboard_with_back(page=page, tg_id=tg_id)
    else:
        new_markup = get_time_inline_keyboard(page=page, tg_id=tg_id)
    try:
        await callback.message.edit_reply_markup(reply_markup=new_markup)
    except Exception as e:
        logger.error(f"Error updating inline keyboard: {e}")
    await callback.answer()

@callback_router.callback_query(lambda c: c.data == "update_notifications")
async def process_update_notifications(callback: CallbackQuery, state: FSMContext):
    await push_menu(state, "settings")
    await show_menu("update_notifications", callback, state)

@callback_router.callback_query(lambda c: c.data == "yes_update_notifications")
async def process_yes_update_notifications(callback: CallbackQuery):
    waiting_for_time_message[callback.from_user.id] = True
    text = get_text(key = "notification_time_prompt", tg_id = callback.from_user.id, db=db)
    await callback.message.answer(text)

@callback_router.callback_query(lambda c: c.data == "no_update_notifications")
async def process_no_update_notifications(callback: CallbackQuery):
    tg_id = callback.from_user.id
    db.update_data(
        table_name="users",
        data={"notification_time": None},
        where_conditions={"tg_id":tg_id}
    )
    text = get_text(key = "notification_time_set", tg_id = callback.from_user.id, db=db)
    await callback.message.answer(text)
    await callback.answer()

@callback_router.callback_query(lambda c: c.data == "settings")
async def process_settings_menu(callback: CallbackQuery, state: FSMContext):
    await push_menu(state, "main")
    await show_menu("settings", callback, state)

@callback_router.callback_query(lambda c: c.data == "documents")
async def process_documents_menu(callback: CallbackQuery, state: FSMContext):
    await push_menu(state, "main")
    await show_menu("documents", callback, state)

@callback_router.callback_query(lambda c: c.data == "admin_panel")
async def process_admin_panel(callback: CallbackQuery, state: FSMContext):
    await push_menu(state, "main")   # или из какого меню пришли? Если только из главного, то "main"
    await show_menu("admin_panel", callback, state)

@callback_router.callback_query(lambda c: c.data == "admin_update_notification")
async def process_admin_update_notification(callback: CallbackQuery):
    if callback.from_user.id not in ADMINS:
        text = get_text(key = "admin_no_permission", tg_id = callback.from_user.id, db=db)
        await callback.message.answer(text)
        await callback.answer()
        return
    waiting_for_broadcast.add(callback.from_user.id)
    text = get_text(key = "admin_broadcast_prompt", tg_id = callback.from_user.id, db=db)
    await callback.message.answer(text)
    await callback.answer()
@callback_router.callback_query(lambda c: c.data == "services_status")
async def process_admin_status_services(callback: CallbackQuery):
    status = get_full_status()
    text = format_status(status)
    await callback.message.answer(text)
    await callback.answer()
    return
@callback_router.callback_query(lambda c: c.data == "calendars_setup")
async def process_calendars_setup(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id

    user = db.select_data(
        "users",
        where_conditions={"tg_id": tg_id}
    )

    if not user:
        await callback.answer(
            "Ошибка: пользователь не найден",
            show_alert=True
        )
        return

    user_id = user[0][0]

    # Проверяем подписку
    """if not is_pro_user(db, user_id):
        text = get_text(
            key="calendars_pro_only",
            tg_id=tg_id,
            db=db
        )
        await callback.answer(
            text,
            show_alert=True
        )
        return
    """
    # PRO → открываем меню календарей
    await push_menu(state, "main")
    await show_menu("calendars_setup", callback, state)
@callback_router.callback_query(lambda c: c.data == "apple_calendar")
async def process_apple_calendar(callback: CallbackQuery, state: FSMContext):
    await push_menu(state, "calendars_setup")
    await show_menu("apple_calendar", callback, state)
@callback_router.callback_query(lambda c: c.data.startswith("google_specific_password_auth"))
async def process_google_calendar_spec_pass_setup(callback: CallbackQuery, state: FSMContext):
    text = get_text(key = "google_email_prompt", tg_id = callback.from_user.id, db=db)
    await state.update_data(provider="google")
    await callback.message.answer(text)
    await state.set_state(CalendarStates.waiting_email)
    await callback.answer()
@callback_router.callback_query(lambda c: c.data.startswith("google_calendar"))
async def process_google_calendar_setup(callback: CallbackQuery, state: FSMContext):
    await push_menu(state, "calendars_setup")
    await show_menu("google_calendar", callback, state)
@callback_router.callback_query(lambda c: c.data.startswith("change_language"))
async def process_change_language(callback: CallbackQuery, state: FSMContext):
    await push_menu(state, "settings")
    await show_menu("change_language", callback, state)
@callback_router.callback_query(lambda c: c.data.startswith("russian_language"))
async def process_russian_language(callback: CallbackQuery):
    tg_id = callback.from_user.id
    try:
        db.update_data(
            table_name="users",
            data={"language": "ru"},
            where_conditions={"tg_id":tg_id}
        )
        text = get_text(key = "language_changed_ru", tg_id = callback.from_user.id, db=db)
        await callback.message.answer(text)
    except Exception as e:
        logger.error(f"Error updating language for user {tg_id}: {e}")
        text = get_text(key = "language_change_error", tg_id = callback.from_user.id, db=db)
        await callback.message.answer(text)
    await callback.answer()
@callback_router.callback_query(lambda c: c.data.startswith("english_language"))
async def process_english_language(callback: CallbackQuery):

    tg_id = callback.from_user.id

    try:
        db.update_data(
            table_name="users",
            data={"language": "en"},
            where_conditions={"tg_id":tg_id}
        )
        text = get_text(key = "language_changed_en", tg_id = callback.from_user.id, db=db)
        await callback.message.answer(text)
    except Exception as e:
        logger.error(f"Error updating language for user {tg_id}: {e}")
        text = get_text(key = "language_change_error", tg_id = callback.from_user.id, db=db)
        await callback.message.answer(text)
    await callback.answer()
@callback_router.callback_query(lambda c: c.data.startswith("reconnect_google_calendar"))
async def reconnect_google_calendar(callback: CallbackQuery, state: FSMContext):
    await push_menu(state, "google_calendar")   # запоминаем, что были в меню Google
    tg_id = callback.from_user.id
    user = db.select_data("users", where_conditions={"tg_id":tg_id})
    user_id = user[0][0]

    text = get_text(
    key="google_calendar_oauth",
    tg_id=tg_id,
    db=db
)

    # Получаем ссылку
    keyboard = get_inline_google_authorization(
        user_id=user_id,
        tg_id=tg_id
    )

    google_url = keyboard.inline_keyboard[0][0].url

    text = text.format(url=google_url)

    await callback.message.edit_text(text)
    await callback.answer()
@callback_router.callback_query(lambda c: c.data == "disconnect_google_calendar")
async def disconnect_google_calendar(callback: CallbackQuery):
    tg_id = callback.from_user.id
    user = db.select_data("users", where_conditions={"tg_id" : tg_id})
    if not user:
        await callback.answer("Ошибка: пользователь не найден")
        return
    user_id = user[0][0]

    # Очищаем все данные Google
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

    text = get_text(key="calendar_disconnected", tg_id=tg_id, db=db)
    await callback.message.answer(text)
    await callback.answer()
@callback_router.callback_query(lambda c: c.data == "reconnect_apple_calendar")
async def reconnect_apple_calendar(callback: CallbackQuery, state: FSMContext):
    await push_menu(state, "apple_calendar")   # запоминаем меню Apple
    tg_id = callback.from_user.id
    user = db.select_data("users", where_conditions={"tg_id":tg_id})
    if not user:
        await callback.answer("Ошибка")
        return
    user_id = user[0][0]
    # Очищаем старые данные Apple
    db.update_data(
        table_name="users_authorizations",
        data={
            "apple_calendar_email": None,
            "apple_calendar_password": None,
            "apple_calendar_url": None
        },
        where_conditions={"user_id" : user_id}
    )
    text = get_text(key="apple_email_prompt", tg_id=tg_id, db=db)
    await state.update_data(provider="apple")
    await callback.message.edit_text(text)
    await state.set_state(CalendarStates.waiting_email)
    await callback.answer()
    
@callback_router.callback_query(lambda c: c.data.startswith("disconnect_apple_calendar"))
async def disconnect_apple_calendar(callback: CallbackQuery):
    tg_id = callback.from_user.id
    user = db.select_data("users", where_conditions={"tg_id":tg_id})
    user_id = user[0][0]
    db.update_data(table_name="users_authorizations",
    
    data={
        "apple_calendar_email": None,
        "apple_calendar_password": None,
        "apple_calendar_url": None
    },
    where_conditions={"user_id" : user_id}
    )
    text = get_text(key = "calendar_disconnected", tg_id = callback.from_user.id, db=db)
    
    await callback.message.answer(text)
    await callback.answer()

@callback_router.callback_query(lambda c: c.data == "back")
async def process_back(callback: CallbackQuery, state: FSMContext):
    # Если в процессе ввода – выходим из FSM и возвращаемся
    current_state = await state.get_state()
    if current_state in (CalendarStates.waiting_email, CalendarStates.waiting_password):
        await state.clear()
        prev = await pop_menu(state)
        if prev:
            await show_menu(prev, callback, state)
        else:
            await show_menu("main", callback, state)
        await callback.answer()
        return

    prev = await pop_menu(state)
    if prev is None:
        prev = "main"
    await show_menu(prev, callback, state)
    await callback.answer()

@callback_router.callback_query(lambda c: c.data == "manage_subscription")
async def process_manage_subscription(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id

    user = db.select_data("users", where_conditions={"tg_id": tg_id})
    if not user:
        text = get_text(key="user_not_found", tg_id=tg_id, db=db)
        await callback.answer(text, show_alert=True)
        return

    user_id = user[0][0]

    user_analytics = db.select_data(
        "users",
        columns=["yclid", "metrika_client_id"],
        where_conditions={"id": user_id}
    )
    if user_analytics:
        yclid = user_analytics[0][0]
        client_id = user_analytics[0][1]
        if client_id:
            asyncio.create_task(
                send_metrika_event(
                    client_id=client_id,
                    target="subscription_management_opened",
                    yclid=yclid
                )
            )

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
        tg_id=tg_id,
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

            # Если дата из БД без timezone
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=user_tz)

            remaining = (expires_at - now_user).total_seconds()
            remaining_days = int(remaining // 86400) + (1 if remaining % 86400 > 0 else 0)

            if remaining > 0:
                expires_at_str = get_text(
                    key="subscription_expires_with_days",
                    tg_id=tg_id,
                    db=db,
                    date=expires_at.strftime("%d.%m.%Y"),
                    days=remaining_days
                )
            else:
                expires_at_str = get_text(
                    key="subscription_expired",
                    tg_id=tg_id,
                    db=db
                )
                plan_name = "free"

    if plan_name == "pro":
        status_text = get_text(
            key="subscription_status_pro",
            tg_id=tg_id,
            db=db,
            expires_at=expires_at_str
        )

        # Проверяем, включено ли автопродление
        auto_renewal = active_sub[7] if len(active_sub) > 7 else False

        buttons = [
            [
                InlineKeyboardButton(
                    text=get_text(
                        key="back_btn",
                        tg_id=tg_id,
                        db=db
                    ),
                    callback_data="back"
                )
            ]
        ]

        # Если автопродление включено – добавляем кнопку отключения
        if auto_renewal:
            disable_btn = InlineKeyboardButton(
                text=get_text(
                    key="disable_auto_renewal_btn",  # новый ключ локализации
                    tg_id=tg_id,
                    db=db
                ),
                callback_data="disable_auto_renewal"
            )
            buttons.insert(0, [disable_btn])  # вставляем первой строкой

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    else:
        status_text = get_text(
            key="subscription_status_free",
            tg_id=tg_id,
            db=db
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=get_text(
                            key="subscription_buy_pro_btn",
                            tg_id=tg_id,
                            db=db
                        ),
                        callback_data="buy_pro"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=get_text(
                            key="back_btn",
                            tg_id=tg_id,
                            db=db
                        ),
                        callback_data="back"
                    )
                ]
            ]
        )

    await push_menu(state, "main")
    await callback.message.edit_text(
        status_text,
        reply_markup=keyboard
    )
    await callback.answer()


@callback_router.callback_query(lambda c: c.data == "buy_pro")
async def process_buy_pro(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id

    user = db.select_data(
        "users",
        where_conditions={"tg_id": tg_id}
    )

    if not user:
        await callback.answer(
            get_text(
                key="user_not_found",
                tg_id=tg_id,
                db=db
            ),
            show_alert=True
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(
                        key="subscription_one_time_btn",
                        tg_id=tg_id,
                        db=db
                    ),
                    callback_data="buy_pro_once"
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text(
                        key="subscription_auto_payment_btn",
                        tg_id=tg_id,
                        db=db
                    ),
                    callback_data="buy_pro_auto"
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text(
                        key="back_btn",
                        tg_id=tg_id,
                        db=db
                    ),
                    callback_data="back"
                )
            ]
        ]
    )

    text = get_text(
        key="subscription_payment_method",
        tg_id=tg_id,
        db=db
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard
    )

    await callback.answer()


@callback_router.callback_query(lambda c: c.data == "buy_pro_once")
async def process_buy_pro_once(
    callback: CallbackQuery,
    state: FSMContext
):
    tg_id = callback.from_user.id

    user = db.select_data(
        "users",
        where_conditions={"tg_id": tg_id}
    )

    if not user:
        await callback.answer(
            get_text(
                key="user_not_found",
                tg_id=tg_id,
                db=db
            ),
            show_alert=True
        )
        return

    user_id = user[0][0]

    user_analytics = db.select_data(
        "users",
        columns=["yclid", "metrika_client_id"],
        where_conditions={"id": user_id}
    )
    if user_analytics:
        yclid = user_analytics[0][0]
        client_id = user_analytics[0][1]
        if client_id:
            asyncio.create_task(
                send_metrika_event(
                    client_id=client_id,
                    target="payment_started",
                    yclid=yclid
                )
            )
            
    try:
        payment = create_first_payment(
            user_id,
            tg_id
        )

        payment_url = payment.confirmation.confirmation_url

        text = get_text(
            key="subscription_payment_link",
            tg_id=tg_id,
            db=db,
            payment_url=payment_url
        )

        await callback.message.edit_text(text)

    except Exception as e:
        logger.exception(
            f"Error creating one-time payment for user {tg_id}: {e}"
        )

        await callback.answer(
            get_text(
                key="subscription_payment_error",
                tg_id=tg_id,
                db=db
            ),
            show_alert=True
        )
        return

    await callback.answer()


@callback_router.callback_query(lambda c: c.data == "buy_pro_auto")
async def process_buy_pro_auto(
    callback: CallbackQuery,
    state: FSMContext
):
    tg_id = callback.from_user.id

    user = db.select_data(
        "users",
        where_conditions={"tg_id": tg_id}
    )

    if not user:
        await callback.answer(
            get_text(
                key="user_not_found",
                tg_id=tg_id,
                db=db
            ),
            show_alert=True
        )
        return

    user_id = user[0][0]
    user_analytics = db.select_data(
        "users",
        columns=["yclid", "metrika_client_id"],
        where_conditions={"id": user_id}
    )
    if user_analytics:
        yclid = user_analytics[0][0]
        client_id = user_analytics[0][1]
        if client_id:
            asyncio.create_task(
                send_metrika_event(
                    client_id=client_id,
                    target="payment_started",
                    yclid=yclid
                )
            )
    try:
        payment = create_auto_payment(
            user_id,
            tg_id
        )

        payment_url = payment.confirmation.confirmation_url

        text = get_text(
            key="subscription_auto_payment_link",
            tg_id=tg_id,
            db=db,
            payment_url=payment_url
        )

        await callback.message.edit_text(text)

    except Exception as e:
        logger.exception(
            f"Error creating auto payment for user {tg_id}: {e}"
        )

        await callback.answer(
            get_text(
                key="subscription_payment_error",
                tg_id=tg_id,
                db=db
            ),
            show_alert=True
        )
        return

    await callback.answer()

@callback_router.callback_query(lambda c: c.data == "disable_auto_renewal")
async def process_disable_auto_renewal(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id

    user = db.select_data("users", where_conditions={"tg_id": tg_id})
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    user_id = user[0][0]

    # Найти активную подписку
    subs = db.select_data(
        "subscriptions",
        where_conditions={"user_id": user_id, "status": "active"}
    )
    active_sub = None
    for sub in subs:
        if active_sub is None or sub[0] > active_sub[0]:
            active_sub = sub

    if not active_sub:
        await callback.answer("Нет активной подписки", show_alert=True)
        return

    # Отключаем автопродление
    db.update_data(
        "subscriptions",
        {"auto_renewal": False},
        where_conditions={"id": active_sub[0]}
    )

    # Опционально: очистить сохранённый метод оплаты
    # db.update_data(
    #     "users",
    #     {"yookassa_payment_method_id": None},
    #     where_conditions={"id": user_id}
    # )

    text = get_text(key="auto_renewal_disabled", tg_id=tg_id, db=db)
    await callback.answer(text, show_alert=True)

    # Обновляем меню управления подпиской
    await process_manage_subscription(callback, state)