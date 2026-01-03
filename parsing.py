# parsing.py
import re
from typing import List, Tuple, Optional

MIDNIGHT = 1440

def _to_minutes(hour: int, minute: int = 0, ampm: Optional[str] = None) -> int:
    hour = int(hour)
    minute = int(minute)

    if ampm:
        ampm = ampm.lower()
        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0

    return hour * 60 + minute

def parse_time_token(token: str) -> Tuple[int, int]:
    """
    Parses ONE token like:
      - "8pm"
      - "8pm-12am"
      - "18:00"
      - "18:00-22:00"
    Returns (start_min, end_min).
    If end is omitted -> defaults to MIDNIGHT.
    """
    t = token.strip().lower()

    # 24h range: 18:00-22:00
    m = re.fullmatch(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", t)
    if m:
        s = _to_minutes(m.group(1), m.group(2))
        e = _to_minutes(m.group(3), m.group(4))
        return s, e

    # 12h range: 8pm-12am (minutes optional)
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?(am|pm)\s*-\s*(\d{1,2})(?::(\d{2}))?(am|pm)", t)
    if m:
        s = _to_minutes(m.group(1), m.group(2) or 0, m.group(3))
        e = _to_minutes(m.group(4), m.group(5) or 0, m.group(6))
        if e == 0:
            e = MIDNIGHT
        return s, e

    # 24h start only: 18:00 -> midnight
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", t)
    if m:
        s = _to_minutes(m.group(1), m.group(2))
        return s, MIDNIGHT

    # 12h start only: 8pm -> midnight
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?(am|pm)", t)
    if m:
        s = _to_minutes(m.group(1), m.group(2) or 0, m.group(3))
        return s, MIDNIGHT

    raise ValueError(f"Invalid time format: '{token.strip()}'")

def parse_time_list(line: str) -> List[Tuple[int, int]]:
    """
    Parses the full one-line input (comma-separated list) for a day.
    - "none" => []
    - "6pm, 8pm-11pm" => [(1080,1440), (1200,1380)]
    """
    raw = line.strip().lower()

    if raw in {"none", "n/a", ""}:
        return []

    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    if not tokens:
        return []

    ranges: List[Tuple[int, int]] = []
    for tok in tokens:
        ranges.append(parse_time_token(tok))

    return ranges
