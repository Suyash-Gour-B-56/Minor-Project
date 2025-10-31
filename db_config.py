# db_config.py
import mysql.connector
from mysql.connector import errorcode
import time

DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "rootpassword"    # <-- your provided password
DB_NAME = "scheduling_db"

def get_connection(retries=3, delay=1):
    """Return a mysql.connector connection; create DB if missing (best-effort)."""
    attempt = 0
    while attempt < retries:
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME,
                connection_timeout=30
            )
            return conn
        except mysql.connector.Error as err:
            # If DB does not exist, try to create it (one time)
            if err.errno == errorcode.ER_BAD_DB_ERROR:
                try:
                    tmp = mysql.connector.connect(
                        host=DB_HOST,
                        user=DB_USER,
                        password=DB_PASS,
                        connection_timeout=30
                    )
                    cur = tmp.cursor()
                    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
                    cur.close()
                    tmp.close()
                    time.sleep(0.5)
                    attempt += 1
                    continue
                except Exception:
                    raise
            attempt += 1
            time.sleep(delay)
            if attempt >= retries:
                raise
    raise RuntimeError("Could not connect to the database after retries.")
