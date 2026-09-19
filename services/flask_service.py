# это прям отдельный сервис по типу duckling. отдельно нужно запускать

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

def send_telegram_message(user_id, text):
    logger.info(f"Attempting to send message to user_id={user_id}, text preview: {text[:50]}...")
    if not TG_BOT_API:
        logger.error("TG_BOT_API is not set. Cannot send message.")
        return
    url = f"https://api.telegram.org/bot{TG_BOT_API}/sendMessage"
    try:
        response = requests.post(url, json={"chat_id": user_id, "text": text})
        logger.info(f"Telegram response status: {response.status_code}, body: {response.text[:200]}")
        if response.status_code != 200:
            logger.error(f"Failed to send message to {user_id}. Response: {response.text}")
    except Exception as e:
        logger.error(f"Error occurred while sending message to {user_id}: {e}")

def render_html(title, message, success=True):
    status_icon = "✅" if success else "❌"
    status_title = "Успешно" if success else "Ошибка"
    color = "#4CAF50" if success else "#f44336"
    logger.info(f"Rendering HTML page: title='{title}', success={success}")
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{title}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: #f0f2f5;
            }}
            .container {{
                background: white;
                padding: 40px 50px;
                border-radius: 16px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.1);
                text-align: center;
                max-width: 500px;
            }}
            .icon {{
                font-size: 64px;
                display: block;
                margin-bottom: 20px;
            }}
            h1 {{
                color: {color};
                font-size: 28px;
                margin-bottom: 12px;
            }}
            p {{
                color: #555;
                font-size: 16px;
                line-height: 1.6;
                margin: 8px 0;
            }}
            .btn {{
                display: inline-block;
                margin-top: 20px;
                padding: 12px 30px;
                background: #0088cc;
                color: white;
                text-decoration: none;
                border-radius: 30px;
                font-weight: bold;
                transition: background 0.2s;
            }}
            .btn:hover {{
                background: #006699;
            }}
            .hint {{
                margin-top: 16px;
                font-size: 14px;
                color: #888;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <span class="icon">{status_icon}</span>
            <h1>{title}</h1>
            <p>{message}</p>
            <a href="tg://resolve?domain={BOT_USERNAME}" class="btn">📱 Open Bot</a>
            <p class="hint">If the link doesn't work, find @{BOT_USERNAME} in Telegram</p>
        </div>
    </body>
    </html>
    """

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
            columns=["user_id", "timezone_offset"],
            where_conditions={"id": user_id}
        )

        if not user:
            logger.error(f"User {user_id} not found")
            return "OK", 200

        user_id = user[0][0]
        user_timezone = user[0][1] or "UTC"
        expires_at_user = expires_at.astimezone(
                ZoneInfo(user_timezone)
            )
        # Разовая оплата
        if payment_type == "first_one_time":
            text = get_text(
                key="pro_activated",
                user_id=user_id,
                db=db
            )
        # Первая оплата с автопродлением
        elif payment_type == "first_auto":
            text = get_text(
                key="pro_auto_activated",
                user_id=user_id,
                db=db,
                expires_at=expires_at_user.strftime("%d.%m.%Y %H:%M")
            )

        # Ручное продление
        elif payment_type == "renewal_one_time":
            text = get_text(
                key="pro_renewed",
                user_id=user_id,
                db=db,
                expires_at=expires_at_user.strftime("%d.%m.%Y %H:%M")
            )

        # Автоматическое продление
        elif payment_type == "renewal_auto":
            text = get_text(
                key="pro_auto_renewed",
                user_id=user_id,
                db=db,
                expires_at=expires_at_user.strftime("%d.%m.%Y %H:%M")
            )

        else:
            return "OK", 200

        send_telegram_message(user_id, text)

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

@app.route("/callback")
def google_calendar():
    code = request.args.get("code")
    state = request.args.get("state")

    logger.info("=== CALLBACK INVOKED ===")

    if not code or not state:
        return render_html(
            "Error",
            "Insufficient authorization parameters",
            success=False
        )

    oauth_state = db.select_data(
        "oauth_states",
        columns=["user_id"],
        where_conditions={"state": state}  # изменено
    )

    if not oauth_state:
        return render_html(
            "Error",
            "Authorization session expired",
            success=False
        )

    user_id = oauth_state[0][0]
    logger.info(f"GET params: code={code[:10] if code else None}..., state={state}")
    logger.info(f"Full request URL: {request.url}")
    logger.info(f"Remote IP: {request.remote_addr}, User-Agent: {request.headers.get('User-Agent')}")
    
    data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret" : CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type" : "authorization_code",
    }
    try:
        logger.info("Sending token exchange request to google OAuth")
        r = requests.post(
            "https://oauth2.googleapis.com/token",
            data=data
        )
        
        tokens = r.json()
        logger.info(f"Token response status: {r.status_code}")
        logger.info(f"Token response keys: {tokens.keys() if isinstance(tokens, dict) else 'not a dict'}")
        
        if r.status_code != 200:
            logger.error(f"Google token exchange failed: {tokens}")
            return f"Error: {tokens}"

        refresh_token = tokens.get("refresh_token")
        logger.info(f"Received refresh_token: {bool(refresh_token)} (first 10 chars: {refresh_token[:10] if refresh_token else None})")
        
        logger.info(f"Fetching user with id={user_id} from DB")
        user = db.select_data(
            "users",
            where_conditions={"id": user_id}  # изменено
            )
        if not user:
            logger.error(f"User with id {user_id} not found in DB")
            return render_html("Eroor", "User not found. Try to register again", success=False)
        if user and user[0][1]:
            user_id = user[0][1]
            logger.info(f"Found user: user_id={user_id}, language={user[0][6] if user and len(user[0])>6 else 'unknown'}")
            text = get_text(key="google_authorized", user_id=user_id, db=db)
            logger.info(f"text = {text}, language = {user[0][6]}")
        if refresh_token:
            existing = db.select_data(
                "users_authorizations",
                columns=["id"],
                where_conditions={"user_id": user_id}  # изменено
            )
            try:
                if existing:
                    logger.info(f"Updating refresh_token for user {user_id}")
                    db.update_data(
                        "users_authorizations",
                        {"google_calendar_refresh_token": refresh_token},
                        where_conditions={"user_id": user_id}  # изменено
                    )
                    
                else:
                    logger.info(f"Inserting new authorization record for user {user_id}")
                    db.insert_data(
                        "users_authorizations",
                        {
                            "user_id": user_id,
                            "google_calendar_refresh_token": refresh_token
                        }
                    )
                db.delete_data(
                    "oauth_states",
                    where_conditions={"state": state}  # изменено
                )
                send_telegram_message(user_id, text)
                google_text = get_text(key="google_authorized", user_id=user_id, db=db)
                close_page_text = get_text(key="close_authorization_page", user_id=user_id, db=db)
                return render_html(google_text, close_page_text, success=True)    
            
            except Exception as e:
                error_text = get_text(key="error", user_id=user_id, db=db)
                refresh_error_text = get_text(key="refresh_token_not_received", user_id=user_id, db=db)
                return render_html(error_text, refresh_error_text, success=False)
    except Exception as e:
        logger.error(f"Ошибка при обработке callback: {e}")
        error_processing_callback_text = get_text(key="error_processing_callback", user_id=user_id, db=db)
        return render_html(error_text, error_processing_callback_text, success=False)

    

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8005, debug=False)