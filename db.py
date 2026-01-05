import sqlite3
from contextlib import contextmanager

DB_PATH = "events.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # events table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            channel_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # event participants
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS event_joins (
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (event_id, user_id)
        )
        """
    )

    conn.commit()
    conn.close()

@contextmanager
def get_cursor():
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    finally:
        conn.close()

def add_event(title, channel_id, message_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO events (title, channel_id, message_id)
            VALUES (?, ?, ?)
            """,
            (title, channel_id, message_id)
        )
        return cursor.lastrowid

def add_join(event_id, user_id):
    with get_cursor() as cursor:
        try:
            cursor.execute(
                """
                INSERT INTO event_joins (event_id, user_id)
                VALUES (?, ?)
                """,
                (event_id, user_id)
            )
            return True
        except sqlite3.IntegrityError:
            return False

def count_joins(event_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM event_joins 
            WHERE event_id = ?
            """,
            (event_id,)
        )
        return cursor.fetchone()[0]

def user_in_event(event_id: int, user_id: int) -> bool:
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM event_joins
            WHERE event_id = ? AND user_id = ?
            LIMIT 1
            """,
            (event_id, user_id)
        )
        return cursor.fetchone() is not None