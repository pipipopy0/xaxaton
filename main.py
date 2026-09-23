import asyncio
from os import getenv
from dotenv import load_dotenv
from maxapi import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

import handlers.callback
import handlers.router
import services.google_calendar_service
import services.calendars.calendar_service

from handlers.router import router
from handlers.callback import callback_router
from handlers.commands import command_router
from services.database.work_with_dp import connect_database, create_tables
from services.database.database import Database
from services.recurrent_payment_worker import run_recurrent_payments
from services.remind_user import remind_user_about_event


TOKEN = getenv("MAX_BOT_API")

admin_id = int(getenv("tg_admin_id"))

connection = connect_database()
db = Database(connection)

services.calendars.calendar_service.db = db
services.google_calendar_service.db = db
handlers.callback.db = db
handlers.router.db = db
handlers.router.ADMINS.add(admin_id)
services.access.ADMINS.add(admin_id)
handlers.commands.db = db
handlers.keyboards.db = db
dp = Dispatcher()

dp.include_routers(command_router, router, callback_router)


async def main():
    bot = Bot(token=TOKEN)
    create_tables()
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_recurrent_payments,
        trigger="interval", 
        minutes=1,
        args=(db, bot)
    )
    # scheduler.add_job(
    #     send_cheques_to_users,
    #     trigger="interval",
    #     seconds=30,
    #     args=(db, bot)
    # )
    scheduler.start()

    asyncio.create_task(remind_user_about_event(bot))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())