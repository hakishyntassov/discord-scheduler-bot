import asyncpg
from contextlib import asynccontextmanager
from config import DATABASE_PUBLIC_URL

pool: asyncpg.Pool | None = None

async def init_database():
    global pool
    pool = await asyncpg.create_pool(DATABASE_PUBLIC_URL, min_size=1, max_size=5)

    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id             BIGSERIAL PRIMARY KEY,
            title          TEXT NOT NULL,
            channel_id     BIGINT NOT NULL,
            guild_id       BIGINT NOT NULL,
            message_id     BIGINT NOT NULL,
            count_members  INTEGER NOT NULL,
            start_timep    TIMESTAMPTZ NOT NULL,
            end_timep      TIMESTAMPTZ,
            created_at     TIMESTAMPTZ DEFAULT NOW()
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS event_joins (
            event_id    BIGINT NOT NULL,
            user_id     BIGINT NOT NULL,
            submitted   BOOLEAN DEFAULT FALSE,
            joined_at   TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (event_id, user_id),
            FOREIGN KEY (event_id)
                REFERENCES events(id)
                ON DELETE CASCADE
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS availability (
            availability_id BIGSERIAL PRIMARY KEY,
            event_id        BIGINT NOT NULL,
            user_id         BIGINT NOT NULL,
            weekday         INTEGER NOT NULL,
            date1           DATE NOT NULL,
            start_time      TIME NOT NULL,
            end_time        TIME NOT NULL,
            is_preferred    BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (event_id)
                REFERENCES events(id)
                ON DELETE CASCADE,
            UNIQUE (event_id, user_id, weekday, start_time, end_time)
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS rsvp (
            rsvp_id BIGSERIAL PRIMARY KEY,
            event_id BIGINT NOT NULL,
            user_id  BIGINT NOT NULL,
            status   INTEGER NOT NULL,
            FOREIGN KEY (event_id)
                REFERENCES events(id)
                ON DELETE CASCADE,
            UNIQUE (event_id, user_id)
        );
        """)

    print("Postgres schema initialized")

@asynccontextmanager
async def get_connection():
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn

async def close_database():
    if pool:
        await pool.close()

async def add_event1(title, channel_id, guild_id, message_id, count_members, start_timep, end_timep):
    async with get_connection() as conn:
        event_id = await conn.fetchval(
            """
            INSERT INTO events (title, 
                                channel_id, 
                                guild_id, 
                                message_id, 
                                count_members, 
                                start_timep, 
                                end_timep)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            title,
            channel_id,
            guild_id,
            message_id,
            count_members,
            start_timep,
            end_timep
        )
        return event_id