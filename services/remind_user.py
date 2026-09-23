import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from services.database.work_with_dp import connect_database
from services.database.database import Database
from maxapi.exceptions import MaxApiError
from logger_config import logger

async def remind_user_about_event(bot):
    while True:
        try:
            db = Database(connect_database())
            
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            
            all_pending = db.select_data(
                table_name="events_notifications",
                where_conditions={"status": "pending"}
            )
            
            notifications = []
            for n in all_pending:
                if n[2] <= now:
                    notifications.append(n)
            
            if len(notifications) > 1:
                logger.info(f"found {len(notifications)} notifications to send.")
            
            for notification in notifications:
                event_notification_id = notification[0]
                event_id = notification[1]

                event = db.select_data(
                    table_name="events",
                    where_conditions={"id": event_id}
                )
                
                if event:
                    logger.debug(f"Processing notification for event: {event}")
                    user_id = event[0][1]
                    event_text = event[0][2]
                    start_at = event[0][3]

                    user = db.select_data(
                        table_name="users",
                        where_conditions={"id": user_id}
                    )
                    
                    if user:
                        max_id = user[0][1]
                        offset = user[0][4]
                        
                        start_at = start_at.replace(tzinfo=timezone.utc)
                        user_tz = ZoneInfo(offset)
                        local_time = start_at.astimezone(user_tz)
                        local_time = local_time.strftime("%d.%m.%Y %H:%M")

                        try:
                            await bot.send_message(
                                user_id=max_id, 
                                text=f"Напоминание: {event_text} в {local_time}"
                            )
                            logger.info(f"Notification sent to user {max_id}: {event_text}")
                            
                            db.update_data(
                                table_name="events_notifications",
                                data={"status": "sent"},
                                where_conditions={"id": event_notification_id}
                            )
                            
                        except MaxApiError as e:
                            logger.error(
                                f"MAX API error while sending "
                                f"notification to user {max_id}: "
                                f"code={e.code}, raw={e.raw}"
                            )

        except Exception as e:
            logger.error(
                f"Failed to send notification "
                f"to user {max_id}: {e}",
                exc_info=True
            )

        await asyncio.sleep(30)