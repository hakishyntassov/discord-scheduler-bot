import sqlite3
import re
from collections import defaultdict
from contextlib import contextmanager
from time_parse import to_minutes, minutes_to_label

DB_PATH = "events.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # events table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            channel_id  INTEGER NOT NULL,
            guild_id    INTEGER NOT NULL,
            message_id  INTEGER NOT NULL,
            created_at  TEXT DEFAULT (datetime('now'))
        )
        """
    )

    # event participants
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS event_joins (
            event_id    INTEGER NOT NULL,
            user_id     INTEGER NOT NULL,
            joined_at   TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (event_id, user_id),
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        )
        """
    )

    # availability table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS availability (
            availability_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id        INTEGER NOT NULL,
            user_id         INTEGER NOT NULL,
            weekday         INTEGER NOT NULL,
            start_time      TEXT NOT NULL,
            end_time        TEXT NOT NULL,
            is_preferred    BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
            UNIQUE (event_id, user_id, weekday, start_time, end_time)
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

def add_event(title, channel_id, guild_id, message_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO events (title, channel_id, guild_id, message_id)
            VALUES (?, ?, ?, ?)
            """,
            (title, channel_id, guild_id, message_id)
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

def save_availability(event_id: int, user_id: int, weekday: int, raw_input: str, is_preferred: bool):
    TIME_RANGE_REGEX = re.compile(
        r"""
        (?P<start_hour>1[0-2]|0?[1-9]|2[0-3])
        (?:
            :(?P<start_min>[0-5][0-9])
        )?
        \s*(?P<start_ampm>am|pm)?
        \s*-\s*
        (?P<end_hour>1[0-2]|0?[1-9]|2[0-3])
        (?:
            :(?P<end_min>[0-5][0-9])
        )?
        \s*(?P<end_ampm>am|pm)?
        """,
        re.IGNORECASE | re.VERBOSE
    )
    matches = list(TIME_RANGE_REGEX.finditer(raw_input))
    for match in matches:
        start_time = to_minutes(
            match.group("start_hour"),
            match.group("start_min"),
            match.group("start_ampm")
        )

        end_time = to_minutes(
            match.group("end_hour") or 11,
            match.group("end_min") or 59,
            match.group("end_ampm") or "pm"
        )

        if end_time <= start_time:
            raise ValueError("End time must be after start time")

        with get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO availability (event_id, user_id, weekday, start_time, end_time, is_preferred)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_id, user_id, weekday, start_time, end_time, is_preferred)
            )

def find_overlaps(event_id: int, min_people: int = 2):
    with get_cursor() as cursor:
        rows = cursor.execute(
            """
            SELECT weekday, start_time, end_time, is_preferred
            FROM availability
            WHERE event_id = ?
            """,
            (event_id,)
        ).fetchall()

    events = defaultdict(list)
    for weekday, start_time, end_time, is_preferred in rows:
        start_time = int(start_time)
        end_time = int(end_time)

        events[weekday].append((start_time, +1, is_preferred))
        events[weekday].append((end_time, -1, is_preferred))

        print(
            f"{weekday}: "
            f"{minutes_to_label(start_time)}–{minutes_to_label(end_time)} "
            f"Preferred: {is_preferred}"
        )

    for weekday, points in events.items():
        print(
            f"{weekday}: "
            f"{points}"
        )

    results = []

    for weekday, points in events.items():
        points.sort(key=lambda x: (x[0], x[1]))
        print(points)
        count = 0
        pref_count = 0
        for i in range(len(points) - 1):
            time, delta, pref_delta = points[i]
            count += delta  # apply change at boundary
            pref_count += pref_delta

            next_time = points[i + 1][0]

            if count >= min_people and time < next_time:
                results.append((weekday, time, next_time, count, pref_count))

            results.sort(key=lambda r: (r[3], r[4], r[0]), reverse=True)

    for weekday, start, end, count, pref_count in results:
        print(
            f"For {weekday}: "
            f"{minutes_to_label(start)}–{minutes_to_label(end)} "
            f"for {count} people) "
            f"and preferred for {pref_count} people."
        )
    return results