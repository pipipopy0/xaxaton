import os
import requests
import secrets
from dotenv import load_dotenv
from datetime import timedelta, datetime, timezone

from logger_config import logger

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_GOOGLE_ID")
CLIENT_SECRET = os.getenv("CLIENT_GOOGLE_SECRET")
REDIRECT_URL = os.getenv("REDIRECT_URI")
DEVICE_CODE_URL = os.getenv("DEVICE_CODE_URL")
TOKEN_URI = os.getenv("TOKEN_URI")

db = None

def request_device_code(user_id):
    data = {
        "client_id": CLIENT_ID,
        "scope": "https://www.googleapis.com/auth/calendar",
    }
    r = requests.post(DEVICE_CODE_URL, data=data)
    r.raise_for_status()

    return r.json()

def _get_valid_access_token(user_id):
    refresh_token = db.select_data(
        "users_authorizations",
        columns = ["google_calendar_refresh_token"],
        where_conditions = {"user_id": user_id}
    )
    logger.info(f"refresh_token from DB: {refresh_token[0][0] if refresh_token else 'None'}")

    if not refresh_token or not refresh_token[0][0]:
        logger.warning(f"Пользователь{user_id} не привязал или не получил refresh_token")
        return None
    refresh_token = refresh_token[0][0]

    data = {
        "client_id": CLIENT_ID,
        "client_secret" : CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type" : "refresh_token",
    }
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data=data
    )
    logger.info(f"Token response status: {r.status_code}, body: {r.text}")

    tokens = r.json()
    access_token = tokens.get("access_token")

    return access_token

def _authorize(access_token):
    
    headers_put = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    return headers_put

def _parameterize_event_data(event_data, reminder_offset_minutes = None):

    start_time = event_data["start_at"]
    duration_min = event_data.get("duration_min", 60)
    end_time = (start_time + timedelta(minutes=duration_min))
    summary = event_data.get("text", "Событие")

    start_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    event_body = {
        "summary": summary,
        "start": {
            "dateTime": start_str,
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_str,
            "timeZone": "UTC"
    }
}
    if reminder_offset_minutes is not None and reminder_offset_minutes > 0:
        event_body['reminders'] = {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': reminder_offset_minutes},
            ]
        }

    return event_body

def create_google_calendar_event(user_id, event_data, reminder_offset_minutes = None):

    access_token = _get_valid_access_token(user_id)

    if not access_token:
        logger.error(f"Не удалось получть access_token для user_id: {user_id}")
        return None, None
    
    calendar_url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    event_body = _parameterize_event_data(event_data = event_data, reminder_offset_minutes = reminder_offset_minutes)
    headers_post  = _authorize(access_token=access_token)

    try:
        response = requests.post(calendar_url, headers=headers_post, json=event_body)
        result = response.json()
        logger.info(f"Create event response status: {response.status_code}, body: {response.text}")

        if 200 <= response.status_code < 300:
            logger.info(f"Событие для пользователя user_id: {user_id} добавлено в Google Calendar")
            google_event_url, google_event_id = result.get('htmlLink'), result.get('id')
            return google_event_url, google_event_id
        else:
            logger.error(f"Ошибка Google API: {result}")
            return None, None
            
    except Exception as e:
        logger.error(f"Исключение при создании события: {e}")
        return None, None

def update_google_calendar_event(user_id, google_old_event_id, update_data, reminder_offset_minutes = None):

    access_token = _get_valid_access_token(user_id)
    
    if not access_token:
        logger.error(f"Не удалось получть access_token для user_id: {user_id}")
        return None, None
    

    event_body = _parameterize_event_data(event_data = update_data, reminder_offset_minutes = reminder_offset_minutes)
    headers_put  = _authorize(access_token=access_token)

    calendar_url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{google_old_event_id}"

    try:
        response = requests.patch(calendar_url, headers=headers_put, json=event_body)
        result = response.json()

        if 200 <= response.status_code < 300:
            logger.info(f"Событие {google_old_event_id} для пользователя user_id: {user_id} обновлено в Google Calendar")
            google_event_url, google_event_id = result.get('htmlLink'), result.get('id')
            return google_event_url, google_event_id
           
        else:
            logger.error(f"Ошибка Google API: {result}")
            return None, None
            
    except Exception as e:
        logger.error(f"Исключение при обнолвении: {e}")
        return None, None

def delete_google_calendar_event(user_id, event_id):

    access_token = _get_valid_access_token(user_id)

    if not access_token:
        logger.error(f"Не удалось получть access_token для user_id: {user_id}")
        return False
    
    headers  = _authorize(access_token=access_token)
    calendar_url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}"

    try:
        response = requests.delete(calendar_url, headers=headers)
        if 200 <= response.status_code < 300:
            logger.info(f"Событие {event_id} для пользователя user_id: {user_id} удалено в Google Calendar")
            return True
        else:
            logger.error(f"Ошибка Google API: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Исключение при обнолвении: {e}")
        return False