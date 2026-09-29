import psycopg2

from dotenv import load_dotenv
from os import getenv

from logger_config import logger
from services.database.database import Database

load_dotenv()

host = getenv("host")
user = getenv("user")
password = getenv("password")
database = getenv("database")
port = getenv("port")

users_db = {
    "users": """
        id SERIAL PRIMARY KEY,
        user_id BIGINT UNIQUE NOT NULL,
        max_nickname TEXT,
        name TEXT,
        timezone_offset TEXT,
        notification_time INTEGER,
        language VARCHAR(10) DEFAULT 'ru',
        yookassa_payment_method_id VARCHAR(100),
        auto_renewal BOOLEAN,
        admin_notified BOOLEAN DEFAULT FALSE,
        blocked_bot BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW()
    """
}
user_authorization = {
    "users_authorizations": """
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        apple_calendar_email TEXT,
        apple_calendar_password TEXT,
        apple_calendar_url TEXT,
        google_calendar_email TEXT,
        google_calendar_password TEXT,
        google_calendar_url TEXT,
        google_calendar_refresh_token TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    """
}
users_costs = {
    "users_costs": """
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        text_cost NUMERIC(10,6) DEFAULT 0,
        all_cost NUMERIC(10,6) DEFAULT 0,
        created_at TIMESTAMP DEFAULT NOW()
    """
}

events_db = {
    "events": """
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        text TEXT NOT NULL,
        start_at TIMESTAMP NOT NULL,
        duration_min INTEGER DEFAULT 30,
        created_at TIMESTAMP DEFAULT NOW(),
        apple_event_url TEXT,
        apple_event_uid TEXT,
        google_event_url TEXT,
        google_event_id TEXT,
        active BOOLEAN DEFAULT TRUE
    """
}

events_notifications_db = {
    "events_notifications": """  
        id SERIAL PRIMARY KEY,   
        event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
        notify_at TIMESTAMP NOT NULL, 
        type TEXT NOT NULL DEFAULT 'before',
        status TEXT NOT NULL DEFAULT 'pending'
    """
}

oauth_devices = {
    "oauth_devices": """
        id SERIAL PRIMARY KEY,
        device_code TEXT UNIQUE NOT NULL,
        user_code TEXT NOT NULL,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        provider TEXT NOT NULL DEFAULT 'google',
        interval_seconds INTEGER DEFAULT 5,
        created_at TIMESTAMP DEFAULT NOW()
    """
}
plans_db = {
    "plans": """
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        events_limit INTEGER,
        google_calendar BOOLEAN DEFAULT FALSE,
        apple_calendar BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW()
    """
}

subscriptions_db = {
    "subscriptions": """
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        plan_id INTEGER REFERENCES plans(id),
        status TEXT NOT NULL,
        started_at TIMESTAMP,
        expires_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW(),
        auto_renewal BOOLEAN NOT NULL DEFAULT FALSE,
        expiry_notified_at TIMESTAMP,
        auto_renewal_attempted_at TIMESTAMP
    """
}

usage_db = {
    "usage": """
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        events_created INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT NOW()
    """
}

payments_db = {
    "payments": """
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        provider TEXT NOT NULL,
        provider_payment_id TEXT UNIQUE,
        amount NUMERIC(10,2) NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        paid_at TIMESTAMP
    """
}

payment_notifications_db = {
    "payment_notifications": """
        id SERIAL PRIMARY KEY,
        payment_id INTEGER REFERENCES payments(id) ON DELETE CASCADE,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        admin_message_id BIGINT,
        cheque_file_path TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    """
}
def connect_database():
    connection = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port
    )
    return connection


def insert_initial_plans(db):
    existing = db.select_data("plans", where_conditions={"name" : "free"})
    if not existing:
        db.insert_data("plans",{
            "name": "free",
            "events_limit": 7,
            "google_calendar": False,
            "apple_calendar": False
        })
        db.insert_data("plans",{
                    "name": "pro",
                    "events_limit": None,
                    "google_calendar": True,
                    "apple_calendar": True
                })
        logger.info("Initial plans inserted")
    else:
        logger.info("Plans already exist")


                       

def create_tables():
    try:
        connection = connect_database()
        db = Database(connection)
        db.create_table(users_db)
        db.create_table(events_db)
        db.create_table(events_notifications_db)
        db.create_table(users_costs)
        db.create_table(user_authorization)
        db.create_table(oauth_devices)
        db.create_table(plans_db)         
        db.create_table(subscriptions_db)   
        db.create_table(usage_db)           
        db.create_table(payments_db)
        db.create_table(payment_notifications_db)
        insert_initial_plans(db=db)
    except Exception as e:
        logger.error(f"Error {e}")
