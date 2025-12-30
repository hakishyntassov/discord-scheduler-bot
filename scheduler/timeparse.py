# scheduler/timeparse.py
import re

TIME_RE = re.compile(
    r"^\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*$",
    re.IGNORECASE
)
DURATION_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours)\s*$",
    re.IGNORECASE
)
def parse_duration_to_minutes(text: str) -> int:
    """
    Accepts: '8pm', '8 pm', '8:30pm', '20', '20:00', '7:15 am'
    Returns minutes since midnight (0-1439).
    """
    m = DURATION_RE.match(text)
    if not m:
        raise ValueError("Invalid duration time. Try like '30mins' or '2hr'.")

    value = float(m.group(1))
    unit = m.group(2).lower()

    if unit.startswith("h"):
        return int(value * 60)
    else:
        return int(value)

def parse_time_to_minutes(text: str) -> int:
    """
    Accepts: '8pm', '8 pm', '8:30pm', '20', '20:00', '7:15 am'
    Returns minutes since midnight (0-1439).
    """
    m = TIME_RE.match(text)
    if not m:
        raise ValueError("Invalid time. Try like '8pm' or '20:00'.")

    hour = int(m.group(1))
    minute = int(m.group(2) or "0")
    suffix = (m.group(3) or "").lower()

    if minute > 59:
        raise ValueError("Minutes must be 00–59.")

    if suffix in ("am", "pm"):
        if hour < 1 or hour > 12:
            raise ValueError("For am/pm, hour must be 1–12.")
        if suffix == "am":
            hour = 0 if hour == 12 else hour
        else:
            hour = 12 if hour == 12 else hour + 12
    else:
        if hour > 23:
            raise ValueError("For 24h time, hour must be 0–23.")

    return hour * 60 + minute

def format_minutes_label(minutes: int) -> str:
    hour = minutes // 60
    minute = minutes % 60
    ampm = "AM" if hour < 12 else "PM"
    hr12 = hour % 12
    hr12 = 12 if hr12 == 0 else hr12
    return f"{hr12}:{minute:02d} {ampm}"
