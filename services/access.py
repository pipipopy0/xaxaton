from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from handlers.answer_texts.TEXT import get_text
from logger_config import logger
ADMINS = set()

def is_pro_user(db, user_id):
    user_row = db.select_data(
        "users",
        columns=["user_id"],
        where_conditions={"id": user_id}
    )
    if user_row:
        max_id = user_row[0][0]
        if max_id in ADMINS:
            logger.info(f"ADMINS: {ADMINS}, max_id: {max_id}")
            return True
    subs = db.select_data(
        "subscriptions",
        where_conditions={
            "user_id": user_id,
            "status": "active"
        }
    )

    active_sub = None

    for sub in subs:
        if active_sub is None or sub[0] > active_sub[0]:
            active_sub = sub

    if not active_sub:
        return False

    plan_id = active_sub[2]
    expires_at = active_sub[5]

    if expires_at:
        if expires_at.tzinfo is None:
            if expires_at < datetime.now():
                return False
        else:
            if expires_at < datetime.now(expires_at.tzinfo):
                return False

    plan = db.select_data(
        "plans",
        where_conditions={"id": plan_id}
    )

    if not plan:
        return False

    return plan[0][1] == "pro"

def check_access(db, user_id, action_type='event'):
    """
    Проверяет, может ли пользователь создать событие или голосовое.
    action_type: 'event' или 'voice'
    Возвращает (allowed, message, plan_name)
    """

    user_row = db.select_data(
            "users",
            columns=["user_id"],
            where_conditions={"id": user_id}
        )
    if user_row:
        max_id = user_row[0][0]
        if max_id in ADMINS:
            return True, "", "pro"
    subs = db.select_data(
        "subscriptions",
        where_conditions={"user_id": user_id, "status": "active"}
    )

    active_sub = None
    for sub in subs:
        if active_sub is None or sub[0] > active_sub[0]:
            active_sub = sub
    
    plan_id = None
    if active_sub:
        plan_id = active_sub[2]          
        expires_at = active_sub[5]       
        if expires_at and expires_at < datetime.now():
            plan_id = None
    
    if not plan_id:
        free_plan = db.select_data("plans", where_conditions={"name": "free"})
        if not free_plan:
            db.insert_data("plans", {"name": "free", "events_limit": 7, "voice_limit": 2})
            free_plan = db.select_data("plans", where_conditions={"name": "free"})
        plan_id = free_plan[0][0]
    
    plan = db.select_data("plans", where_conditions={"id": plan_id})[0]
    plan_name = plan[1]          
    events_limit = plan[2]       
    voice_limit = plan[3]        
    
    if plan_name == 'pro':
        return True, "", "pro"
    
    user_data = db.select_data("users", where_conditions={"id": user_id})
    if not user_data:
        text = get_text(key = "user_not_found", max_id = user_id, db=db)
        return False, text, "free"
    max_id = user_data[0][1]
    user_offset = user_data[0][4]
    if not user_offset:
        user_offset = "UTC"
    user_tz = ZoneInfo(user_offset)
    
    now_user = datetime.now(user_tz)
    month_start = now_user.date().replace(day=1)
    next_month = month_start + timedelta(days=32)
    month_end = next_month.replace(day=1) - timedelta(days=1)
    
    usage = db.select_data(
        "usage",
        where_conditions={
            "user_id": user_id
        }
    )
    if usage:
        events_used = usage[0][2] or 0
        voice_used = usage[0][3] or 0
    else:
        db.insert_data(
            "usage",
            {
                "user_id": user_id,
                "events_created": 0,
                "voice_used": 0
            }
        )
        events_used = 0
        voice_used = 0
    
    text = get_text(key="access_denied", max_id=max_id, db=db)
    
    if action_type == 'event':
        if events_limit is not None and events_used >= events_limit:
            from services.metrika import send_metrika_event
            import asyncio
            
            user_data = db.select_data(
                "users",
                columns=["yclid", "metrika_client_id"],
                where_conditions={"id": user_id}
            )
            if user_data:
                yclid = user_data[0][0]
                client_id = user_data[0][1]
                if client_id:
                    asyncio.create_task(
                        send_metrika_event(
                            client_id=client_id,
                            target="limit_reached",
                            yclid=yclid
                        )
                    )
            return False, text, "free"
        return True, "", "free"
    elif action_type == 'voice':
        if voice_limit is not None and voice_used >= voice_limit:
            return False, text, "free"
        return True, "", "free"
    else:
        return True, "", "free"