import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from maxapi import Router, F
from maxapi.enums import SenderAction
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext

from forms.calendar_fsm import CalendarStates
from services.ai_service import ai_answer
from handlers.answer_texts.TEXT import get_text

from services.event_service import process_ai_event
#from services.voice_to_text_ai import transcribe
from services.crypto_utils import CryptographyService
from services.calendars.calendar_service import get_calendar_url
from services.access import check_access

from handlers.keyboards import (
    get_time_inline_keyboard,
    get_inline_apple_app_specific_password_link,
    get_inline_google_app_specific_password_link,
)

from datetime import timezone
from logger_config import logger
from zoneinfo import ZoneInfo


router = Router()
history = {}
db = None
ADMINS = set()
CRYPT_SERVICE = CryptographyService(os.getenv("key_cryptography"))

waiting_for_broadcast = set()


async def _save_notification_time(event: MessageCreated) -> bool:
    from handlers.callback import waiting_for_time_message

    max_id = event.from_user.user_id

    if (
        max_id in waiting_for_time_message
        and waiting_for_time_message[max_id]
    ):
        try:
            notification_time = int(event.message.body.text)

            db.update_data(
                table_name="users",
                data={
                    "notification_time": notification_time
                },
                where_conditions={
                    "user_id": max_id
                }
            )

            text = get_text(
                key="notification_time_set",
                max_id=max_id,
                db=db,
                minutes=notification_time
            )

            await event.message.answer(text)

            del waiting_for_time_message[max_id]

            return True

        except ValueError:

            text = get_text(
                key="notification_time_invalid",
                max_id=max_id,
                db=db
            )

            await event.message.answer(text)

            return True

    return False


async def check_user_registration(user_id):
    user = db.select_data(
        table_name="users",
        where_conditions={"user_id": user_id}
    )

    if user and user[0][4] is not None:
        logger.debug(
            f"User {user_id} has timezone: {user[0][4]}"
        )
        return True

    logger.debug(
        f"User {user_id} has no timezone set"
    )

    return False


async def cost(user_id, response_cost, column_name):
    logger.debug(
        f"cost: user_id={user_id}, "
        f"cost={response_cost}, "
        f"column={column_name}"
    )

    cost_record = db.select_data(
        "users_costs",
        where_conditions={"user_id": user_id}
    )

    if cost_record:
        old_cost = float(
            cost_record[0][2]
            if column_name == "text_cost"
            else cost_record[0][3]
        )

        new_cost = old_cost + response_cost
        new_all_cost = float(cost_record[0][4]) + response_cost

        db.update_data(
            "users_costs",
            {
                column_name: new_cost,
                "all_cost": new_all_cost
            },
            where_conditions={"user_id": user_id}
        )

    else:
        db.insert_data(
            "users_costs",
            {
                "user_id": user_id,
                column_name: float(response_cost),
                "all_cost": float(response_cost)
            }
        )

    logger.info(
        f"Cost updated for user {user_id}: "
        f"{column_name} += {response_cost}"
    )


async def handle_user_input(event: MessageCreated, text: str, user_id):
    logger.info(
        f"User {user_id} sent: {text[:200]}"
    )

    user = db.select_data(
        "users",
        where_conditions={"id": user_id}
    )

    offset = (
        user[0][4]
        if user and user[0][4]
        else "UTC"
    )

    user_default_time = (
        user[0][6]
        if user and len(user[0]) > 6
        else None
    )

    logger.debug(
        f"User offset: {offset}"
    )

    logger.debug(
        f"User default time: {user_default_time}"
    )

    await event.message.action(
        SenderAction.TYPING_ON
    )

    if user_id not in history:
        history[user_id] = []

    history[user_id].append(
        {
            "role": "user",
            "content": text
        }
    )

    last_12 = history[user_id][-12:]

    max_id = event.from_user.user_id

    result = ai_answer(
        user_text=text,
        system_prompt="intemt_router_prompt.txt",
        history=last_12,
        user_offset=offset,
        max_id=max_id
    )

    ai_router_response = result["response"]
    response_cost = result["response_cost"]

    await cost(
        user_id,
        response_cost,
        "text_cost"
    )

    action = ai_router_response.get("action")
    language = ai_router_response.get("language", "ru")

    logger.info(
        f"User {user_id}: action={action}"
    )

    answer_text = get_text(
        key="unsupported_action",
        max_id=max_id,
        db=db
    )

    if action == "create_event":

        allowed, msg, plan = check_access(
            db,
            user_id,
            action_type="event"
        )

        if not allowed:
            await event.message.answer(msg)
            return

        if language == "ru":

            with open(
                "prompts/create_task_ru_prompt.txt",
                "r",
                encoding="utf-8"
            ) as file:
                template = file.read()

        elif language == "en":

            with open(
                "prompts/create_task_en_prompt.txt",
                "r",
                encoding="utf-8"
            ) as file:
                template = file.read()

        filled_prompt = template.replace(
            "[[default_remind_time]]",
            (
                str(user_default_time)
                if user_default_time
                else "not specified"
            )
        )

        result = ai_answer(
            user_text=text,
            system_prompt=filled_prompt,
            history=last_12,
            user_offset=offset,
            max_id=max_id
        )

        await cost(
            user_id,
            result["response_cost"],
            "text_cost"
        )

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

            answer_text = get_text(
                key="no_events_update",
                max_id=max_id,
                db=db
            )

        else:

            events_str = ""

            user = db.select_data(
                "users",
                where_conditions={"id": user_id}
            )

            offset = user[0][4]

            for event_row in events:

                event_id = event_row[0]
                event_text = event_row[2]
                start_at_utc = event_row[3]

                start_at_utc_tz = start_at_utc.replace(
                    tzinfo=timezone.utc
                )

                user_tz = ZoneInfo(offset)

                start_at_local = (
                    start_at_utc_tz.astimezone(user_tz)
                )

                start_at_str = start_at_local.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                events_str += (
                    f"{event_id}. "
                    f"{event_text} "
                    f"в {start_at_str}\n"
                )

            if language == "ru":

                with open(
                    "prompts/update_task_ru_prompt.txt",
                    "r",
                    encoding="utf-8"
                ) as file:
                    template = file.read()

            elif language == "en":

                with open(
                    "prompts/update_task_en_prompt.txt",
                    "r",
                    encoding="utf-8"
                ) as file:
                    template = file.read()

            filled = (
                template
                .replace("{user_message}", text)
                .replace("{events_list}", events_str)
            )

            filled = filled.replace(
                "[[default_remind_time]]",
                (
                    str(user_default_time)
                    if user_default_time
                    else "не указано"
                )
            )

            result = ai_answer(
                user_text=text,
                system_prompt=filled,
                history=last_12,
                user_offset=offset,
                max_id=max_id
            )

            await cost(
                user_id,
                result["response_cost"],
                "text_cost"
            )

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

            answer_text = get_text(
                key="no_events_delete",
                max_id=max_id,
                db=db
            )

        else:

            events_str = ""

            user = db.select_data(
                "users",
                where_conditions={"id": user_id}
            )

            offset = user[0][4]

            for event_row in events:

                event_id = event_row[0]
                event_text = event_row[2]
                start_at_utc = event_row[3]

                start_at_utc_tz = start_at_utc.replace(
                    tzinfo=timezone.utc
                )

                user_tz = ZoneInfo(offset)

                start_at_local = (
                    start_at_utc_tz.astimezone(user_tz)
                )

                start_at_str = start_at_local.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                events_str += (
                    f"{event_id}. "
                    f"{event_text} "
                    f"в {start_at_str}\n"
                )

            if language == "ru":

                with open(
                    "prompts/delete_task_ru_prompt.txt",
                    "r",
                    encoding="utf-8"
                ) as file:
                    template = file.read()

            elif language == "en":

                with open(
                    "prompts/delete_task_en_prompt.txt",
                    "r",
                    encoding="utf-8"
                ) as file:
                    template = file.read()

            filled = (
                template
                .replace("{user_message}", text)
                .replace("{events_list}", events_str)
            )

            result = ai_answer(
                user_text=text,
                system_prompt=filled,
                history=last_12,
                user_offset=offset,
                max_id=max_id
            )

            await cost(
                user_id,
                result["response_cost"],
                "text_cost"
            )

            answer_text = process_ai_event(
                ai_response=result["response"],
                db=db,
                user_id=user_id
            )

 
    if action == "list_per_time":

        if language == "ru":

            with open(
                "prompts/list_events_ru_prompt.txt",
                "r",
                encoding="utf-8"
            ) as file:
                prompt = file.read()

        elif language == "en":

            with open(
                "prompts/list_events_en_prompt.txt",
                "r",
                encoding="utf-8"
            ) as file:
                prompt = file.read()

        result = ai_answer(
            user_text=text,
            system_prompt=prompt,
            history=last_12,
            user_offset=offset,
            max_id=max_id
        )

        await cost(
            user_id,
            result["response_cost"],
            "text_cost"
        )

        answer_text = process_ai_event(
            ai_response=result["response"],
            db=db,
            user_id=user_id
        )


    if action == "daily_summary":

        answer_text = get_text(
            key="daily_summary_not_implemented",
            max_id=max_id,
            db=db
        )

    if action == "unsupported_multi_action":

        answer_text = ai_router_response.get("text")

    if action == "chat":

        answer_text = ai_router_response.get("text")

    if action == "question":

        if language == "ru":
            prompt_file = "prompts/question_ru_prompt.txt"

        elif language == "en":
            prompt_file = "prompts/question_en_prompt.txt"

        else:
            prompt_file = "prompts/question_ru_prompt.txt"

        with open(
            prompt_file,
            "r",
            encoding="utf-8"
        ) as file:
            question_prompt = file.read()

        result_question = ai_answer(
            user_text=text,
            system_prompt=question_prompt,
            history=last_12,
            user_offset=offset,
            max_id=max_id
        )

        await cost(
            user_id,
            result_question["response_cost"],
            "text_cost"
        )

        answer_text = (
            result_question["response"]
            .get("text", "")
        )

    history[user_id].append(
        {
            "role": "assistant",
            "content": answer_text
        }
    )

    await event.message.answer(answer_text)

    logger.info(
        f"User {user_id}: "
        f"answer={answer_text[:100]}..."
    )

@router.message_created(
    CalendarStates.waiting_email,
    F.message.body.text
)
async def process_calendar_email(
    event: MessageCreated,
    context: MemoryContext
):
    data = await context.get_data()

    provider = data.get("provider")

    email = event.message.body.text

    await context.update_data(
        email=email
    )

    max_id = event.from_user.user_id

    if provider == "apple":

        text = get_text(
            key="apple_password_prompt",
            max_id=max_id,
            db=db
        )

        reply_markup = (
            get_inline_apple_app_specific_password_link(
                max_id=max_id
            )
        )

    elif provider == "google":

        text = get_text(
            key="google_password_prompt",
            max_id=max_id,
            db=db
        )

        reply_markup = (
            get_inline_google_app_specific_password_link(
                max_id=max_id
            )
        )

    else:

        await event.message.answer(
            "Ошибка: неизвестный провайдер"
        )

        await context.clear()

        return

    await event.message.answer(
        text,
        attachments=[reply_markup]
    )

    await context.set_state(
        CalendarStates.waiting_password
    )

@router.message_created(
    CalendarStates.waiting_password,
    F.message.body.text
)
async def process_calendar_password(
    event: MessageCreated,
    context: MemoryContext
):
    password = event.message.body.text

    await context.update_data(
        password=password
    )

    data = await context.get_data()

    provider = data.get("provider")
    email = data.get("email")

    max_id = event.from_user.user_id

    try:

        calendar_url = get_calendar_url(
            provider=provider,
            email=email,
            password=password
        )

        encrypted_password = CRYPT_SERVICE.encrypt(
            password
        )

        user_row = db.select_data(
            "users",
            columns=["id"],
            where_conditions={"user_id": max_id}
        )

        if not user_row:

            text = get_text(
                key="user_not_found",
                max_id=max_id,
                db=db
            )

            await event.message.answer(text)

            await context.clear()

            return

        user_id = user_row[0][0]

        existing = db.select_data(
            "users_authorizations",
            where_conditions={
                "user_id": user_id
            }
        )

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

            await event.message.answer(
                "Неизвестный провайдер"
            )

            await context.clear()

            return

        if existing:

            db.update_data(
                table_name="users_authorizations",
                data=update_data,
                where_conditions={
                    "user_id": user_id
                }
            )

        else:

            update_data["user_id"] = user_id

            db.insert_data(
                "users_authorizations",
                update_data
            )

        success_key = (
            f"{provider}_calendar_success"
        )

        text = get_text(
            key=success_key,
            max_id=max_id,
            db=db
        )

        await event.message.answer(text)

    except Exception as e:

        logger.error(
            f"Error saving calendar credentials "
            f"for user {max_id}: {e}"
        )

        text = get_text(
            key="apple_calendar_error",
            max_id=max_id,
            db=db
        )

        await event.message.answer(text)

    finally:

        await context.clear()

@router.message_created(F.message.body.text)
async def handle_text_message(
    event: MessageCreated
):
    max_id = event.from_user.user_id

    text = event.message.body.text

    if (
        max_id in ADMINS
        and max_id in waiting_for_broadcast
    ):
        users = db.select_data("users")

        for user in users:

            try:

                await event.bot.send_message(
                    chat_id=user[1],
                    text=text
                )

            except Exception as e:

                logger.error(
                    f"Error broadcasting message "
                    f"to user {user[1]}: {e}"
                )

        waiting_for_broadcast.remove(max_id)

        success_text = get_text(
            key="admin_broadcast_success",
            max_id=max_id,
            db=db
        )

        await event.message.answer(
            success_text
        )

        return
    
    if await _save_notification_time(event):
        return

    user_id_db = db.select_data(
        table_name="users",
        where_conditions={"user_id": max_id}
    )

    logger.debug(
        f"get_text: user_id_db={user_id_db}"
    )

    if not user_id_db:

        logger.warning(
            f"User {max_id} not registered, "
            f"asking /start"
        )

        text = get_text(
            key="not_registered",
            max_id=max_id,
            db=db
        )

        await event.message.answer(text)

        return

    user_id = user_id_db[0][0]

    logger.debug(
        f"user_id from DB: {user_id}"
    )

    if not await check_user_registration(max_id):

        logger.info(
            f"User {max_id} needs timezone setup"
        )

        text = get_text(
            key="need_timezone",
            max_id=max_id,
            db=db
        )

        keyboard = get_time_inline_keyboard(
            max_id=max_id
        )

        await event.message.answer(
            text,
            attachments=[keyboard]
        )

        return

    await handle_user_input(
        event,
        text,
        user_id
    )

# def _is_audio_message(event: MessageCreated) -> bool:
#     body = event.message.body

#     if body is None:
#         return False

#     attachments = body.attachments or []

#     return any(
#         getattr(attachment.type, "value", attachment.type) == "audio"
#         for attachment in attachments
#     )


# @router.message_created(
#     lambda event: _is_audio_message(event)
# )
# async def handle_voice_message(
#     event: MessageCreated
# ):
#     max_id = event.from_user.user_id

#     logger.debug(
#         f"get_audio: user={max_id}"
#     )

#     user_id_db = db.select_data(
#         table_name="users",
#         where_conditions={"user_id": max_id}
#     )

#     if not user_id_db:

#         text = get_text(
#             key="not_registered",
#             max_id=max_id,
#             db=db
#         )

#         await event.message.answer(text)

#         return

#     user_id = user_id_db[0][0]

#     if not await check_user_registration(max_id):

#         text = get_text(
#             key="need_timezone",
#             max_id=max_id,
#             db=db
#         )

#         keyboard = get_time_inline_keyboard(
#             max_id=max_id
#         )

#         await event.message.answer(
#             text,
#             attachments=[keyboard]
#         )

#         return

#     allowed, msg, plan = check_access(
#         db,
#         user_id,
#         action_type="voice"
#     )

#     if not allowed:

#         await event.message.answer(msg)

#         return

#     body = event.message.body

#     attachments = body.attachments or []

#     audio_attachment = next(
#         (
#             attachment
#             for attachment in attachments
#             if getattr(
#                 attachment.type,
#                 "value",
#                 attachment.type
#             ) == "audio"
#         ),
#         None
#     )

#     if audio_attachment is None:

#         logger.error(
#             f"Audio attachment not found "
#             f"for user {max_id}"
#         )

#         return

#     if audio_attachment.payload is None:

#         logger.error(
#             f"Audio payload is missing "
#             f"for user {max_id}"
#         )

#         text = get_text(
#             key="voice_not_understood",
#             max_id=max_id,
#             db=db
#         )

#         await event.message.answer(text)

#         return

#     audio_url = getattr(
#         audio_attachment.payload,
#         "url",
#         None
#     )

#     if not audio_url:

#         logger.error(
#             f"Audio URL is missing "
#             f"for user {max_id}"
#         )

#         text = get_text(
#             key="voice_not_understood",
#             max_id=max_id,
#             db=db
#         )

#         await event.message.answer(text)

#         return

#     url_path = urlparse(audio_url).path

#     extension = Path(
#         url_path
#     ).suffix.lower()

#     if not extension:
#         extension = ".ogg"

#     temp_file = tempfile.NamedTemporaryFile(
#         delete=False,
#         suffix=extension
#     )

#     local_audio_path = temp_file.name

#     temp_file.close()

#     text = None
#     error = None
#     voice_cost_rub = 0

#     try:

#         session = await event.bot.ensure_session()

#         async with session.get(audio_url) as response:

#             response.raise_for_status()

#             with open(
#                 local_audio_path,
#                 "wb"
#             ) as file:

#                 async for chunk in response.content.iter_chunked(
#                     1024 * 1024
#                 ):
#                     file.write(chunk)

#         logger.debug(
#             f"Audio file downloaded: "
#             f"{local_audio_path}"
#         )

#         result = await transcribe(
#             local_audio_path
#         )

#         text = result.get("text")
#         error = result.get("error")

#         voice_cost_rub = result.get(
#             "voice_cost_rub",
#             0
#         )

#         logger.info(
#             f"Voice transcribed: "
#             f"{(text or '')[:50]}..., "
#             f"cost_rub={voice_cost_rub}"
#         )

#         await cost(
#             user_id,
#             voice_cost_rub,
#             "voice_cost"
#         )

#         logger.debug(
#             f"Voice cost saved: "
#             f"{voice_cost_rub}"
#         )

#     except Exception as e:

#         logger.error(
#             f"Error processing voice: {e}",
#             exc_info=True
#         )

#     finally:

#         try:

#             os.remove(
#                 local_audio_path
#             )

#             logger.debug(
#                 f"Temp file removed: "
#                 f"{local_audio_path}"
#             )

#         except FileNotFoundError:
#             pass


#     if not text:

#         if error == "Audio duration > 2 minutes":

#             text = get_text(
#                 key="voice_too_long",
#                 max_id=max_id,
#                 db=db
#             )

#         else:

#             text = get_text(
#                 key="voice_not_understood",
#                 max_id=max_id,
#                 db=db
#             )

#         await event.message.answer(text)

#         return

#     await handle_user_input(
#         event,
#         text,
#         user_id
#     )

@router.message_created()
async def handle_other_message(
    event: MessageCreated
):
    max_id = event.from_user.user_id

    text = get_text(
        key="unsupported_message_type",
        max_id=max_id,
        db=db
    )

    await event.message.answer(text)

@router.message_created()
async def audio_message(
    event: MessageCreated
):
    max_id = event.from_user.user_id
    
    text = get_text(
        key="unsupported_message_type",
        max_id=max_id,
        db=db
    )
    
    await event.message.answer(text)