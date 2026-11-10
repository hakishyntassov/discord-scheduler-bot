"""
Pure scheduling logic, no Discord or DB stuff in here so it's easy to test.

Availability is stored as hourly slots: (date, hour). Hours can go past 24
when the window crosses midnight, e.g. a 6pm-2am window is hours 18..25,
and hour 25 on Friday just means 1am Saturday.
"""
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from config import EVENT_TZ, MAX_SLOTS_PER_DAY

TZ = ZoneInfo(EVENT_TZ)

_TIME_RE = re.compile(r"^\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm|a|p)?\s*$", re.IGNORECASE)
_SPLIT_RE = re.compile(r"\s*(?:-|–|\bto\b)\s*", re.IGNORECASE)


# ---------- hour window ----------

def _to_minutes(text: str) -> int:
    m = _TIME_RE.match(text)
    if not m:
        raise ValueError(f"couldn't read the time `{text}`")
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = (m.group(3) or "").lower()
    if ampm:
        if not 1 <= hour <= 12:
            raise ValueError(f"`{text}` isn't a real time")
        if ampm.startswith("a"):
            hour = 0 if hour == 12 else hour
        else:
            hour = hour if hour == 12 else hour + 12
    elif hour > 24:
        raise ValueError(f"`{text}` isn't a real time")
    return hour * 60 + minute


def parse_hour_window(text: str) -> tuple[int, int]:
    """'10am-12am' -> (10, 24), '6pm-2am' -> (18, 26). End is exclusive."""
    parts = _SPLIT_RE.split(text.strip(), maxsplit=1)
    if len(parts) != 2:
        raise ValueError("hours should look like `10am-12am` or `6pm-2am`")
    start = _to_minutes(parts[0]) // 60
    end = math.ceil(_to_minutes(parts[1]) / 60)
    if end == 0:
        end = 24
    if end <= start:
        end += 24  # crosses midnight
    if end - start > MAX_SLOTS_PER_DAY:
        raise ValueError(f"that's {end - start} hours, max is {MAX_SLOTS_PER_DAY} per day")
    return start, end


# ---------- labels ----------

def hour_label(hour: int) -> str:
    """Short label for grid buttons: 10a, 12p, 1a."""
    h = hour % 24
    return f"{h % 12 or 12}{'a' if h < 12 else 'p'}"


def time_label(hour: int) -> str:
    """Longer label for embeds: 10am, 12pm, 1am."""
    h = hour % 24
    return f"{h % 12 or 12}{'am' if h < 12 else 'pm'}"


def day_label(d: date) -> str:
    return d.strftime("%a %-m/%-d")


def tz_abbrev() -> str:
    return datetime.now(TZ).tzname() or EVENT_TZ


# ---------- dates ----------

def slot_start(d: date, hour: int) -> datetime:
    return datetime.combine(d, time(0), tzinfo=TZ) + timedelta(hours=hour)


def event_dates(start_timep: datetime, end_timep: datetime) -> list[date]:
    first = start_timep.astimezone(TZ).date()
    last = end_timep.astimezone(TZ).date()
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


# ---------- ranking ----------

@dataclass
class Block:
    day: date
    start_hour: int
    end_hour: int  # exclusive
    people: frozenset
    preferred: frozenset

    @property
    def hours(self) -> int:
        return self.end_hour - self.start_hour

    @property
    def start_dt(self) -> datetime:
        return slot_start(self.day, self.start_hour)

    @property
    def end_dt(self) -> datetime:
        return slot_start(self.day, self.end_hour)


def _slot_map(rows):
    """rows of (user_id, slot_date, hour, preferred) -> {(date, hour): {user_id: preferred}}"""
    slots = defaultdict(dict)
    for user_id, slot_date, hour, preferred in rows:
        slots[(slot_date, hour)][user_id] = bool(preferred)
    return slots


def rank_blocks(rows, dates: list[date], day_start: int, day_end: int) -> list[Block]:
    """
    Splits each day into runs of consecutive hours where the exact same group
    is free, then ranks them: most people, then most stars, then longest.
    """
    slots = _slot_map(rows)
    blocks: list[Block] = []

    for d in dates:
        run = None
        for h in range(day_start, day_end):
            who = slots.get((d, h), {})
            people = frozenset(who)
            stars = frozenset(u for u, p in who.items() if p)
            if run and people == run.people:
                run.end_hour = h + 1
                run.preferred = run.preferred | stars
                continue
            if run:
                blocks.append(run)
            run = Block(d, h, h + 1, people, stars) if people else None
        if run:
            blocks.append(run)

    blocks.sort(key=lambda b: (-len(b.people), -len(b.preferred), -b.hours, b.day, b.start_hour))
    return blocks


def day_summary(rows, dates: list[date], day_start: int, day_end: int) -> list[tuple[date, int]]:
    """Most people free at any one time, per day."""
    slots = _slot_map(rows)
    return [
        (d, max((len(slots.get((d, h), {})) for h in range(day_start, day_end)), default=0))
        for d in dates
    ]


def pick_runner_ups(blocks: list[Block], best: Block, total: int) -> list[Block]:
    """
    One backup per day, never on the winner's day. On each day the longest
    stretch wins (ties go to more people, then more stars). Needs at least
    half the group free to count.
    """
    floor = max(2, -(-total // 2))
    by_day: dict[date, Block] = {}
    for b in blocks:
        if b.day == best.day or len(b.people) < floor:
            continue
        cur = by_day.get(b.day)
        if cur is None or (b.hours, len(b.people), len(b.preferred)) > (cur.hours, len(cur.people), len(cur.preferred)):
            by_day[b.day] = b
    return sorted(by_day.values(), key=lambda b: (-len(b.people), -len(b.preferred), -b.hours, b.day))


def ranked_options(blocks: list[Block], total: int) -> list[Block]:
    """Winner first, then the backups in order. Reschedule walks down this list."""
    if not blocks:
        return []
    return [blocks[0], *pick_runner_ups(blocks, blocks[0], total)]
