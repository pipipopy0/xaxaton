import asyncio
import os
from aiogram.types import FSInputFile
from logger_config import logger

async def send_cheques_to_users(db, bot):
    """Отправляет готовые чеки пользователям от имени основного бота."""

    try:
        rows = db.select_data(
            "payment_notifications",
            columns=["id", "user_id", "cheque_file_path"],
            where_conditions={"status": "cheque_uploaded"}
        )
    except Exception as e:
        logger.error(f"Ошибка при выборке чеков для отправки: {e}")
        return

    if not rows:
        logger.debug("Нет готовых чеков для отправки")
        return

    for row in rows:
        notif_id = row[0]
        user_id = row[1]
        file_path = row[2]

        if not file_path or not os.path.exists(file_path):
            logger.error(f"Файл чека не найден: {file_path}")
            continue

        try:
            user = db.select_data(
                "users",
                columns=["user_id"],
                where_conditions={"id": user_id}
            )
            if not user:
                logger.warning(f"Пользователь {user_id} не найден, чек не отправлен")
                continue
            user_user_id = user[0][0]

            # Определяем тип файла по расширению
            ext = os.path.splitext(file_path)[1].lower()
            if ext in (".jpg", ".jpeg", ".png"):
                await bot.send_photo(
                    chat_id=user_user_id,
                    photo=FSInputFile(file_path),
                    caption="Ваш чек"
                )
            else:
                await bot.send_document(
                    chat_id=user_user_id,
                    document=FSInputFile(file_path),
                    caption="Ваш чек"
                )

            # Обновляем статус
            db.update_data(
                "payment_notifications",
                {"status": "sent", "updated_at": "NOW()"},
                where_conditions={"id": notif_id}
            )
            logger.info(f"Чек отправлен пользователю {user_user_id}, уведомление {notif_id}")

        except Exception as e:
            logger.error(f"Ошибка отправки чека для уведомления {notif_id}: {e}")

        await asyncio.sleep(0.3)