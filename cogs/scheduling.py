# cogs/scheduling.py
import discord
from discord import app_commands
from discord.ext import commands

from views.signup_view import SignupView

class Scheduling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="schedule", description="Create a weekly scheduler")
    @app_commands.describe(
        title="Event title",
        role="Role required to fill this out",
        users="Specific users required to fill this out",
    )
    async def schedule(
        self,
        interaction: discord.Interaction,
        title: str,
        role: discord.Role | None = None,
        users: list[discord.Member] | None = None,
    ):
        allowed_role_id = role.id if role else None
        allowed_user_ids = [u.id for u in users] if users else None

        await interaction.response.send_message(
            f"📅 **{title}**\nClick **Sign Up** to begin.",
            view=SignupView(
                channel_id=interaction.channel_id,
                allowed_role_id=allowed_role_id,
                allowed_user_ids=allowed_user_ids,
            )
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Scheduling(bot))
