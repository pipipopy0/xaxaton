import asyncio

from maxapi import Router
from maxapi import context
from maxapi.context import MemoryContext
from maxapi.types import MessageCreated, Command

from handlers.answer_texts.TEXT import get_text
from handlers.keyboards import(
    get_admin_inline_keyboard,
    get_register_inline_keyboard,
    get_time_inline_keyboard,
    get_delete_inline_keyboard, 
    
)
from handlers.router import ADMINS

from datetime import datetime, timedelta
from logger_config import logger

from services.metrika import send_metrika_event

command_router = Router()
db = None

@command_router.message_created(Command("start"))
async def start_cmd(event: MessageCreated, context: MemoryContext, args: list[str]):
    max_id = event.from_user.user_id

    logger.info(f"RAW message.text: {event.message.body.text}")
    start_args = " ".join(args)

    yclid = None
    client_id = None
    if "_client_" in start_args:

        yclid_part, client_part = start_args.split(
            "_client_",
            1
        )

        if yclid_part.startswith("yclid_"):
            yclid = yclid_part[len("yclid_"):]

        if client_part:
            client_id = client_part

    elif start_args.startswith("client_"):

        client_id = start_args[len("client_"):]

    elif start_args.startswith("yclid_"):

        yclid = start_args[len("yclid_"):]

    logger.info(
        f"START params: "
        f"yclid={yclid}, "
        f"client_id={client_id}"
    )

    exist = db.select_data(
        "users",
        where_conditions={"user_id": max_id}
    )

    user_id = exist[0][0] if exist else None


    if not exist:

        name = event.from_user.first_name
        nickname = event.from_user.username or "no_nickname"

        user_id = db.insert_data(
            "users",
            {
                "user_id": max_id,
                "name": name,
                "max_nickname": nickname,
                "yclid": yclid,
                "metrika_client_id": client_id,
                "admin_notified": False   
            }
        )

        free_plan = db.select_data(
            "plans",
            where_conditions={"name": "free"}
        )

        if free_plan:

            db.insert_data(
                "subscriptions",
                {
                    "user_id": user_id,
                    "plan_id": free_plan[0][0],
                    "status": "active"
                }
            )

        db.insert_data(
            "usage",
            {
                "user_id": user_id,
                "events_created": 0,
                "voice_used": 0
            }
        )

        logger.info(
            f"New user {max_id} registered "
            f"with free subscription"
        )
    else:

        update_data = {}

        if yclid:
            update_data["yclid"] = yclid

        if client_id:
            update_data["metrika_client_id"] = client_id

        if update_data:

            db.update_data(
                "users",
                update_data,
                where_conditions={"user_id": max_id}
            )

    if yclid or client_id:

        try:

            result = await send_metrika_event(
                client_id=client_id,
                target="start_bot",
                yclid=yclid
            )

            logger.info(
                f"Metrika start_bot result: {result}"
            )

        except Exception:

            logger.exception(
                "Failed to send start_bot to Metrika"
            )

    else:

        logger.info(
            "No yclid/client_id — "
            "Metrika start_bot skipped"
        )

    await context.clear()

    if not exist:

        text = get_text(
            db,
            "start_new",
            max_id=max_id
        )

        await event.message.answer(
            text,
            attachments=[get_time_inline_keyboard(
                page=3,
                max_id=max_id
            )]
        )

    # Существующий пользователь

    else:

        user = db.select_data(
            "users",
            where_conditions={"user_id": max_id}
        )

        if user and user[0][4] is None:

            text = get_text(
                db,
                "start_new",
                max_id=max_id
            )

            await event.message.answer(
                text,
                attachments=[get_time_inline_keyboard(
                    page=3,
                    max_id=max_id
                )]
            )

        else:

            is_admin = max_id in ADMINS

            text = get_text(
                db,
                "start_registered",
                max_id=max_id
            )

            await event.message.answer(
                text,
                attachments=[get_register_inline_keyboard(
                    is_admin=is_admin,
                    max_id=max_id
                )]
            )
            
@command_router.message_created(Command("delete_data"))
async def delete_data_cmd(event: MessageCreated):
    text = get_text(key = "delete_confirmation", max_id = event.from_user.user_id, db=db)
    await event.message.answer(text, attachments=[get_delete_inline_keyboard(max_id=event.from_user.user_id)])

@command_router.message_created(Command("update_time"))
async def update_time_cmd(event: MessageCreated):
    text = get_text(key = "timezone_setup", max_id = event.from_user.user_id, db=db)
    await event.message.answer(text, attachments=[get_time_inline_keyboard(max_id=event.from_user.user_id)])

@command_router.message_created(Command("penis"))
async def penis_cmd(event: MessageCreated):
    text = 'is very big'
    await event.message.answer(text)

@command_router.message_created(Command("menu"))
async def menu_cmd(event: MessageCreated, context: MemoryContext, args: list[str]):
    await start_cmd(event, context=context, args=args)
