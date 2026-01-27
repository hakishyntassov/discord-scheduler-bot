import os
import asyncpg
from config import DATABASE_URL

pool: asyncpg.Pool | None = None

async def init_database():
    global pool
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=5,
        ssl="require"
    )

async def close_database():
    if pool:
        await pool.close()