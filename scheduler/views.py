# scheduler/views.py
import discord
from datetime import datetime, timedelta, date
from dateutil.tz import gettz

from config import SERVER_TZ_NAME, DEFAULT_DURATION_MINUTES, TOP_RESULTS
from scheduler.timeparse import parse_time_to_minutes, format_minutes_label, parse_duration_to_minutes
from scheduler.logic import DAY_NAMES, compute_best_overlaps
import scheduler.db as db

def monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())

def build_embed(title: str, week_start: date, expires_at: datetime, participants: int, submitted: int) -> discord.Embed:
    week_end = week_start + timedelta(days=6)
    e = discord.Embed(
        title=f"Schedule: {title}",
        description="Here's how it works!\n1) **Join the group**\n2) **Pick days/times**\n3) **Submit**\n4) **Results will show the best overlaps**"
    )
    e.add_field(name="Week (Mon–Sun)", value=f"{week_start.isoformat()} → {week_end.isoformat()}", inline=False)
    e.add_field(name="Expires (server time)", value=expires_at.strftime("%Y-%m-%d %I:%M %p"), inline=False)
    e.add_field(name="Status", value=f"Participants: {participants} | Submitted: {submitted}", inline=False)
    return e

class TimeModal(discord.ui.Modal, title="Enter start time"):
    time_text = discord.ui.TextInput(
        label="Start time",
        placeholder="Example: 8pm or 20:00",
        required=True,
        max_length=20,
    )

    # duration_text = discord.ui.TextInput(
    #     label="Duration",
    #     placeholder="Example: 30mins or 2hrs",
    #     required=True,
    #     max_length=20,
    # )

    def __init__(self, session_id: int, user_id: int, day_index: int):
        super().__init__()
        self.session_id = session_id
        self.user_id = user_id
        self.day_index = day_index

    async def on_submit(self, interaction: discord.Interaction):
        try:
            minutes = parse_time_to_minutes(str(self.time_text.value))
            #duration_minutes = parse_duration_to_minutes(str(self.duration_text.value))
        except ValueError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)

        await db.upsert_availability(
            session_id=self.session_id,
            user_id=self.user_id,
            day_index=self.day_index,
            start_minutes=minutes,
            duration_minutes=DEFAULT_DURATION_MINUTES,
        )

        await interaction.response.send_message(
            f"Saved **{DAY_NAMES[self.day_index]} {format_minutes_label(minutes)}**",
            ephemeral=True,
        )

class PickDaysView(discord.ui.View):
    def __init__(self, session_id: int, user_id: int):
        super().__init__(timeout=300)
        self.session_id = session_id
        self.user_id = user_id

        for i, name in enumerate(DAY_NAMES):
            self.add_item(PickDayButton(i, name))

class PickDayButton(discord.ui.Button):
    def __init__(self, day_index: int, label: str):
        super().__init__(style=discord.ButtonStyle.secondary, label=label)
        self.day_index = day_index

    async def callback(self, interaction: discord.Interaction):
        v: PickDaysView = self.view  # type: ignore
        await interaction.response.send_modal(TimeModal(v.session_id, v.user_id, self.day_index))

class SessionView(discord.ui.View):
    """Persistent view on the main schedule message."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success, custom_id="sched:join")
    async def join(self, interaction: discord.Interaction, _btn: discord.ui.Button):
        row = await db.get_session_by_message(interaction.message.id)
        if not row:
            return await interaction.response.send_message("Session not found.", ephemeral=True)

        session_id, _guild_id, _channel_id, _msg_id, title, week_start_s, expires_s = row

        await db.add_participant(session_id, interaction.user.id)

        parts = await db.list_participants(session_id)
        participants_count = len(parts)
        submitted_count = sum(1 for _uid, sub in parts if sub == 1)

        week_start = date.fromisoformat(week_start_s)
        expires_at = datetime.fromisoformat(expires_s)

        await interaction.response.edit_message(
            embed=build_embed(title, week_start, expires_at, participants_count, submitted_count),
            view=self,
        )

    @discord.ui.button(label="Pick", style=discord.ButtonStyle.primary, custom_id="sched:pick")
    async def pick(self, interaction: discord.Interaction, _btn: discord.ui.Button):
        row = await db.get_session_by_message(interaction.message.id)
        if not row:
            return await interaction.response.send_message("Session not found.", ephemeral=True)

        session_id = row[0]
        parts = await db.list_participants(session_id)
        active = {uid for uid, _sub in parts}

        if interaction.user.id not in active:
            return await interaction.response.send_message("Hit **Join** first.", ephemeral=True)

        await interaction.response.send_message(
            "Pick a day, then enter a start time:",
            view=PickDaysView(session_id, interaction.user.id),
            ephemeral=True,
        )

    @discord.ui.button(label="Submit", style=discord.ButtonStyle.secondary, custom_id="sched:submit")
    async def submit(self, interaction: discord.Interaction, _btn: discord.ui.Button):
        row = await db.get_session_by_message(interaction.message.id)
        if not row:
            return await interaction.response.send_message("Session not found.", ephemeral=True)

        session_id, _guild_id, _channel_id, _msg_id, title, week_start_s, expires_s = row

        parts = await db.list_participants(session_id)
        active = {uid for uid, _sub in parts}
        if interaction.user.id not in active:
            return await interaction.response.send_message("Hit **Join** first.", ephemeral=True)

        avail = await db.list_availability(session_id)
        if not any(uid == interaction.user.id for (uid, _d, _s, _dur) in avail):
            return await interaction.response.send_message("Add at least one day/time first using **Pick**.", ephemeral=True)

        await db.mark_submitted(session_id, interaction.user.id)

        parts = await db.list_participants(session_id)
        participants_count = len(parts)
        submitted_count = sum(1 for _uid, sub in parts if sub == 1)

        week_start = date.fromisoformat(week_start_s)
        expires_at = datetime.fromisoformat(expires_s)

        await interaction.response.edit_message(
            embed=build_embed(title, week_start, expires_at, participants_count, submitted_count),
            view=self,
        )

    @discord.ui.button(label="Results", style=discord.ButtonStyle.danger, custom_id="sched:results")
    async def results(self, interaction: discord.Interaction, _btn: discord.ui.Button):
        row = await db.get_session_by_message(interaction.message.id)
        if not row:
            return await interaction.response.send_message("Session not found.", ephemeral=True)

        session_id = row[0]
        parts = await db.list_participants(session_id)
        participants = [uid for uid, _sub in parts]
        if not participants:
            return await interaction.response.send_message("No participants yet.", ephemeral=True)

        availability = await db.list_availability(session_id)
        overlaps = compute_best_overlaps(participants, availability, top_n=TOP_RESULTS)

        if not overlaps:
            return await interaction.response.send_message("No availability submitted yet.", ephemeral=True)

        lines = [f"**{DAY_NAMES[day]} {format_minutes_label(start)}** — {cnt}/{len(participants)}"
                 for (day, start, cnt) in overlaps]

        await interaction.response.send_message("Top overlaps:\n" + "\n".join(lines), ephemeral=True)
