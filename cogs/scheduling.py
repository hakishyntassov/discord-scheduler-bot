# cogs/scheduling.py
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, date
from dateutil.tz import gettz

from config import SERVER_TZ_NAME, SCHEDULE_EXPIRE_HOURS
import scheduler.db as db
from scheduler.views import SessionView, monday_of_week, build_embed

class Scheduling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="schedule", description="Create a schedule session for this week.")
    @app_commands.describe(title="Title of the event")
    async def schedule(self, interaction: discord.Interaction, title: str):
        tz = gettz(SERVER_TZ_NAME)
        now = datetime.now(tz)

        week_start = monday_of_week(now.date())
        expires_at = now + timedelta(hours=SCHEDULE_EXPIRE_HOURS)

        view = SessionView()
        embed = build_embed(title, week_start, expires_at, participants=0, submitted=0)

        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()

        await db.create_session(
            guild_id=interaction.guild_id or 0,
            channel_id=interaction.channel_id or 0,
            message_id=msg.id,
            title=title,
            week_start=week_start.isoformat(),
            expires_at=expires_at.isoformat(),
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Scheduling(bot))
