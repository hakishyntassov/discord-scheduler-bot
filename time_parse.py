# Helper module to process time
from datetime import datetime, timedelta, timezone
from dateutil import parser
from zoneinfo import ZoneInfo
from durations_nlp import Duration

def to_minutes(hour, minute=0, ampm=None):
    hour = int(hour)
    minute = int(minute or 0)

    if ampm:
        ampm = ampm.lower()
        if ampm == "am":
            hour = 0 if hour == 12 else hour
        elif ampm == "pm":
            hour = 12 if hour == 12 else hour + 12
    else:
        # no am/pm provided
        # if hour >= 13, assume 24-hour
        if hour > 23:
            raise ValueError("Invalid hour")

    total = hour * 60 + minute
    return total

def minutes_to_label(minutes: int) -> str:
    if int(minutes) == 1439:
        return "midnight"
    else:
        minutes = int(minutes)
        hour = int(minutes // 60)
        minute = int(minutes % 60)
        ampm = "am" if hour < 12 else "pm"
        hour = hour % 12
        hour = 12 if hour == 0 else hour
        return f"{hour}:{minute:02d}{ampm}"

def time_to_label(weekday: int, minutes: int) -> datetime:
    minutes = int(minutes)
    hour = int(minutes // 60)
    minute = int(minutes % 60)
    year = 2026
    month = 1
    day = 30
    dt = datetime(year, month, day, hour, minute)
    return dt

def parse_time(time: str) -> datetime:
    default = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    dt = parser.parse(
        time,
        fuzzy=True,
        default=default
    )
    if dt < datetime.now():
        dt += timedelta(days=7)
    print(dt)
    return dt

def parse_end_day(time: str) -> datetime:
    default = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
    dt = parser.parse(
        time,
        fuzzy=True,
        default=default
    )
    if dt < datetime.now():
        dt += timedelta(days=7)
    print(dt)
    return dt

def parse_end_time(dt: datetime, dur: str = "0"):
    duration = Duration(dur)
    duration_minutes = duration.to_minutes()
    dt += timedelta(minutes=duration_minutes)
    print(dt)
    return dt

def parse_time_wd(weekday: int, minutes: int, user_tz: str) -> datetime:
    """
    weekday: 1=Monday ... 7=Sunday
    minutes: minutes from midnight
    """

    # --- validate ---
    if not 1 <= weekday <= 7:
        raise ValueError("weekday must be 1 (Mon) to 7 (Sun)")

    tz = ZoneInfo(user_tz)

    now = datetime.now(tz)
    today = now.date()

    # --- get next date for weekday ---
    days_ahead = (weekday - today.weekday() - 1) % 7
    days_ahead = 7 if days_ahead == 0 else days_ahead
    target_date = today + timedelta(days=days_ahead)

    # --- convert minutes to time ---
    hour = minutes // 60
    minute = minutes % 60

    dt = datetime(
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
        hour=hour,
        minute=minute,
        tzinfo=tz
    )

    return dt

def get_next_day(dt):
    return dt + timedelta(days=1)