import os
from dotenv import load_dotenv
from yookassa import Configuration

load_dotenv()

# Настройка клиента ЮKassa
Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")