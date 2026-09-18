from services.calendars.caldav_service import CalDAVService
from services.crypto_utils import CryptographyService
import os
import caldav

key = CryptographyService(os.getenv("key_cryptography"))

db = None

def get_calendar_url(provider:str, email: str, password: str):
    if provider == "apple":
        server = "https://caldav.icloud.com"
    elif provider == "google":
        server = "https://www.google.com/calendar/dav/"
    else:
        raise ValueError("Unknown provider")
    client = caldav.DAVClient(url=server, username=email, password=password)
    principal = client.principal()
    calendars = principal.calendars()
    
    for calendar in calendars:
        url = str(calendar.url)
        if "inbox" in url or "outbox" in url or "notification" in url:
            continue
        return url
    
    raise Exception("Не найден ни один личный календарь пользователя")

def get_user_connections(user_id):
    row = db.select_data("users_authorizations", where_conditions={"user_id": user_id})
    if not row:
        return []
    user_auth = row[0]
    connections = []
    if user_auth[2]:
        connections.append({
            "provider": "apple",
            "email": user_auth[2],
            "password": key.decrypt(user_auth[3]),
            "calendar_url": user_auth[4]
        })
    if user_auth[5]:
        connections.append({
            "provider": "google",
            "email": user_auth[5],
            "password": key.decrypt(user_auth[6]),
            "calendar_url": user_auth[7]
        })
    return connections
def create_calendar_event(user_id, event_data, reminder_offset_minutes=None):
    results = []
    connections = get_user_connections(user_id=user_id)
    for connection in connections:
        service = CalDAVService(
            email=connection["email"],
            password=connection["password"],
            calendar_url=connection["calendar_url"]
        )
        try:
            result = service.create_calendar_event(event_data, reminder_offset_minutes)
            results.append({
                "provider": connection["provider"],
                "success" : True,
                "uid": result["uid"],
                "url": result["url"]
                })
        except Exception as e:
            results.append({
                "provider": connection["provider"],
                "success" : False,
                "error" : e
                })
    return results

def update_calendar_event(user_id, event_id, updated_data, reminder_offset_minutes=None):
    event = db.select_data("events", where_conditions={"id": event_id})[0]
    connections = get_user_connections(user_id=user_id)
    results = []
    for connection in connections:
        service = CalDAVService(
            email=connection["email"],
            password=connection["password"],
            calendar_url=connection["calendar_url"]
        )
        try:
            if connection["provider"] == "apple":
                if event[6] and event[7]:
                    result = service.update_event(event_url=event[6], event_uid=event[7], event_data=updated_data, reminder_offset_minutes=reminder_offset_minutes)
                    results.append({
                        "provider": "apple",
                        "success" : True,
                        "uid": result["uid"],
                        "url": result["url"]
                        })
            elif connection["provider"] == "google":
                if event[8] and event[9]:
                    result = service.update_event(event_url=event[8], event_uid=event[9], event_data=updated_data, reminder_offset_minutes=reminder_offset_minutes)
                    results.append({
                        "provider": "google",
                        "success" : True,
                        "uid": result["uid"],
                        "url": result["url"]
                        })
        except Exception as e:
            results.append({
                "provider": connection["provider"],
                "success" : False,
                "error" : e
                })
    return results

def delete_calendar_event(user_id, event_id):
    event = db.select_data("events", where_conditions={"id": event_id})
    if not event:
        raise Exception("Событие не найдено")
    event = event[0]
    connections = get_user_connections(user_id=user_id)
    results = []
    for connection in connections:
        service = CalDAVService(
            email=connection["email"],
            password=connection["password"],
            calendar_url=connection["calendar_url"]
        )
        try:
            if connection["provider"] == "apple":
                if event[6]:  
                    service.delete_event(event[6])
                    results.append({
                        "provider": "apple",
                        "success": True
                    })
            elif connection["provider"] == "google":
                if event[8]:  
                    service.delete_event(event[8])
                    results.append({
                        "provider": "google",
                        "success": True
                    })
        except Exception as e:
            results.append({
                "provider": connection["provider"],
                "success": False,
                "error": str(e)
            })
    return results