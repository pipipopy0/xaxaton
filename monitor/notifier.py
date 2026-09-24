import requests

from monitor.config import BOT_TOKEN, ADMIN_ID


def send_alert(text):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    requests.post(
        url,
        json={
            "chat_id": ADMIN_ID,
            "text": text
        },
        timeout=10
    )