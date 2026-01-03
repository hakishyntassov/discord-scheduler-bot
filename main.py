# main.py
import discord
from discord.ext import commands

from config import TOKEN
from views.signup_view import SignupView
from views.day_view import DayView

class SchedulerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Register persistent views
        self.add_view(SignupView())

        # Load cogs
        await self.load_extension("cogs.scheduling")

        # Sync slash commands
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user}")

bot = SchedulerBot()
bot.run(TOKEN)
