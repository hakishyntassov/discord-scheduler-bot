# db.py
import sqlite3
from typing import Iterable, Tuple, List, Optional

DB_PATH = "availability.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS availability_ranges (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                day TEXT NOT NULL,          -- "Mon"..."Sun"
                start_min INTEGER NOT NULL, -- minutes since midnight
                end_min INTEGER NOT NULL,   -- minutes since midnight (midnight = 1440)
                PRIMARY KEY (guild_id, user_id, day, start_min, end_min)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS preferred_days (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                day TEXT NOT NULL,          -- "Mon"..."Sun"
                preferred INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, day)
            )
        """)

def clear_day_ranges(guild_id: int, user_id: int, day: str):
    with get_connection() as conn:
        conn.execute("""
            DELETE FROM availability_ranges
            WHERE guild_id=? AND user_id=? AND day=?
        """, (guild_id, user_id, day))

def insert_day_ranges(guild_id: int, user_id: int, day: str, ranges: Iterable[Tuple[int, int]]):
    with get_connection() as conn:
        conn.executemany("""
            INSERT OR IGNORE INTO availability_ranges (guild_id, user_id, day, start_min, end_min)
            VALUES (?, ?, ?, ?, ?)
        """, [(guild_id, user_id, day, s, e) for (s, e) in ranges])

def toggle_preferred(guild_id: int, user_id: int, day: str) -> int:
    """Returns new preferred value (0 or 1)."""
    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO preferred_days (guild_id, user_id, day, preferred)
            VALUES (?, ?, ?, 0)
        """, (guild_id, user_id, day))

        cur = conn.execute("""
            SELECT preferred FROM preferred_days
            WHERE guild_id=? AND user_id=? AND day=?
        """, (guild_id, user_id, day))
        current = cur.fetchone()[0]

        new_val = 0 if current == 1 else 1
        conn.execute("""
            UPDATE preferred_days
            SET preferred=?
            WHERE guild_id=? AND user_id=? AND day=?
        """, (new_val, guild_id, user_id, day))
        return new_val