import sys
import os

sys.path.append('/root/Calendator')
sys.path.append('/root/Calendator/services')

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
REDIRECT_URI = os.getenv("REDIRECT_URI")
BOT_USERNAME = os.getenv("TG_BOT_USERNAME")
TG_BOT_API = os.getenv("TG_BOT_API")
app = Flask(__name__)

connection = connect_database()
db = Database(connection)

def send_telegram_message(max_id, text):
    logger.info(f"Attempting to send message to max_id={max_id}, text preview: {text[:50]}...")
    if not TG_BOT_API:
        logger.error("TG_BOT_API is not set. Cannot send message.")
        return
    url = f"https://api.telegram.org/bot{TG_BOT_API}/sendMessage"
    try:
        response = requests.post(url, json={"chat_id": max_id, "text": text})
        logger.info(f"Telegram response status: {response.status_code}, body: {response.text[:200]}")
        if response.status_code != 200:
            logger.error(f"Failed to send message to {max_id}. Response: {response.text}")
    except Exception as e:
        logger.error(f"Error occurred while sending message to {max_id}: {e}")

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

        send_telegram_message(max_id, text)

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