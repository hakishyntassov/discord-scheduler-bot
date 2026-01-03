# flow.py
from typing import Dict, Tuple
import discord
from views import PreferredDayView

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_LABELS = {
    "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
    "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday"
}

waiting_index: Dict[Tuple[int, int], int] = {}
# key: (guild_id, user_id) -> index in DAYS

def prompt_text(day: str, position: int) -> str:
    # position is 1..7 for user-facing clarity
    return (
        f"**Day {position} of 7 — {DAY_LABELS[day]}**\n"
        "Type your availability in **one line** (comma-separated list).\n"
        "Examples: `8pm` • `6pm, 8pm-11pm` • `18:00, 20:30-23:00` • `none`\n"
        "(If you don’t type an end time, it defaults to **midnight**.)"
    )

async def start_flow(channel: discord.TextChannel, guild_id: int, user_id: int):
    waiting_index[(guild_id, user_id)] = 0
    day = DAYS[0]
    await channel.send(prompt_text(day, 1), view=PreferredDayView(day))

async def advance_flow(channel: discord.TextChannel, guild_id: int, user_id: int) -> bool:
    """
    Advances to next day and prompts it.
    Returns True if finished (after Sunday), False otherwise.
    """
    key = (guild_id, user_id)
    waiting_index[key] += 1

    if waiting_index[key] >= len(DAYS):
        waiting_index.pop(key, None)
        await channel.send("✅ **All days saved!** You can still click ⭐ Preferred on any of the day prompts.")
        return True

    idx = waiting_index[key]
    day = DAYS[idx]
    await channel.send(prompt_text(day, idx + 1), view=PreferredDayView(day))
    return False

def get_current_day(guild_id: int, user_id: int):
    key = (guild_id, user_id)
    if key not in waiting_index:
        return None
    idx = waiting_index[key]
    return DAYS[idx], idx
