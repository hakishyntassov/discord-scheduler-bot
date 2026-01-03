# cogs/scheduling.py
import discord
from discord import app_commands
from discord.ext import commands

from views.schedule_views import SignupView

class Scheduling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="schedule")
    async def schedule(self, interaction: discord.Interaction, title: str, role: discord.Role | None = None):
        await interaction.response.send_message(
            f"📅 Event: **{title}**\nEligible role: {role.mention if role else 'Everyone'}",
            view=SignupView(allowed_role_id=role.id if role else None)
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Scheduling(bot))
