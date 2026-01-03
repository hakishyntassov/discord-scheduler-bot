import discord
from discord import app_commands
from discord.ext import commands

from views.signup_view import SignupView

class Scheduling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="schedule", description="Create a weekly scheduler")
    async def schedule(self, interaction: discord.Interaction, title: str):
        await interaction.response.send_message(
            f"📅 **{title}**\nClick **Sign Up** to begin.",
            view=SignupView(channel_id=interaction.channel_id)
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Scheduling(bot))