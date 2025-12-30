# scheduler/db.py
import aiosqlite
from typing import Optional, List, Tuple
from config import DB_PATH

CREATE_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id INTEGER NOT NULL,
  channel_id INTEGER NOT NULL,
  message_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  week_start TEXT NOT NULL,  -- YYYY-MM-DD
  expires_at TEXT NOT NULL   -- ISO string
);

CREATE TABLE IF NOT EXISTS participants (
  session_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  submitted INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(session_id, user_id),
  FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS availability (
  session_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  day_index INTEGER NOT NULL,
  start_minutes INTEGER NOT NULL,
  duration_minutes INTEGER NOT NULL,
  PRIMARY KEY(session_id, user_id, day_index),
  FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_SQL)
        await db.commit()

async def create_session(guild_id: int, channel_id: int, message_id: int, title: str, week_start: str, expires_at: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO sessions (guild_id, channel_id, message_id, title, week_start, expires_at) VALUES (?,?,?,?,?,?)",
            (guild_id, channel_id, message_id, title, week_start, expires_at),
        )
        await db.commit()
        return cur.lastrowid

async def get_session_by_message(message_id: int) -> Optional[Tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, guild_id, channel_id, message_id, title, week_start, expires_at FROM sessions WHERE message_id=?",
            (message_id,),
        )
        return await cur.fetchone()

async def add_participant(session_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO participants (session_id, user_id, submitted) VALUES (?,?,0)",
            (session_id, user_id),
        )
        await db.commit()

async def mark_submitted(session_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE participants SET submitted=1 WHERE session_id=? AND user_id=?",
            (session_id, user_id),
        )
        await db.commit()

async def list_participants(session_id: int) -> List[Tuple[int, int]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT user_id, submitted FROM participants WHERE session_id=?",
            (session_id,),
        )
        return await cur.fetchall()

async def upsert_availability(session_id: int, user_id: int, day_index: int, start_minutes: int, duration_minutes: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO availability (session_id, user_id, day_index, start_minutes, duration_minutes)
            VALUES (?,?,?,?,?)
            ON CONFLICT(session_id, user_id, day_index)
            DO UPDATE SET start_minutes=excluded.start_minutes, duration_minutes=excluded.duration_minutes
            """,
            (session_id, user_id, day_index, start_minutes, duration_minutes),
        )
        await db.commit()

async def list_availability(session_id: int) -> List[Tuple[int, int, int, int]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT user_id, day_index, start_minutes, duration_minutes FROM availability WHERE session_id=?",
            (session_id,),
        )
        return await cur.fetchall()
