from datetime import datetime, timezone

from services.payment_service import create_recurrent_payment
from logger_config import logger


def run_recurrent_payments(db):
    now = datetime.now(timezone.utc)

    active_subs = db.select_data(
        "subscriptions",
        where_conditions={
            "status": "active"
        }
    )

    expiring_subs = []

    for sub in active_subs:
        expires_at = sub[5]

        if not expires_at:
            continue

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc
            )

        if expires_at <= now:
            expiring_subs.append(sub)

    logger.info(
        f"Found {len(expiring_subs)} subscriptions "
        f"ready for auto-renewal"
    )

    for sub in expiring_subs:
        user_id = sub[1]

        user_data = db.select_data(
            "users",
            columns=["yookassa_payment_method_id"],
            where_conditions={
                "id": user_id
            }
        )

        if not user_data:
            logger.warning(
                f"User {user_id} not found"
            )
            continue

        payment_method_id = user_data[0][0]

        if not payment_method_id:
            logger.info(
                f"User {user_id} has no saved payment method"
            )
            continue

        try:
            payment = create_recurrent_payment(
                user_id,
                payment_method_id
            )

            logger.info(
                f"Auto-renewal payment created: "
                f"user_id={user_id}, "
                f"payment_id={payment.id}"
            )

        except Exception as e:
            logger.exception(
                f"Failed to create auto-renewal "
                f"for user {user_id}: {e}"
            )