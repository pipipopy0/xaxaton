import os

from aiogram import (
    Router,
    Bot
)
from aiogram.types import (
    Message
)
from aiogram.fsm.context import FSMContext

from forms.calendar_fsm import CalendarStates
from services.ai_service import ai_answer
from handlers.answer_texts.TEXT import get_text

from services.event_service import process_ai_event
from services.voice_to_text_ai import transcribe
from services.crypto_utils import CryptographyService
from services.calendars.calendar_service import get_calendar_url
from services.access import check_access

from handlers.keyboards import (
    get_time_inline_keyboard,
    get_inline_apple_app_specific_password_link, 
    get_inline_google_app_specific_password_link)

from datetime import timezone
from logger_config import logger
from zoneinfo import ZoneInfo



router = Router()
history = {}
db = None
ADMINS = set() 
CRYPT_SERVICE = CryptographyService(os.getenv("key_cryptography"))

waiting_for_broadcast = set()


async def _save_notification_time(message: Message) -> bool:
    from handlers.callback import waiting_for_time_message
    if message.from_user.id in waiting_for_time_message and waiting_for_time_message[message.from_user.id]:
        try:
            notification_time = int(message.text)
            db.update_data(
                table_name="users",
                data={"notification_time": notification_time},
                where_conditions={"tg_id": message.from_user.id}
            )
            text = get_text(key="notification_time_set", tg_id=message.from_user.id, db=db, minutes=notification_time)
            await message.answer(text)
            del waiting_for_time_message[message.from_user.id]
            return True
        except ValueError:
            text = get_text(key="notification_time_invalid", tg_id=message.from_user.id, db=db)
            await message.answer(text)
            return True
    return False

async def check_user_registration(user_id):
    user = db.select_data(table_name="users", where_conditions={"tg_id": user_id})
    if user and user[0][4] is not None:
        logger.debug(f"User {user_id} has timezone: {user[0][4]}")
        return True
    logger.debug(f"User {user_id} has no timezone set")
    return False

async def cost(user_id, response_cost, column_name):
    logger.debug(f"cost: user_id={user_id}, cost={response_cost}, column={column_name}")
    # column_name = "text_cost" или "voice_cost"
    cost_record = db.select_data("users_costs", where_conditions={"user_id": user_id})
    
    if cost_record:
        old_cost = float(cost_record[0][2] if column_name == "text_cost" else cost_record[0][3])
        new_cost = old_cost + response_cost
        new_all_cost = float(cost_record[0][4]) + response_cost
        
        db.update_data("users_costs", 
            {column_name: new_cost, "all_cost": new_all_cost},
            where_conditions={"user_id": user_id})
    else:
        db.insert_data("users_costs", {
            "user_id": user_id,
            column_name: float(response_cost),
            "all_cost": float(response_cost)
        })
    logger.info(f"Cost updated for user {user_id}: {column_name} += {response_cost}")

async def handle_user_input(message, text: str, user_id):
    logger.info(f"User {user_id} sent: {text[:200]}")
    user = db.select_data("users", where_conditions={"id": user_id})
    offset = user[0][4] if user and user[0][4] else "UTC"
    user_default_time = user[0][6] if user and len(user[0]) > 6 else None
    logger.debug(f"User offset: {offset}")
    logger.debug(f"User default time: {user_default_time}")

    await message.bot.send_chat_action(
        chat_id = message.chat.id,
        action = "typing"
    )
    if user_id not in history:
        history[user_id] = []
    
    history[user_id].append({"role": "user", "content": text})

    last_12 = history[user_id][-12:]

    result = ai_answer(
        user_text=text,
        system_prompt="intemt_router_prompt.txt",
        history=last_12,
        user_offset=offset, 
        tg_id=message.from_user.id
    )

    ai_router_response = result["response"]
    response_cost = result["response_cost"]
    await cost(user_id, response_cost, "text_cost")

    action = ai_router_response.get("action")
    language = ai_router_response.get("language", "ru")
    logger.info(f"User {user_id}: action={action}")

    answer_text = get_text(key = "unsupported_action", tg_id = message.from_user.id, db=db)
    
        
    if action == "create_event": 
        allowed, msg, plan = check_access(db, user_id, action_type='event')
        if not allowed:
            await message.answer(msg)   # msg уже содержит готовый текст из access.py
            return
        if language == "ru":
            with open("prompts/create_task_ru_prompt.txt", "r", encoding="utf-8") as file:
                template = file.read()
        elif language == "en":
            with open("prompts/create_task_en_prompt.txt", "r", encoding="utf-8") as file:
                template = file.read()

        filled_prompt = template.replace("[[default_remind_time]]", str(user_default_time) if user_default_time else "not specified")
        result = ai_answer(
            user_text=text,
            system_prompt=filled_prompt,
            history=last_12,
            user_offset=offset, 
            tg_id=message.from_user.id
        )
        await cost(user_id, result["response_cost"], "text_cost")
        

        answer_text = process_ai_event(
            ai_response=result["response"],
            db=db,
            user_id=user_id
        ) 


    if action == "update_event":
        events = db.select_data(
            table_name="events",
            where_conditions={"user_id": user_id}
        )
        if not events:
            answer_text = get_text(key = "no_events_update", tg_id = message.from_user.id, db=db)
        else:
            events_str = ""
            user = db.select_data("users", where_conditions={"id": user_id})
            offset = user[0][4]
            for event in events:
                event_id = event[0]
                event_text = event[2]
                start_at_utc  = event[3]

                start_at_utc_tz = start_at_utc.replace(tzinfo = timezone.utc)
                user_tz = ZoneInfo(offset)


                start_at_local = start_at_utc_tz.astimezone(user_tz)
                start_at_str = start_at_local.strftime("%Y-%m-%d %H:%M:%S")

                events_str += f"{event_id}. {event_text} в {start_at_str}\n"

            if language == "ru":
                with open("prompts/update_task_ru_prompt.txt", "r", encoding="utf-8") as file:
                    template = file.read()
            elif language == "en":
                with open("prompts/update_task_en_prompt.txt", "r", encoding="utf-8") as file:
                    template = file.read()
            filled = template.replace("{user_message}", text).replace("{events_list}", events_str)
            filled = filled.replace("[[default_remind_time]]", str(user_default_time) if user_default_time else "не указано")
            result = ai_answer(
                user_text=text,
                system_prompt=filled,
                history=last_12,
                user_offset=offset, 
                tg_id=message.from_user.id
            )
            await cost(user_id, result["response_cost"], "text_cost")
            answer_text = process_ai_event(
                ai_response=result["response"],
                db=db,
                user_id=user_id
            ) 

    if action == "delete_event":
        events = db.select_data(
            table_name="events",
            where_conditions={"user_id": user_id}
        )
        if not events:
            answer_text = get_text(key = "no_events_delete", tg_id = message.from_user.id, db=db)
        else:
            events_str = ""
            user = db.select_data("users", where_conditions={"id": user_id})
            offset = user[0][4]
            for event in events:
                event_id = event[0]
                event_text = event[2]
                start_at_utc  = event[3]

                start_at_utc_tz = start_at_utc.replace(tzinfo = timezone.utc)
                user_tz = ZoneInfo(offset)


                start_at_local = start_at_utc_tz.astimezone(user_tz)
                start_at_str = start_at_local.strftime("%Y-%m-%d %H:%M:%S")

                events_str += f"{event_id}. {event_text} в {start_at_str}\n"
            if language == "ru":
                with open("prompts/delete_task_ru_prompt.txt", "r", encoding="utf-8") as file:
                    template = file.read()
            elif language == "en":
                with open("prompts/delete_task_en_prompt.txt", "r", encoding="utf-8") as file:
                    template = file.read() 
            filled = template.replace("{user_message}", text).replace("{events_list}", events_str)
            result = ai_answer(
                user_text=text,
                system_prompt=filled,
                history=last_12,
                user_offset=offset, 
                tg_id = message.from_user.id
            )
            await cost(user_id, result["response_cost"], "text_cost")
            answer_text = process_ai_event(
                ai_response=result["response"],
                db=db,
                user_id=user_id
            ) 

    if action == "list_per_time":
        if language == "ru":
            with open("prompts/list_events_ru_prompt.txt", "r", encoding="utf-8") as file:
                prompt = file.read()
        elif language == "en":
            with open("prompts/list_events_en_prompt.txt", "r", encoding="utf-8") as file:
                prompt = file.read()
        
        result = ai_answer(
            user_text = text,
            system_prompt = prompt,
            history = last_12,
            user_offset = offset, 
            tg_id = message.from_user.id
        )
        
        await cost(user_id, result["response_cost"], "text_cost")
        answer_text = process_ai_event(
            ai_response = result["response"],
            db = db,
            user_id = user_id
        )

    if action == "daily_summary":
        answer_text = get_text(key = "daily_summary_not_implemented", tg_id = message.from_user.id, db=db)
    if action == "unsupported_multi_action":
        answer_text = ai_router_response.get("text")
    if action == "chat":
        answer_text = ai_router_response.get("text")
    if action == "question":
    # Выбираем нужный промпт по языку, определённому роутером
        if language == "ru":
            prompt_file = "prompts/question_ru_prompt.txt"
        elif language == "en":
            prompt_file = "prompts/question_en_prompt.txt"
        else:
            prompt_file = "prompts/question_ru_prompt.txt"  # fallback

        with open(prompt_file, "r", encoding="utf-8") as file:
            question_prompt = file.read()

        # Вызываем ИИ с отдельным промптом для вопросов
        result_question = ai_answer(
            user_text=text,
            system_prompt=question_prompt,
            history=last_12,
            user_offset=offset,
            tg_id=message.from_user.id
        )

        await cost(user_id, result_question["response_cost"], "text_cost")

        # Извлекаем текст ответа (предполагаем, что ответ – JSON с ключом "text")
        answer_text = result_question["response"].get("text", "") 

    
    history[user_id].append({"role": "assistant", "content": answer_text})
    await message.answer(answer_text)
    logger.info(f"User {user_id}: answer={answer_text[:100]}...")

@router.message(CalendarStates.waiting_email, lambda message: message.text)
async def process_calendar_email(message: Message, state: FSMContext):
    data = await state.get_data()
    provider = data.get("provider")
    await state.update_data(email=message.text)

    if provider == "apple":
        text = get_text(key="apple_password_prompt", tg_id=message.from_user.id, db=db)
        reply_markup = get_inline_apple_app_specific_password_link(tg_id=message.from_user.id)
    elif provider == "google":
        text = get_text(key="google_password_prompt", tg_id=message.from_user.id, db=db)
        reply_markup = get_inline_google_app_specific_password_link(tg_id=message.from_user.id)
    else:
        await message.answer("Ошибка: неизвестный провайдер")
        await state.clear()
        return

    await message.answer(text, reply_markup=reply_markup)
    await state.set_state(CalendarStates.waiting_password) 

@router.message(CalendarStates.waiting_password, lambda message: message.text)
async def process_calendar_password(message: Message, state: FSMContext):
    await state.update_data(password=message.text)
    data = await state.get_data()
    provider = data.get("provider")  # "apple" или "google"
    email = data.get("email")
    password = data.get("password")

    try:
        calendar_url = get_calendar_url(provider=provider, email=email, password=password)
        encrypted_password = CRYPT_SERVICE.encrypt(password)
        user_row = db.select_data("users", columns=["id"], where_conditions={"tg_id": message.from_user.id})
        if not user_row:
            text = get_text(key = "user_not_found", tg_id = message.from_user.id, db=db)
            await message.answer(text)
            await state.clear()
            return
        user_id = user_row[0][0]
        existing = db.select_data("users_authorizations", where_conditions={"user_id": user_id})

        if provider == "apple":
            update_data = {
                "apple_calendar_email": email,
                "apple_calendar_password": encrypted_password,
                "apple_calendar_url": calendar_url
            }
        elif provider == "google":
            update_data = {
                "google_calendar_email": email,
                "google_calendar_password": encrypted_password,
                "google_calendar_url": calendar_url
            }

        else:
            await message.answer("Неизвестный провайдер")
            await state.clear()
            return
        
        if existing:
            db.update_data(
                table_name="users_authorizations",
                data=update_data,
                where_conditions={"user_id": user_id}
            )
        else:
            update_data["user_id"] = user_id
            db.insert_data("users_authorizations", update_data)
        success_key = f"{provider}_calendar_success"
        text = get_text(key=success_key, tg_id=message.from_user.id, db=db)
        await message.answer(text)

    except Exception as e:
        logger.error(f"Error saving Apple Calendar credentials for user {message.from_user.id}: {e}")
        text = get_text(key = "apple_calendar_error", tg_id = message.from_user.id, db=db)
        await message.answer(text)

    finally:
        await state.clear()

@router.message(lambda message: message.text)
async def handle_text_message(message: Message):
    if message.from_user.id in ADMINS and message.from_user.id in waiting_for_broadcast:
        users = db.select_data("users")
        for user in users:
            try:
                await message.bot.send_message(chat_id=user[1], text=message.text)
            except Exception as e:
                logger.error(f"Error broadcasting message to user {user[1]}: {e}")
        waiting_for_broadcast.remove(message.from_user.id)
        text = get_text(key = "admin_broadcast_success", tg_id = message.from_user.id, db=db)
        await message.answer(text)
        return

    if await _save_notification_time(message):
        return
    user_id_db = db.select_data(table_name="users", where_conditions={"tg_id": message.from_user.id})

    logger.debug(f"get_text: user_id_db={user_id_db}")

    if not user_id_db:
        logger.warning(f"User {message.from_user.id} not registered, asking /start")
        text = get_text(key = "not_registered", tg_id = message.from_user.id, db=db)
        await message.answer(text)
        return
    
    user_id = user_id_db[0][0]
    logger.debug(f"user_id from DB: {user_id}")

    if not await check_user_registration(message.from_user.id):
        logger.info(f"User {message.from_user.id} needs timezone setup")
        text = get_text(key = "need_timezone", tg_id = message.from_user.id, db=db)
        await message.answer(text, reply_markup=get_time_inline_keyboard(tg_id=message.from_user.id))
        return
    
    await handle_user_input(message, message.text, user_id)
    
@router.message(lambda message: message.voice)
async def handle_voice_message(message: Message, bot: Bot):
    logger.debug(f"get_voice: user={message.from_user.id}")
    
    user_id_db = db.select_data(
        table_name="users",
        where_conditions={"tg_id": message.from_user.id}
    )

    if not user_id_db:
        text = get_text(key = "not_registered", tg_id = message.from_user.id, db=db)
        await message.answer(text)
        return

    user_id = user_id_db[0][0]

    if not await check_user_registration(message.from_user.id):
        text = get_text(key = "need_timezone", tg_id = message.from_user.id, db=db)
        await message.answer(text, reply_markup=get_time_inline_keyboard(tg_id=message.from_user.id))
        return

    allowed, msg, plan = check_access(db, user_id, action_type='voice')
    if not allowed:
        await message.answer(msg)
        return
    
    voice = message.voice
    file = await bot.get_file(voice.file_id)

    import tempfile
    import os

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg")
    local_audio_path = temp_file.name

    try:
        await bot.download_file(file.file_path, local_audio_path)
        logger.debug(f"Voice file downloaded: {local_audio_path}")
        result = await transcribe(local_audio_path)
        text = result["text"]
        error = result.get("error")
        voice_cost_rub = result["voice_cost_rub"]
        logger.info(f"Voice transcribed: {text[:50]}..., cost_rub={voice_cost_rub}")
        await cost(user_id, voice_cost_rub, "voice_cost")
        logger.debug(f"Voice cost saved: {voice_cost_rub}")
    except Exception as e:
        logger.error(f"Error processing voice: {e}", exc_info=True)
    finally:
        os.remove(local_audio_path)
        logger.debug(f"Temp file removed: {local_audio_path}")

    if not text:
        if error == "Audio duration > 2 minutes":
            text = get_text(key = "voice_too_long", tg_id = message.from_user.id, db=db)
        else:
            text = get_text(key = "voice_not_understood", tg_id = message.from_user.id, db=db)
        await message.answer(text)
        return

    await handle_user_input(message, text, user_id)

@router.message()
async def handle_other_message(message: Message):
    text = get_text(key = "unsupported_message_type", tg_id = message.from_user.id, db=db)
    await message.answer(text)