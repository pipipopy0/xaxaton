import requests
from monitor.config import OPENROUTER_API, POLZA_API, EXCHANGE_RATE


def get_balance(api_key: str, provider: str, exchange_rate = None):
    providers = {
        "polza": "https://polza.ai/api/v1/balance",
        "openrouter": "https://openrouter.ai/api/v1/credits"
    }

    if provider not in providers:
        raise ValueError(f"Unknown provider: {provider}")

    response = requests.get(
        providers[provider],
        headers={
            "Authorization": f"Bearer {api_key}"
        },
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    if provider == "polza":
        return {
            "used": float(data["spentAmount"]),
            "remaining": float(data["amount"])
        }

    if provider == "openrouter":
        data = data["data"]

        return {
            "used": exchange_rate*float(data["total_usage"]),
            "remaining": exchange_rate*(float(data["total_credits"]) - float(data["total_usage"]))
        }
    

def get_balance_statuses():
    """Возвращает список статусов для балансов Polza и OpenRouter."""
    result = []

    # Polza
    if POLZA_API:
        try:
            balance = get_balance(POLZA_API, "polza")
            remaining = balance.get("remaining", 0)
            result.append({
                "name": "Polza Balance",
                "value": f"{remaining:.2f} ₽",
                "ok": True,
                "details": None
            })
        except Exception as e:
            result.append({
                "name": "Polza Balance",
                "value": "Ошибка",
                "ok": False,
                "details": str(e)
            })
    else:
        result.append({
            "name": "Polza Balance",
            "value": "Ключ не задан",
            "ok": False,
            "details": "POLZA_API отсутствует в .env"
        })

    # OpenRouter
    if OPENROUTER_API and EXCHANGE_RATE:
        try:
            balance = get_balance(OPENROUTER_API, "openrouter", exchange_rate=float(EXCHANGE_RATE))
            remaining = balance.get("remaining", 0)
            result.append({
                "name": "OpenRouter Balance",
                "value": f"{remaining:.2f} ₽",
                "ok": True,
                "details": None
            })
        except Exception as e:
            result.append({
                "name": "OpenRouter Balance",
                "value": "Ошибка",
                "ok": False,
                "details": str(e)
            })
    else:
        result.append({
            "name": "OpenRouter Balance",
            "value": "Ключ или курс не заданы",
            "ok": False,
            "details": "OPENROUTER_API или EXCHANGE_RATE отсутствует в .env"
        })

    return result