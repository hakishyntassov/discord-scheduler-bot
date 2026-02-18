import math
import re
import logging
from collections import defaultdict
from datetime import datetime
import asyncpg
from contextlib import asynccontextmanager
from config import DATABASE_PUBLIC_URL
from time_parse import to_minutes, minutes_to_label

logger = logging.getLogger(__name__)

pool: asyncpg.Pool | None = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_PUBLIC_URL, min_size=1, max_size=20)

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
            start_date      DATE NOT NULL,
            start_time      INTEGER NOT NULL,
            end_time        INTEGER NOT NULL,
            is_preferred    BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (event_id)
                REFERENCES events(id)
                ON DELETE CASCADE
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

        await conn.execute("""
        ALTER TABLE availability
        ALTER COLUMN start_date TYPE TIMESTAMPTZ;
        """)

        await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_availability_event_id
        ON availability(event_id);
        """)

    logger.info("Postgres schema initialized")

@asynccontextmanager
async def get_connection():
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn

async def close_database():
    if pool:
        await pool.close()

async def add_event(title, channel_id, guild_id, message_id, count_members, start_timep, end_timep) -> int:
    async with get_connection() as conn:
        return await conn.fetchval(
            """
            INSERT INTO events (
                title,
                channel_id,
                guild_id,
                message_id,
                count_members,
                start_timep,
                end_timep
            )
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

async def add_join(event_id, user_id):
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO event_joins (
                event_id, 
                user_id
            )
            VALUES ($1, $2)
            """,
            event_id,
            user_id
        )

async def add_rsvp(event_id, user_id, status):
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO rsvp (event_id, user_id, status)
            VALUES ($1, $2, $3)
            """,
            event_id,
            user_id,
            status
            )

async def get_times(event_id: int):
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT start_timep, end_timep
            FROM events
            WHERE id = $1
            """,
            event_id
        )

        if row is None:
            return None

        return row["start_timep"], row["end_timep"]

async def get_channel_message(event_id: int):
    async with get_connection() as conn:
        ch_msg = await conn.fetch(
            """
            SELECT channel_id, message_id
            FROM events
            WHERE id = $1
            """,
            event_id
        )
        return ch_msg

async def count_joins(event_id) -> int:
    async with get_connection() as conn:
        return await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM event_joins
            WHERE event_id = $1
            """,
            event_id
        )

async def get_joins(event_id) -> list[int]:
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT user_id
            FROM event_joins
            WHERE event_id = $1
            LIMIT 500
            """,
            event_id
        )
        return [row["user_id"] for row in rows]

async def get_message_id(event_id: int) -> int | None:
    async with get_connection() as conn:
        return await conn.fetchval(
            """
            SELECT message_id
            FROM events
            WHERE id = $1
            """,
            event_id
        )

async def get_channel_id(event_id: int) -> int | None:
    async with get_connection() as conn:
        return await conn.fetchval(
            """
            SELECT channel_id
            FROM events
            WHERE id = $1
            """,
            event_id
        )

async def get_not_submitted(event_id: int) -> list[int]:
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT user_id
            FROM event_joins
            WHERE event_id = $1
              AND submitted = FALSE
            LIMIT 500
            """,
            event_id
        )
        return [row["user_id"] for row in rows]

async def count_members(event_id: int) -> int | None:
    async with get_connection() as conn:
        return await conn.fetchval(
            """
            SELECT count_members
            FROM events
            WHERE id=$1
            """,
            event_id
        )

async def get_title(event_id: int) -> str | None:
    async with get_connection() as conn:
        return await conn.fetchval(
            """
            SELECT title
            FROM events
            WHERE id = $1
            """,
            event_id
        )

async def get_start_timep(event_id: int) -> datetime:
    async with get_connection() as conn:
        return await conn.fetchval(
            """
            SELECT start_timep
            FROM events
            WHERE id = $1
            """,
            event_id
        )

async def get_end_timep(event_id: int) -> datetime | None:
    async with get_connection() as conn:
        return await conn.fetchval(
            """
            SELECT end_timep
            FROM events
            WHERE id = $1
            """,
            event_id
        )

async def user_in_event(event_id: int, user_id: int) -> bool:
    async with get_connection() as conn:
        return await conn.fetchval(
            """
            SELECT EXISTS (SELECT 1
                           FROM event_joins
                           WHERE event_id = $1
                             AND user_id = $2)
            """,
            event_id,
            user_id
        )

async def user_in_rsvp(event_id: int, user_id: int) -> bool:
    async with get_connection() as conn:
        return await conn.fetchval(
            """
            SELECT EXISTS (SELECT 1
                           FROM rsvp
                           WHERE event_id = $1 
                             AND user_id = $2
            )
            """,
            event_id,
            user_id
        )

async def change_rsvp(event_id: int, user_id: int, status: int):
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE rsvp
            SET status = $1
            WHERE event_id = $2
              AND user_id = $3
            """,
            status,
            event_id,
            user_id
        )

async def get_rsvp(event_id: int, user_id: int) -> int:
    async with get_connection() as conn:
        return await conn.fetchval(
            """
            SELECT status
            FROM rsvp
            WHERE event_id = $1 
            AND user_id = $2
            """,
            event_id,
            user_id
        )

async def set_rsvp(event_id: int, user_id: int, status: int) -> bool:
    async with get_connection() as conn:
        change = await conn.fetchrow(
            """
            INSERT INTO rsvp (event_id, user_id, status)
            VALUES ($1, $2, $3)
            ON CONFLICT (event_id, user_id)
            DO UPDATE
                SET status = EXCLUDED.status
                WHERE rsvp.status IS DISTINCT FROM EXCLUDED.status
            RETURNING 1
            """,
            event_id,
            user_id,
            status
        )
        return change is not None

async def get_rsvp_users(event_id: int):
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT user_id, status
            FROM rsvp
            WHERE event_id = $1
            LIMIT 500
            """,
            event_id
        )
        return rows

async def count_status(event_id: int, status: int) -> int:
    async with get_connection() as conn:
        return await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM rsvp
            WHERE event_id = $1 
            AND status = $2
            """,
            event_id,
            status
        )

async def save_availability(event_id: int, user_id: int, weekday: int, start_date: datetime, raw_input: str, is_preferred: bool):
    TIME_RANGE_REGEX = re.compile(
        r"""
        (?P<start_hour>1[0-2]|0?[1-9]|2[0-3])
        (?::(?P<start_min>[0-5][0-9]))?
        \s*(?P<start_ampm>am|pm)?
        (?:
            \s*-\s*
            (?:
                (?P<end_hour>1[0-2]|0?[1-9]|2[0-3])
                (?::(?P<end_min>[0-5][0-9]))?
                \s*(?P<end_ampm>am|pm)?
            )?
        )?
        """,
        re.IGNORECASE | re.VERBOSE
    )

    MAX_RANGES_PER_DAY = 10
    matches = list(TIME_RANGE_REGEX.finditer(raw_input))[:MAX_RANGES_PER_DAY]
    for match in matches:
        start_time = to_minutes(
            match.group("start_hour"),
            match.group("start_min"),
            match.group("start_ampm")
        )

        end_exists = any(
            match.group(k) is not None
            for k in ("end_hour", "end_min", "end_ampm")
        )

        if not end_exists:
            end_time = to_minutes(11, 59, "pm")
        else:
            end_time = to_minutes(
                match.group("end_hour"),
                match.group("end_min"),
                match.group("end_ampm")
            )

        if end_time <= start_time:
            raise ValueError("End time must be after start time")

        async with get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO availability (event_id,
                                          user_id,
                                          weekday,
                                          start_date,
                                          start_time,
                                          end_time,
                                          is_preferred)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                event_id,
                user_id,
                weekday,
                start_date,
                start_time,
                end_time,
                is_preferred
            )

async def submit_availability(event_id: int, user_id: int) -> None:
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE event_joins
            SET submitted = TRUE
            WHERE event_id = $1
              AND user_id = $2
            """,
            event_id,
            user_id
        )

async def get_count_members(event_id: int):
    async with get_connection() as conn:
        return await conn.fetchval(
            """
            SELECT count_members
            FROM events
            WHERE id = $1
            """,
            event_id
        )

async def get_count_submits(event_id: int):
    async with get_connection() as conn:
        return await conn.fetchval(
            """
            SELECT COUNT(*) 
            FROM event_joins 
            WHERE event_id = $1 AND submitted = TRUE
            """,
            event_id
        )

MAX_AVAILABILITY_ROWS = 10_000

async def find_overlaps(event_id: int, min_people: int):
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT weekday, start_date, start_time, end_time, is_preferred
            FROM availability
            WHERE event_id = $1
            LIMIT $2
            """,
            event_id,
            MAX_AVAILABILITY_ROWS
        )

    if len(rows) == MAX_AVAILABILITY_ROWS:
        logger.warning(
            "find_overlaps hit the row cap (%d) for event_id=%s — results may be incomplete",
            MAX_AVAILABILITY_ROWS, event_id
        )

    events = defaultdict(list)
    for weekday, start_date, start_time, end_time, is_preferred in rows:
        start_time = int(start_time)
        end_time = int(end_time)

        pref = 1 if is_preferred else 0
        events[weekday].append((start_time, +1, +pref, start_date))
        events[weekday].append((end_time, -1, -pref, start_date))

        logger.debug(
            "availability row — weekday=%s date=%s %s–%s preferred=%s",
            weekday, start_date,
            minutes_to_label(start_time), minutes_to_label(end_time),
            is_preferred
        )

    results = []

    for weekday, points in events.items():
        points.sort(key=lambda x: (x[0], x[1]))
        logger.debug("sweep points weekday=%s: %s", weekday, points)
        count = 0
        pref_count = 0
        for i in range(len(points) - 1):
            time, delta, pref_delta, start_date = points[i]
            count += delta  # apply change at boundary
            pref_count += pref_delta
            next_time = points[i + 1][0]

            if count >= min_people and time < next_time:
                results.append((weekday, time, next_time, count, pref_count, start_date))

    results.sort(key=lambda r: (r[3], r[4], r[0]), reverse=True)

    count_members = await get_count_members(event_id)
    threshold = 0.75 * int(count_members)
    min_threshold = math.floor(threshold)
    logger.debug("find_overlaps event_id=%s count_members=%s min_threshold=%s", event_id, count_members, min_threshold)

    for weekday, start, end, count, pref_count, start_date in results:
        if count >= min_threshold:
            logger.debug(
                "overlap — weekday=%s date=%s %s–%s people=%s preferred=%s",
                weekday, start_date,
                minutes_to_label(start), minutes_to_label(end),
                count, pref_count
            )
    return results