import os
import asyncpg
import ssl
from config import DATABASE_URL

pool: asyncpg.Pool | None = None

async def init_database():
    global pool
    ssl_context = ssl.create_default_context()
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=5,
        ssl=ssl_context
    )

    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id             BIGSERIAL PRIMARY KEY,
                title          TEXT NOT NULL,
                channel_id     BIGINT NOT NULL,
                guild_id       BIGINT NOT NULL,
                message_id     BIGINT NOT NULL,
                count_members  INTEGER NOT NULL,
                start_timep    TIMESTAMP NOT NULL,
                end_timep      TIMESTAMP,
                created_at     TIMESTAMP DEFAULT NOW()
            )   
            """
        )

    print("Created table")

async def close_database():
    if pool:
        await pool.close()