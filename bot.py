import discord
from discord import app_commands
from datetime import datetime, timedelta
import re
from collections import defaultdict
import os
import asyncio
from config import TOKEN
# =========================
# CONFIG
# =========================
#TOKEN = os.getenv("DISCORD_TOKEN")  # set this in your environment
POLL_DURATION_HOURS = 24
DEFAULT_DURATION_MINUTES = 240  # 4 hours

# =========================
# DISCORD SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# =========================
# IN-MEMORY STORAGE
# channel_id -> schedule data
# =========================
ACTIVE_SCHEDULES = {}

WEEKDAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# =========================
# TIME PARSING
# =========================
def parse_time_range(day_key: str, text: str):
    """
    Parses time strings like:
    7pm
    7-11pm
    7:30-10:15pm
    """
    text = text.lower().strip()

    pattern = r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?(?:\s*-\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?)?"
    match = re.match(pattern, text)

    if not match:
        return None

    sh, sm, sap, eh, em, eap = match.groups()
    sh, sm = int(sh), int(sm or 0)

    if sap == "pm" and sh != 12:
        sh += 12
    if sap == "am" and sh == 12:
        sh = 0

    start_minutes = sh * 60 + sm

    if eh:
        eh, em = int(eh), int(em or 0)
        if eap == "pm" and eh != 12:
            eh += 12
        if eap == "am" and eh == 12:
            eh = 0
        end_minutes = eh * 60 + em
    else:
        end_minutes = start_minutes + DEFAULT_DURATION_MINUTES

    end_minutes = min(end_minutes, 1440)

    return (day_key, start_minutes, end_minutes)

# =========================
# SLASH COMMAND: /schedule
# =========================
@tree.command(name="schedule", description="Create a new game schedule")
@app_commands.describe(title="Event title (e.g. Game Night)")
async def schedule(interaction: discord.Interaction, title: str):
    ACTIVE_SCHEDULES[interaction.channel_id] = {
        "title": title,
        "responses": defaultdict(list),
        "end_time": datetime.utcnow() + timedelta(hours=POLL_DURATION_HOURS)
    }

    await interaction.response.send_message(
        f"🎮 **{title}**\n\n"
        "Submit your availability using `/avail`.\n"
        "Only fill the days you're free.\n\n"
        f"⏳ Poll closes in {POLL_DURATION_HOURS} hours."
    )

# =========================
# SLASH COMMAND: /avail
# =========================
@tree.command(name="avail", description="Submit your availability by day")
@app_commands.describe(
    monday="Example: 7-11pm",
    tuesday="Example: 6-9pm",
    wednesday="Example: 8pm",
    thursday="Example: 7-10pm",
    friday="Example: 6-10pm",
    saturday="Example: 1-5pm",
    sunday="Example: 2-6pm"
)
async def avail(
    interaction: discord.Interaction,
    monday: str | None = None,
    tuesday: str | None = None,
    wednesday: str | None = None,
    thursday: str | None = None,
    friday: str | None = None,
    saturday: str | None = None,
    sunday: str | None = None
):
    schedule = ACTIVE_SCHEDULES.get(interaction.channel_id)
    if not schedule:
        await interaction.response.send_message(
            "❌ No active schedule in this channel.",
            ephemeral=True
        )
        return

    user = interaction.user.display_name
    added = False

    day_inputs = {
        "mon": monday,
        "tue": tuesday,
        "wed": wednesday,
        "thu": thursday,
        "fri": friday,
        "sat": saturday,
        "sun": sunday
    }

    for day, text in day_inputs.items():
        if text:
            parsed = parse_time_range(day, text)
            if not parsed:
                await interaction.response.send_message(
                    f"❌ Couldn't understand `{text}`.",
                    ephemeral=True
                )
                return

            schedule["responses"][parsed].append(user)
            added = True

    if not added:
        await interaction.response.send_message(
            "⚠️ You didn't enter any availability.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "✅ Availability saved!",
        ephemeral=True
    )

# =========================
# BACKGROUND TASK: EVALUATE
# =========================
async def evaluate_schedules():
    await client.wait_until_ready()

    while True:
        now = datetime.utcnow()

        for channel_id, data in list(ACTIVE_SCHEDULES.items()):
            if now >= data["end_time"]:
                channel = client.get_channel(channel_id)
                if not channel:
                    del ACTIVE_SCHEDULES[channel_id]
                    continue

                ranked = sorted(
                    data["responses"].items(),
                    key=lambda x: (-len(x[1]), WEEKDAY_ORDER.index(x[0][0]))
                )

                if not ranked:
                    await channel.send(
                        f"❌ **{data['title']}**\nNo availability submitted."
                    )
                    del ACTIVE_SCHEDULES[channel_id]
                    continue

                msg = f"✅ **Best Times for {data['title']}**\n\n"
                for i, ((day, start, end), users) in enumerate(ranked[:5], 1):
                    msg += (
                        f"{i}️⃣ **{day.title()} "
                        f"{start//60}:{start%60:02d}–{end//60}:{end%60:02d}** "
                        f"({len(users)} people)\n"
                    )

                await channel.send(msg)
                del ACTIVE_SCHEDULES[channel_id]

        await asyncio.sleep(60)

# =========================
# BOT READY
# =========================
@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")

client.loop.create_task(evaluate_schedules())
client.run(TOKEN)