import asyncio
from datetime import datetime, timedelta, timezone
from logger_config import logger, debug_logger

from services.get_correct_time import parser_duckling
from services.calendars.calendar_service import create_calendar_event, update_calendar_event, delete_calendar_event
from services.google_calendar_service import create_google_calendar_event, update_google_calendar_event, delete_google_calendar_event
from services.metrika import send_metrika_event

from zoneinfo import ZoneInfo

def process_ai_event(ai_response, db, user_id):
    logger.debug(f"process_ai_event: action={ai_response.get('action')}, user_id={user_id}")
    action = ai_response["action"]

    if action == "create_event":
        return create_event(ai_response, db, user_id)
    elif action == "update_event":
        return update_event(ai_response, db, user_id)
    elif action == "delete_event":
        return delete_event(ai_response, db, user_id)
    elif action == "list_per_time":
        return select_events(ai_response, db, user_id)
    elif action == "unsupported_multi_action":
        return ai_response.get("text", "К сожалению, я не могу выполнить несколько действий одновременно.")
    elif action == "chat":
        return ai_response.get("text", "К сожалению, я не могу помочь с вопросами, не связанными с событиями.")

def _get_sync_calendars(db, user_id):
    auth = db.select_data("users_authorizations", where_conditions={"user_id": user_id})
    if not auth:
        return {}
    row = auth[0]
    result = {}

    if row[2] and row[4]:  
        result["apple"] = {"type": "app_password"}  
    
    if row[8] and row[8].strip():  
        result["google"] = {"type": "oauth"}
    elif row[6] and row[6].strip():  
        result["google"] = {"type": "app_password"}
    return result

def create_event(ai_response, db, user_id):
    logger.debug(f"create_event: user_id={user_id}, summary={ai_response.get('summary')}")

    user = db.select_data("users", where_conditions={"id": user_id})  
    offset = user[0][4]

    time_text = ai_response.get("time_text", "")
    time_type = ai_response.get("time_type", "absolute")
    
    start_at_local = parser_duckling(time_text, offset)
    if start_at_local is None:
        return "Извините, я не понял время и дату..."
    if start_at_local.tzinfo is None:
        start_at_local = start_at_local.replace(tzinfo=ZoneInfo(offset))

    start_at_utc = start_at_local.astimezone(timezone.utc)

    event_data = {
        "user_id": user_id,
        "text": ai_response["summary"],
        "start_at": start_at_utc.replace(tzinfo=None),
        "duration_min": ai_response.get("duration_min", 60)
    }

    logger.info(f"INSERT EVENT: {ai_response['summary']} at {start_at_utc}, user_id={user_id}")

    event_id = db.insert_data("events", event_data)

    now_user = datetime.now(ZoneInfo(offset))
    month_start = now_user.date().replace(day=1)
    next_month = month_start + timedelta(days=32)
    month_end = next_month.replace(day=1) - timedelta(days=1)

    existing = db.select_data(
        "usage",
        columns=["id", "events_created"],   
        where_conditions={"user_id": user_id}
    )
    if existing:
        new_count = existing[0][1] + 1
        db.update_data(
            "usage",
            {"events_created": new_count},
            where_conditions={"id": existing[0][0]}
        )
    else:
        db.insert_data(
            "usage",
            {
                "user_id": user_id,
                "events_created": 1,
                "voice_used": 0
            }
        )
    reminder_offset_minutes = ai_response.get("reminder_offset_minutes", -1)
    
    if reminder_offset_minutes > 0:
        notify_time_before = start_at_utc - timedelta(minutes=reminder_offset_minutes)
        db.insert_data("events_notifications", {
            "event_id": event_id,
            "notify_at": notify_time_before.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "before",
            "status": "pending"
        })
    
    db.insert_data("events_notifications", {
        "event_id": event_id,
        "notify_at": start_at_utc.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "at_time",
        "status": "pending"
    })

    answer = ai_response.get("answer", "Событие создано")
    if "[[DATE]]" in answer:
        date_str = start_at_local.strftime("%d.%m.%Y")
        answer = answer.replace("[[DATE]]", date_str)

    logger.info("Event add")

    calendars_event_data = {
        "text": ai_response["summary"],
        "start_at": start_at_utc.replace(tzinfo=None),
        "duration_min": ai_response.get("duration_min", 60)
    }
    calendars = _get_sync_calendars(db, user_id)
    update_fields = {}

    new_providers = []
    if "apple" in calendars:
        new_providers.append("apple")
    if "google" in calendars and calendars["google"]["type"] == "app_password":
        new_providers.append("google")
    logger.info(f"new_providers: {new_providers}")
    
    if new_providers:
        try:
            result = create_calendar_event(
                user_id=user_id,
                event_data=calendars_event_data,
                reminder_offset_minutes=reminder_offset_minutes if reminder_offset_minutes > 0 else None
            )
            for res in result:
                if res["success"]:
                    if res["provider"] == "apple":
                        update_fields["apple_event_url"] = res["url"]
                        update_fields["apple_event_uid"] = res["uid"]
                    elif res["provider"] == "google":
                        update_fields["google_event_url"] = res["url"]
                        update_fields["google_event_id"] = res["uid"]
        except Exception as e:
            logger.error(f"New module sync create error: {e}")

    if "google" in calendars and calendars["google"]["type"] == "oauth":
        logger.info("Calling create_google_calendar_event")
        try:
            google_event_url, google_event_id = create_google_calendar_event(
                user_id=user_id,
                event_data=calendars_event_data,
                reminder_offset_minutes=reminder_offset_minutes if reminder_offset_minutes > 0 else None
            )
            logger.info(f"Google OAuth result: url={google_event_url}, id={google_event_id}")
            if google_event_url and google_event_id:
                update_fields["google_event_url"] = google_event_url
                update_fields["google_event_id"] = google_event_id
        except Exception as e:
            logger.error(f"Google OAuth sync create error: {e}")

    if update_fields:
        db.update_data("events", update_fields, where_conditions={"id": event_id})  
        logger.info(f"Updated event {event_id} with fields: {update_fields}")

    user_data = db.select_data(
        "users",
        columns=["yclid", "metrika_client_id"],
        where_conditions={"id": user_id}
    )

    if user_data:
        yclid = user_data[0][0]
        client_id = user_data[0][1]

        usage_data = db.select_data(
            "usage",
            columns=["events_created"],
            where_conditions={"user_id": user_id}
        )
        event_count = usage_data[0][0] if usage_data else 0

        target = "first_event_created" if event_count == 1 else "event_created"

        if client_id:
            asyncio.create_task(
                send_metrika_event(
                    client_id=client_id,
                    target=target,
                    yclid=yclid
                )
            )
            logger.info(f"Metrika {target} sent for user {user_id}")
    
    return answer

def update_event(ai_response, db, user_id): 
    logger.debug(f"update_event: user_id={user_id}, event_id={ai_response.get('event_id')}")
    if str(ai_response.get("has_update")) != "True":
        logger.warning(f"update_event: has_update=False, answer={ai_response.get('answer')}")
        return ai_response.get("answer", "Не могу найти событие для обновления")

    event_id = ai_response.get("event_id")
    if not event_id:
        logger.error("update_event: event_id not specified")
        return "Ошибка: не указан ID события"

    old_event = db.select_data("events", where_conditions={"id": event_id, "user_id": user_id})  
    logger.info(f"old_event: {old_event[0] if old_event else None}")
    
    if not old_event:
        logger.warning(f"update_event: event {event_id} not found for user {user_id}")
        return "Событие не найдено"
    
    old_start_utc = old_event[0][3]

    user = db.select_data("users", where_conditions={"id": user_id})  
    if not user:
        return "Пользователь не найден"
    offset = user[0][4]

    update_data = {}
    if ai_response.get("summary"):
        update_data["text"] = ai_response["summary"]
    if ai_response.get("duration_min"):
        update_data["duration_min"] = ai_response["duration_min"]

    time_text = ai_response.get("time_text", "")
    if time_text:
        new_start_local = parser_duckling(time_text, offset)
        if new_start_local is None:
            return "Извините, я не понял новое время. Пожалуйста, уточните формат."
        new_start_utc = new_start_local.astimezone(timezone.utc)
        update_data["start_at"] = new_start_utc
    elif ai_response.get("start_at"):
        start_local = datetime.strptime(ai_response["start_at"], "%Y-%m-%d %H:%M:%S")
        start_local = start_local.replace(tzinfo=ZoneInfo(offset))
        new_start_utc = start_local.astimezone(timezone.utc)
        update_data["start_at"] = new_start_utc
    else:
        new_start_utc = old_start_utc

    if update_data:
        db.update_data("events", update_data, where_conditions={"id": event_id})  

    db.delete_data("events_notifications", where_conditions={"event_id": event_id})

    reminder_offset = ai_response.get("reminder_offset_minutes", -1)
    
    if reminder_offset > 0:
        notify_time_before = new_start_utc - timedelta(minutes=reminder_offset)
        db.insert_data("events_notifications", {
            "event_id": event_id,
            "notify_at": notify_time_before.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "before",
            "status": "pending"
        })
    
    db.insert_data("events_notifications", {
        "event_id": event_id,
        "notify_at": new_start_utc.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "at_time",
        "status": "pending"
    })
    
    logger.info(f"Event updated: {event_id}, new_time={new_start_utc}")

    answer = ai_response.get("answer", "Событие обновлено")
    if "[[DATE]]" in answer:
        new_start_utc_tz = new_start_utc.replace(tzinfo=timezone.utc)
        user_tz = ZoneInfo(offset)
        new_start_local = new_start_utc_tz.astimezone(user_tz)
        date_str = new_start_local.strftime("%d.%m.%Y")
        answer = answer.replace("[[DATE]]", date_str)

    calendars_event_data = {
        "text": ai_response["summary"],
        "start_at": new_start_utc.replace(tzinfo=None),
        "duration_min": ai_response.get("duration_min", 60)
    }
    reminder = reminder_offset if reminder_offset > 0 else None
    calendars = _get_sync_calendars(db, user_id)
    logger.info(f"calendars in update: {calendars}")
    apple_uid = old_event[0][7] if len(old_event[0]) > 7 else None
    google_id = old_event[0][9] if len(old_event[0]) > 9 else None
    logger.info(f"len(old_event[0]) = {len(old_event[0])}")
    logger.info(f"google_id from DB: {google_id}")
    new_providers_exist = False
    if apple_uid and "apple" in calendars:
        new_providers_exist = True
    if google_id and "google" in calendars and calendars["google"]["type"] == "app_password":
        new_providers_exist = True

    if new_providers_exist:
        try:
            update_calendar_event(
                user_id=user_id,
                event_id=event_id,
                updated_data=calendars_event_data,
                reminder_offset_minutes=reminder
            )
        except Exception as e:
            logger.error(f"New module update error: {e}")

    if google_id and "google" in calendars and calendars["google"]["type"] == "oauth":
        try:
            update_google_calendar_event(
                user_id=user_id,
                google_old_event_id=google_id,
                update_data=calendars_event_data,
                reminder_offset_minutes=reminder
            )
        except Exception as e:
            logger.error(f"Google OAuth update error: {e}")
    return answer

def delete_event(ai_response, db, user_id):
    logger.debug(f"delete_event: user_id={user_id}, event_ids={ai_response.get('event_ids')}")
    user = db.select_data("users", where_conditions={"id": user_id})
    if not user:
        return "Пользователь не найден"
    if str(ai_response.get("has_event")) != "True":
        logger.warning(f"delete_event: has_event=False, answer={ai_response.get('answer')}")
        return ai_response.get("answer", "Не могу найти событие для удаления")

    event_ids = ai_response.get("event_ids")
    if not event_ids:
        logger.error("delete_event: event_ids not specified")
        return "Ошибка: не указан ID события"

    if not isinstance(event_ids, list):
        event_ids = [event_ids]

    for event_id in event_ids:
        event_row = db.select_data("events", where_conditions={"id": event_id, "user_id": user_id})  
        if not event_row:
            logger.warning(f"Event {event_id} not found for user {user_id}")
            continue
        
        calendars = _get_sync_calendars(db, user_id)
        apple_uid = event_row[0][7] if len(event_row[0]) > 7 else None
        google_id = event_row[0][9] if len(event_row[0]) > 9 else None

        new_providers_exist = False
        if apple_uid and "apple" in calendars:
            new_providers_exist = True
        if google_id and "google" in calendars and calendars["google"]["type"] == "app_password":
            new_providers_exist = True

        if new_providers_exist:
            try:
                delete_calendar_event(user_id=user_id, event_id=event_id)
            except Exception as e:
                logger.error(f"New module delete error for event {event_id}: {e}")

        if google_id and "google" in calendars and calendars["google"]["type"] == "oauth":
            try:
                delete_google_calendar_event(user_id=user_id, event_id=google_id)
            except Exception as e:
                logger.error(f"Google OAuth delete error for event {event_id}: {e}")
        db.delete_data("events", where_conditions={"id": event_id, "user_id": user_id})  
        db.delete_data("events_notifications", where_conditions={"event_id": event_id})  
        logger.info(f"Event deleted: {event_id}")
        

    return ai_response.get("answer", "Событие удалено")

def select_events(ai_response, db, user_id):
    logger.debug(f"select_events: user_id={user_id}, time_range={ai_response.get('time_range')}")

    user = db.select_data("users", where_conditions={"id": user_id})  

    offset = user[0][4]
    user_tz = ZoneInfo(offset)

    time_range = ai_response.get("time_text", "tomorrow")
    result = parser_duckling(time_text=time_range, user_offset=offset)

    if result is None:
        return "Извините, не понял, за какой период показать события :("
    
    if isinstance(result, tuple):
        start_local = result[0]
        end_local = result[1]

        start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
        end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)

        date_start = start_local.strftime("%d.%m.%Y")
        date_end = (end_local - timedelta(days = 1)).strftime("%d.%m.%Y")

        all_events = db.select_data("events", where_conditions={"user_id": user_id})
        events = [e for e in all_events if start_utc <= e[3] < end_utc]

        if not events:
            return f"У вас нет событий с {date_start} по {date_end}"
        
        result_text = f"Ваши события с {date_start} по {date_end}\n"
        for event in events:
            event_start_utc = datetime.fromisoformat(str(event[3])).replace(tzinfo=timezone.utc)
            event_start_local = event_start_utc.astimezone(ZoneInfo(offset))
            result_text += f"• {event[2]} — {event_start_local.strftime('%d.%m.%Y %H:%M')}\n"
        
        return result_text
    else:
        target_local = result
        start_of_day = target_local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        start_utc = start_of_day.astimezone(timezone.utc).replace(tzinfo=None)
        end_utc = end_of_day.astimezone(timezone.utc).replace(tzinfo=None)

        
        all_events = db.select_data("events", where_conditions={"user_id": user_id})
        events = [e for e in all_events if start_utc <= e[3] < end_utc]

        if not events:
            return f"У вас нет событий на {target_local.strftime('%d.%m.%Y')}"

        result_text = f"Ваши события на {target_local.strftime('%d.%m.%Y')}:\n"
        for event in events:
            event_start_utc = datetime.fromisoformat(str(event[3])).replace(tzinfo=timezone.utc)
            event_start_local = event_start_utc.astimezone(ZoneInfo(offset))
            result_text += f"• {event[2]} — {event_start_local.strftime('%H:%M')}\n"
        
        return result_text