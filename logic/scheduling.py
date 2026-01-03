# cogs/scheduling.py
import discord
from discord import app_commands
from discord.ext import commands

from views.schedule_views import ScheduleView

class Scheduling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="schedule")
    async def schedule(self, interaction: discord.Interaction, title: str):
        await interaction.response.send_message(
            f"📅 Created a schedule for **{title}**",
            view=ScheduleView()
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Scheduling(bot))
