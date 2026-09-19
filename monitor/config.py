from os import getenv
from dotenv import load_dotenv

load_dotenv()


BOT_TOKEN = getenv("MAX_BOT_API")
ADMIN_ID = getenv("tg_admin_id")
OPENROUTER_API = getenv("OPENROUTER_API")
POLZA_API = getenv("POLZA_API")
EXCHANGE_RATE = getenv("EXCHANGE_RATE")

DB = {
    "dbname": getenv("database"),
    "user": getenv("user"),
    "password": getenv("password"),
    "host": getenv("host"),
}