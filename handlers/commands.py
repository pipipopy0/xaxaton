import asyncio

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext

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

@command_router.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext, command: CommandObject):
    tg_id = message.from_user.id

    logger.info(f"RAW message.text: {message.text}")

    # =====================================================
    # 1. Получаем параметры из /start
    # =====================================================

    args = command.args or ""

    yclid = None
    client_id = None

    # Формат:
    # yclid_XXX_client_YYY

    if "_client_" in args:

        yclid_part, client_part = args.split(
            "_client_",
            1
        )

        if yclid_part.startswith("yclid_"):
            yclid = yclid_part[len("yclid_"):]

        if client_part:
            client_id = client_part

    elif args.startswith("client_"):

        client_id = args[len("client_"):]

    elif args.startswith("yclid_"):

        yclid = args[len("yclid_"):]

    logger.info(
        f"START params: "
        f"yclid={yclid}, "
        f"client_id={client_id}"
    )

    # =====================================================
    # 2. Проверяем пользователя
    # =====================================================

    exist = db.select_data(
        "users",
        where_conditions={"tg_id": tg_id}
    )

    user_id = exist[0][0] if exist else None

    # =====================================================
    # 3. Новый пользователь
    # =====================================================

    if not exist:

        name = message.from_user.first_name
        nickname = message.from_user.username or "no_nickname"

        user_id = db.insert_data(
            "users",
            {
                "tg_id": tg_id,
                "name": name,
                "tg_nickname": nickname,
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
            f"New user {tg_id} registered "
            f"with free subscription"
        )

    # =====================================================
    # 4. Существующий пользователь
    # =====================================================

    else:

        # Если пользователь снова пришёл с рекламными данными,
        # обновляем их.

        update_data = {}

        if yclid:
            update_data["yclid"] = yclid

        if client_id:
            update_data["metrika_client_id"] = client_id

        if update_data:

            db.update_data(
                "users",
                update_data,
                where_conditions={"tg_id": tg_id}
            )

    # =====================================================
    # 5. Отправляем start_bot в Метрику
    # =====================================================

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

    # =====================================================
    # 6. Дальше твоя исходная логика
    # =====================================================

    await state.clear()

    # Новый пользователь

    if not exist:

        text = get_text(
            db,
            "start_new",
            tg_id=tg_id
        )

        await message.answer(
            text,
            reply_markup=get_time_inline_keyboard(
                page=3,
                tg_id=tg_id
            )
        )

    # Существующий пользователь

    else:

        user = db.select_data(
            "users",
            where_conditions={"tg_id": tg_id}
        )

        if user and user[0][4] is None:

            text = get_text(
                db,
                "start_new",
                tg_id=tg_id
            )

            await message.answer(
                text,
                reply_markup=get_time_inline_keyboard(
                    page=3,
                    tg_id=tg_id
                )
            )

        else:

            is_admin = tg_id in ADMINS

            text = get_text(
                db,
                "start_registered",
                tg_id=tg_id
            )

            await message.answer(
                text,
                reply_markup=get_register_inline_keyboard(
                    is_admin=is_admin,
                    tg_id=tg_id
                )
            )
            
@command_router.message(Command("delete_data"))
async def delete_data_cmd(message: Message):
    text = get_text(key = "delete_confirmation", tg_id = message.from_user.id, db=db)
    await message.answer(text, reply_markup=get_delete_inline_keyboard(tg_id=message.from_user.id))

@command_router.message(Command("update_time"))
async def update_time_cmd(message: Message):
    text = get_text(key = "timezone_setup", tg_id = message.from_user.id, db=db)
    await message.answer(text, reply_markup=get_time_inline_keyboard(tg_id=message.from_user.id))
    
@command_router.message(Command("penis"))
async def penis_cmd(message: Message):
    text = 'penis'
    await message.answer(text)
