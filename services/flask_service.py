import asyncio
import sys
import os

sys.path.append('/root/Calendator')
sys.path.append('/root/Calendator/services')

from maxapi import Bot
import requests
from flask import Flask, request, redirect
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
from database.work_with_dp import connect_database
from database.database import Database
from logger_config import logger
from handlers.answer_texts.TEXT import get_text
from datetime import datetime, timedelta
from services.payment_service import handle_webhook

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_GOOGLE_ID")
CLIENT_SECRET = os.getenv("CLIENT_GOOGLE_SECRET")
BOT_USERNAME = os.getenv("TG_BOT_USERNAME")
MAX_BOT_TOKEN = os.getenv("MAX_BOT_API")
app = Flask(__name__)

if not MAX_BOT_TOKEN:
    logger.error("MAX_BOT_TOKEN is not set!")

bot = Bot(token=MAX_BOT_TOKEN)

connection = connect_database()
db = Database(connection)

async def send_max_message(max_id, text):
    logger.info(
        f"Attempting to send MAX message to max_id={max_id}, "
        f"text preview: {text[:50]}..."
    )

    if not MAX_BOT_TOKEN:
        logger.error("MAX_BOT_API is not set. Cannot send message.")
        return

    try:
        await bot.send_message(
            chat_id=max_id,
            text=text
        )

        logger.info(
            f"MAX message successfully sent to {max_id}"
        )

    except Exception as e:
        logger.exception(
            f"Error sending MAX message to {max_id}: {e}"
        )

def send_max_message_sync(max_id, text):

    asyncio.run(
        send_max_message(max_id, text)
    )

@app.route("/yookassa/webhook", methods=["POST"])
def yookassa_webhook():
    try:
        data = request.get_json()

        if not data:
            logger.error("Webhook received without JSON")
            return "OK", 200

        if data.get("event") != "payment.succeeded":
            return "OK", 200

        logger.info(
            f"Webhook received: {data.get('event')}"
        )

        result = handle_webhook(db, data)

        if not result:
            return "OK", 200

        user_id = result["user_id"]
        payment_type = result["payment_type"]
        expires_at = result["expires_at"]

        user = db.select_data(
            "users",
            columns=["max_id", "timezone_offset"],
            where_conditions={"id": user_id}
        )

        if not user:
            logger.error(f"User {user_id} not found")
            return "OK", 200

        max_id = user[0][0]
        user_timezone = user[0][1] or "UTC"
        expires_at_user = expires_at.astimezone(
                ZoneInfo(user_timezone)
            )
        if payment_type == "first_one_time":
            text = get_text(
                key="pro_activated",
                max_id=max_id,
                db=db
            )
        elif payment_type == "first_auto":
            text = get_text(
                key="pro_auto_activated",
                max_id=max_id,
                db=db,
                expires_at=expires_at_user.strftime("%d.%m.%Y %H:%M")
            )

        elif payment_type == "renewal_one_time":
            text = get_text(
                key="pro_renewed",
                max_id=max_id,
                db=db,
                expires_at=expires_at_user.strftime("%d.%m.%Y %H:%M")
            )

        elif payment_type == "renewal_auto":
            text = get_text(
                key="pro_auto_renewed",
                max_id=max_id,
                db=db,
                expires_at=expires_at_user.strftime("%d.%m.%Y %H:%M")
            )

        else:
            return "OK", 200

        send_max_message(max_id, text)

        logger.info(
            f"Payment processed: "
            f"user_id={user_id}, "
            f"type={payment_type}, "
            f"expires_at={expires_at}"
        )

        return "OK", 200

    except Exception as e:
        logger.exception(
            f"Error processing YooKassa webhook: {e}"
        )
        return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8005, debug=False)