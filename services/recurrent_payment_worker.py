import asyncio
from datetime import datetime, timedelta, timezone
from logger_config import logger
from services.payment_service import (
    create_recurrent_payment,
    create_one_time_renewal_payment,
    normalize_datetime,
    AUTO_PRICE
)
from handlers.answer_texts.TEXT import get_text


async def run_recurrent_payments(db, bot):
    now = datetime.now(timezone.utc)
    # ================== 1. АВТОСПИСАНИЕ ==================
    auto_subs = db.select_data(
        "subscriptions",
        columns=["id", "user_id", "expires_at", "auto_renewal_attempted_at"],
        where_conditions={"status": "active", "auto_renewal": True}
    )

    for sub in auto_subs:
        sub_id, user_id, expires_at, last_attempt = sub
        expires_at = normalize_datetime(expires_at)
        last_attempt = normalize_datetime(last_attempt) if last_attempt else None

        if not expires_at or expires_at > now:
            continue  # ещё не истекла

        # Повторная попытка не чаще раза в сутки
        if last_attempt and (now - last_attempt) < timedelta(hours=24):
            continue

        # Получаем сохранённую карту и user_id
        user_data = db.select_data(
            "users",
            columns=["yookassa_payment_method_id", "user_id"],
            where_conditions={"id": user_id}
        )
        if not user_data:
            logger.warning(f"User {user_id} not found")
            continue

        payment_method_id, user_id = user_data[0]
        if not payment_method_id:
            logger.info(f"User {user_id} has no saved payment method")
            continue

        try:
            payment = create_recurrent_payment(user_id, payment_method_id)
            logger.info(
                f"Auto-renewal payment created: "
                f"user_id={user_id}, payment_id={payment.id}"
            )
            # Отмечаем попытку
            db.update_data(
                "subscriptions",
                {"auto_renewal_attempted_at": now.replace(tzinfo=None)},
                where_conditions={"id": sub_id}
            )
        except Exception as e:
            logger.exception(
                f"Failed to create auto-renewal for user {user_id}: {e}"
            )
            db.update_data(
                "subscriptions",
                {"auto_renewal_attempted_at": now.replace(tzinfo=None)},
                where_conditions={"id": sub_id}
            )

    # ================== 2. УВЕДОМЛЕНИЯ ЗА 3 ДНЯ ==================
    active_subs = db.select_data(
        "subscriptions",
        columns=["id", "user_id", "expires_at", "auto_renewal", "expiry_notified_at"],
        where_conditions={"status": "active"}
    )

    three_days_later = now + timedelta(days=3)

    for sub in active_subs:
        sub_id, user_id, expires_at, auto_renewal, last_notified = sub
        expires_at = normalize_datetime(expires_at)
        last_notified = normalize_datetime(last_notified) if last_notified else None

        # Если срок от 0 до 3 дней (но не истек)
        if not expires_at or expires_at <= now or expires_at > three_days_later:
            continue

        # Не чаще раза в сутки
        if last_notified and (now - last_notified) < timedelta(hours=24):
            continue

        # Получаем user_id
        user_data = db.select_data(
            "users",
            columns=["user_id"],
            where_conditions={"id": user_id}
        )
        if not user_data:
            logger.warning(f"User {user_id} not found for notification")
            continue

        user_id = user_data[0][0]

        try:
            if auto_renewal:
                text = get_text(
                    key="subscription_expiring_soon_auto",
                    db=db,
                    user_id=user_id,
                    amount=AUTO_PRICE,
                    date=expires_at.strftime("%d.%m.%Y")
                )
            else:
                # Создаём ссылку на оплату для ручного продления
                renewal_payment = create_one_time_renewal_payment(user_id, user_id)
                payment_url = renewal_payment.confirmation.confirmation_url
                text = get_text(
                    key="subscription_expiring_soon_one_time",
                    db=db,
                    user_id=user_id,
                    date=expires_at.strftime("%d.%m.%Y"),
                    payment_url=payment_url
                )

            # Асинхронная отправка сообщения
            await bot.send_message(chat_id=user_id, text=text)

            # Запоминаем, что уведомили
            db.update_data(
                "subscriptions",
                {"expiry_notified_at": now.replace(tzinfo=None)},
                where_conditions={"id": sub_id}
            )
            logger.info(f"Sent expiration notice to user {user_id}")

        except Exception as e:
            logger.exception(f"Failed to send notice to user {user_id}: {e}")