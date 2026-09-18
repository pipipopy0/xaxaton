import uuid
from datetime import datetime, timedelta, timezone

from yookassa import Payment
from services.yookassa_client import Configuration
from logger_config import logger


ONE_TIME_PRICE = "249.00"
AUTO_PRICE = "229.00"

PRO_PLAN_ID = 2
SUBSCRIPTION_DAYS = 30

RETURN_URL = "https://telegram.me/xrosobot"


def now_utc():
    return datetime.now(timezone.utc)


def normalize_datetime(dt):
    if dt is None:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def parse_yookassa_datetime(value):
    """
    Преобразует дату ЮKassa вида:
    2026-08-12T12:35:52.185918Z
    в timezone-aware datetime UTC.
    """

    if not value:
        return now_utc()

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).astimezone(timezone.utc)
    except Exception:
        return now_utc()


# ============================================================
# ПЕРВАЯ РАЗОВАЯ ОПЛАТА — 249 ₽
# ============================================================

def create_first_payment(user_id: int, tg_id: int):
    """
    Обычная разовая подписка.
    Карта НЕ сохраняется.
    """

    return Payment.create(
        {
            "amount": {
                "value": ONE_TIME_PRICE,
                "currency": "RUB"
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": RETURN_URL
            },
            "description": (
                f"Pro на 30 суток для пользователя {tg_id}"
            ),
            "save_payment_method": False,
            "metadata": {
                "user_id": str(user_id),
                "payment_type": "first_one_time"
            }
        },
        str(uuid.uuid4())
    )


# ============================================================
# ПЕРВАЯ ОПЛАТА С АВТОПРОДЛЕНИЕМ — 229 ₽
# ============================================================

def create_auto_payment(user_id: int, tg_id: int):
    """
    Первая оплата тарифа с автопродлением.
    Способ оплаты сохраняется.
    """

    return Payment.create(
        {
            "amount": {
                "value": AUTO_PRICE,
                "currency": "RUB"
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": RETURN_URL
            },
            "description": (
                f"Pro с автопродлением для пользователя {tg_id}"
            ),
            "save_payment_method": True,
            "metadata": {
                "user_id": str(user_id),
                "payment_type": "first_auto"
            }
        },
        str(uuid.uuid4())
    )


# ============================================================
# РУЧНОЕ ПРОДЛЕНИЕ — 249 ₽
# ============================================================

def create_one_time_renewal_payment(user_id: int, tg_id: int):
    """
    Ручное продление без автопродления.
    """

    return Payment.create(
        {
            "amount": {
                "value": ONE_TIME_PRICE,
                "currency": "RUB"
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": RETURN_URL
            },
            "description": (
                f"Продление Pro на 30 суток для пользователя {tg_id}"
            ),
            "save_payment_method": False,
            "metadata": {
                "user_id": str(user_id),
                "payment_type": "renewal_one_time"
            }
        },
        str(uuid.uuid4())
    )


# ============================================================
# АВТОСПИСАНИЕ — 199 ₽
# ============================================================

def create_recurrent_payment(
    user_id: int,
    payment_method_id: str
):
    """
    Создаёт автосписание по сохранённой карте.
    """

    return Payment.create(
        {
            "amount": {
                "value": AUTO_PRICE,
                "currency": "RUB"
            },
            "capture": True,
            "payment_method_id": payment_method_id,
            "description": (
                f"Автопродление Pro для пользователя {user_id}"
            ),
            "metadata": {
                "user_id": str(user_id),
                "payment_type": "renewal_auto"
            }
        },
        str(uuid.uuid4())
    )


# ============================================================
# АКТИВАЦИЯ ПЕРВОЙ ПОДПИСКИ
# ============================================================

def activate_subscription(db, user_id: int, paid_at, auto_renewal: bool):
    paid_at = normalize_datetime(paid_at)
    expires_at = paid_at + timedelta(days=SUBSCRIPTION_DAYS)

    # Закрываем старые активные подписки
    db.update_data(
        "subscriptions",
        {"status": "expired"},
        where_conditions={
            "user_id": user_id,
            "status": "active"
        }
    )

    db.insert_data(
        "subscriptions",
        {
            "user_id": user_id,
            "plan_id": PRO_PLAN_ID,
            "status": "active",
            "started_at": paid_at.replace(tzinfo=None),
            "expires_at": expires_at.replace(tzinfo=None),
            "auto_renewal": auto_renewal
        }
    )

    return expires_at


# ============================================================
# ПРОДЛЕНИЕ
# ============================================================

def extend_subscription(db, user_id: int, paid_at, auto_renewal: bool = False):
    paid_at = normalize_datetime(paid_at)

    subscriptions = db.select_data(
        "subscriptions",
        where_conditions={
            "user_id": user_id,
            "status": "active"
        }
    )

    active_sub = None
    for sub in subscriptions:
        if active_sub is None or sub[0] > active_sub[0]:
            active_sub = sub

    if active_sub:
        # Есть активная подписка – просто продлеваем, не трогаем auto_renewal
        expires_at = normalize_datetime(active_sub[5])

        if expires_at and expires_at > paid_at:
            new_expires_at = expires_at + timedelta(days=SUBSCRIPTION_DAYS)
        else:
            new_expires_at = paid_at + timedelta(days=SUBSCRIPTION_DAYS)

        db.update_data(
            "subscriptions",
            {
                "plan_id": PRO_PLAN_ID,
                "status": "active",
                "expires_at": new_expires_at.replace(tzinfo=None)
                # auto_renewal не обновляем!
            },
            where_conditions={"id": active_sub[0]}
        )

        return new_expires_at

    # Если активной подписки нет (истекла) – создаём новую
    return activate_subscription(db, user_id, paid_at, auto_renewal)


# ============================================================
# WEBHOOK
# ============================================================

def handle_webhook(db, data: dict):
    """
    Обрабатывает payment.succeeded.
    """

    if data.get("event") != "payment.succeeded":
        return None

    payment = data.get("object", {})

    payment_id = payment.get("id")

    if not payment_id:
        return None

    # --------------------------------------------------------
    # Защита от повторного webhook
    # --------------------------------------------------------

    existing = db.select_data(
        "payments",
        where_conditions={
            "provider_payment_id": payment_id
        }
    )

    if existing:
        logger.info(
            f"Payment {payment_id} already processed"
        )
        return None

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    metadata = payment.get("metadata", {})

    user_id_raw = metadata.get("user_id")

    if not user_id_raw:
        logger.error(
            f"Payment {payment_id}: user_id missing"
        )
        return None

    user_id = int(user_id_raw)

    payment_type = metadata.get(
        "payment_type"
    )

    # --------------------------------------------------------
    # Реальное время успешного платежа
    # --------------------------------------------------------

    paid_at = parse_yookassa_datetime(
        payment.get("captured_at")
        or payment.get("created_at")
    )

    # --------------------------------------------------------
    # Сохраняем платёж
    # --------------------------------------------------------

    db.insert_data(
        "payments",
        {
            "user_id": user_id,
            "provider": "yookassa",
            "provider_payment_id": payment_id,
            "amount": payment["amount"]["value"],
            "status": "succeeded",
            "created_at": paid_at.replace(
                tzinfo=None
            ),
            "paid_at": paid_at.replace(
                tzinfo=None
            )
        }
    )

    # --------------------------------------------------------
    # Первая разовая покупка
    # --------------------------------------------------------

    if payment_type == "first_one_time":
        expires_at = activate_subscription(db, user_id, paid_at, auto_renewal=False)

    elif payment_type == "first_auto":
        expires_at = activate_subscription(db, user_id, paid_at, auto_renewal=True)
        payment_method = payment.get(
            "payment_method"
        )

        if (
            payment_method
            and payment_method.get("saved") is True
        ):
            payment_method_id = payment_method.get("id")

            if payment_method_id:
                db.update_data(
                    "users",
                    {
                        "yookassa_payment_method_id":
                            payment_method_id
                    },
                    where_conditions={
                        "id": user_id
                    }
                )
    
    # --------------------------------------------------------
    # Ручное продление
    # --------------------------------------------------------

    elif payment_type == "renewal_one_time":
        expires_at = extend_subscription(db, user_id, paid_at, auto_renewal=False)

    elif payment_type == "renewal_auto":
        expires_at = extend_subscription(db, user_id, paid_at, auto_renewal=True)

    else:
        logger.error(f"Unknown payment_type: {payment_type}")
        return None
    user_analytics = db.select_data(
        "users",
        columns=["yclid", "metrika_client_id"],
        where_conditions={"id": user_id}
    )
    if user_analytics:
        yclid = user_analytics[0][0]
        client_id = user_analytics[0][1]
        if client_id:
            import asyncio
            from services.metrika import send_metrika_event
            asyncio.create_task(
                send_metrika_event(
                    client_id=client_id,
                    target="subscription_purchased",
                    yclid=yclid,
                    extra_params={"Price": payment["amount"]["value"], "Currency": "RUB"}
                )
            )
    payment_rec = db.select_data(
        "payments",
        columns=["id"],
        where_conditions={"provider_payment_id": payment_id}
    )
    if not payment_rec:
        logger.error(f"Не удалось найти платёж {payment_id} для уведомления")
        return None

    payment_db_id = payment_rec[0][0]

    db.insert_data(
        "payment_notifications",
        {
            "payment_id": payment_db_id,
            "user_id": user_id,
            "status": "pending"
        }
    )
    logger.info(f"Создано уведомление о чеке для payment_id={payment_db_id}, user_id={user_id}")
    
    return {
        "payment_id": payment_id,
        "user_id": user_id,
        "payment_type": payment_type,
        "expires_at": expires_at
    }