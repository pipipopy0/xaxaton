import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.database.work_with_dp import connect_database
from services.database.database import Database
from logger_config import logger
from aiogram.filters import Command
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


load_dotenv()

CHEQUE_BOT_TOKEN = os.getenv("CHEQUE_BOT_TOKEN")  # токен чек-бота
ADMIN_ID = int(os.getenv("tg_admin_id"))

connection = connect_database()
db = Database(connection)

bot = Bot(token=CHEQUE_BOT_TOKEN)
dp = Dispatcher()

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

@dp.message(Command("start"))
async def admin_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа")
        return

    try:
        now_moscow = datetime.now(MOSCOW_TZ)
        start_of_day = now_moscow.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        start_utc = start_of_day.astimezone(timezone.utc).replace(tzinfo=None)
        end_utc = end_of_day.astimezone(timezone.utc).replace(tzinfo=None)

        with db.connection.cursor() as cur:
            # Всего пользователей
            cur.execute("SELECT COUNT(*) FROM users")
            total_users = cur.fetchone()[0]

            # Платящих пользователей (успешные платежи)
            cur.execute("SELECT COUNT(DISTINCT user_id) FROM payments WHERE status = 'succeeded'")
            paying_users = cur.fetchone()[0]

            # Новые пользователи за сегодня (по МСК)
            cur.execute(
                "SELECT COUNT(*) FROM users WHERE created_at >= %s AND created_at < %s",
                (start_utc, end_utc)
            )
            new_today = cur.fetchone()[0]

        text = (
            f"📊 Статистика Calendator\n"
            f"Всего пользователей: {total_users}\n"
            f"Платящих пользователей: {paying_users}\n"
            f"Новых за сегодня (МСК): {new_today}"
        )
        await message.answer(text)

    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await message.answer("Ошибка при получении статистики")

async def check_pending_payments():
    """Проверяет новые платежи и отправляет уведомления админу."""
    logger.info("Запущена проверка новых платежей для уведомления админа")

    try:
        rows = db.select_data(
            "payment_notifications",
            columns=["id", "payment_id", "user_id"],
            where_conditions={"status": "pending"}
        )
    except Exception as e:
        logger.error(f"Ошибка при выборке pending уведомлений: {e}")
        return

    if not rows:
        logger.debug("Новых платежей для уведомления нет")
        db.connection.commit()
        return

    for row in rows:
        notif_id = row[0]
        payment_id = row[1]
        user_id = row[2]

        try:
            # Получаем информацию о платеже
            payment = db.select_data(
                "payments",
                columns=["amount", "paid_at"],
                where_conditions={"id": payment_id}
            )
            if not payment:
                logger.warning(f"Платёж {payment_id} не найден, пропускаем")
                continue

            amount = payment[0][0]
            paid_at = payment[0][1]

            # Получаем пользователя
            user = db.select_data(
                "users",
                columns=["user_id", "tg_nickname", "name"],
                where_conditions={"id": user_id}
            )
            if not user:
                logger.warning(f"Пользователь {user_id} не найден, пропускаем")
                continue

            user_user_id = user[0][0]
            nickname = user[0][1] or "—"
            name = user[0][2] or "—"

            text = (
                f"💰 Новый платёж!\n"
                f"Пользователь: {name} (@{nickname})\n"
                f"TG ID: {user_user_id}\n"
                f"Сумма: {amount} руб.\n"
                f"Дата: {paid_at}\n\n"
                f"Ответьте на это сообщение чеком."
            )

            msg = await bot.send_message(chat_id=ADMIN_ID, text=text)
            db.update_data(
                "payment_notifications",
                {
                    "admin_message_id": msg.message_id,
                    "status": "admin_notified",
                    "updated_at": "NOW()"
                },
                where_conditions={"id": notif_id}
            )
            
            logger.info(f"Админ уведомлён о платеже {payment_id}, message_id={msg.message_id}")

        except Exception as e:
            logger.error(f"Ошибка при обработке уведомления {notif_id}: {e}")
        
        await asyncio.sleep(0.5)

    db.connection.commit()

@dp.message(lambda message: message.reply_to_message is not None)
async def handle_cheque_reply(message: Message):
    logger.info(f"Получен ответ от админа {message.from_user.id} на сообщение {message.reply_to_message.message_id}")

    if message.from_user.id != ADMIN_ID:
        logger.warning(f"Пользователь {message.from_user.id} не админ, игнорируем")
        return

    admin_msg_id = message.reply_to_message.message_id

    try:
        rec = db.select_data(
            "payment_notifications",
            columns=["id", "user_id"],
            where_conditions={"admin_message_id": admin_msg_id}
        )
    except Exception as e:
        logger.error(f"Ошибка при поиске уведомления по admin_message_id={admin_msg_id}: {e}")
        await message.answer("Ошибка базы данных")
        return

    if not rec:
        logger.warning(f"Не найдено уведомление для admin_message_id={admin_msg_id}")
        await message.answer("Не удалось определить платёж.")
        return

    notif_id = rec[0][0]
    user_id = rec[0][1]

    # Создаём папку для чеков, если её нет
    cheques_dir = "/root/Calendator/cheques"
    os.makedirs(cheques_dir, exist_ok=True)

    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id
    elif message.text:
        # Текстовый чек
        text = message.text
        file_path = os.path.join(cheques_dir, f"cheque_{notif_id}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
        db.update_data(
            "payment_notifications",
            {
                "cheque_file_path": file_path,
                "status": "cheque_uploaded",
                "updated_at": "NOW()"
            },
            where_conditions={"id": notif_id}
        )
        logger.info(f"Текстовый чек сохранён: {file_path}")
        await message.answer("Чек сохранён и будет отправлен пользователю.")
        db.connection.commit()
        return

    if not file_id:
        logger.warning(f"Неподдерживаемый тип чека от админа {message.from_user.id}")
        await message.answer("Неподдерживаемый тип чека.")
        return

    try:
        # Получаем объект файла
        file = await bot.get_file(file_id)

        # Определяем расширение из file_path
        ext = os.path.splitext(file.file_path)[1].lower()
        if not ext:
            ext = ".jpg" if message.photo else ".pdf"

        file_path = os.path.join(cheques_dir, f"cheque_{notif_id}{ext}")

        # Скачиваем файл
        await bot.download_file(file.file_path, file_path)
        logger.info(f"Файл чека скачан: {file_path}")

        # Сохраняем путь в БД
        db.update_data(
            "payment_notifications",
            {
                "cheque_file_path": file_path,
                "status": "cheque_uploaded",
                "updated_at": "NOW()"
            },
            where_conditions={"id": notif_id}
        )
        
        logger.info(f"Чек для уведомления {notif_id} сохранён, статус обновлён на 'cheque_uploaded'")

    except Exception as e:
        logger.error(f"Ошибка при сохранении чека для уведомления {notif_id}: {e}")
        await message.answer("Ошибка при сохранении чека.")
        return

    await message.answer("Чек сохранён и будет отправлен пользователю.")
    db.connection.commit()

async def check_new_users():
    """Проверяет новых пользователей и уведомляет админа."""
    try:
        rows = db.select_data(
            "users",
            columns=["id", "user_id", "tg_nickname", "name"],
            where_conditions={"admin_notified": False}
        )
    except Exception as e:
        logger.error(f"Ошибка при выборке новых пользователей: {e}")
        return

    if not rows:
        db.connection.commit()
        return

    for row in rows:
        user_id, user_id, nickname, name = row
        nickname = nickname or "—"
        name = name or "—"

        text = (
            f"🆕 Новый пользователь!\n"
            f"Имя: {name}\n"
            f"Ник: @{nickname}\n"
            f"TG ID: {user_id}"
        )

        try:
            await bot.send_message(chat_id=ADMIN_ID, text=text)
            # Отмечаем, что уведомление отправлено
            db.update_data(
                "users",
                {"admin_notified": True},
                where_conditions={"id": user_id}
            )
            
            logger.info(f"Админ уведомлён о новом пользователе {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о пользователе {user_id}: {e}")

        await asyncio.sleep(1)

    db.connection.commit()

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_pending_payments, trigger="interval", seconds=30)
    scheduler.add_job(check_new_users, trigger="interval", seconds=60)
    scheduler.start()
    logger.info("Чек-бот запущен")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
