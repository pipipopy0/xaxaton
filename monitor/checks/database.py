import psycopg2
from monitor.config import DB


def check_database():

    try:

        conn = psycopg2.connect(**DB)

        cur = conn.cursor()

        cur.execute("SELECT 1")

        conn.close()


        return {
            "name": "PostgreSQL",
            "ok": True,
            "value": "OK"
        }


    except Exception as e:

        return {
            "name": "PostgreSQL",
            "ok": False,
            "value": str(e)
        }