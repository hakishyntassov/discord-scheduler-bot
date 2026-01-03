import discord
from discord.ext import commands
from discord import app_commands
from config import TOKEN
from views.schedule_views import ScheduleView

class SchedulerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(ScheduleView())
        # Load cogs
        await self.load_extension("logic.scheduling")
        # Sync slash commands
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user} (id={self.user.id})")

bot = SchedulerBot()
bot.run(TOKEN)
print("BOT VERSION: 2025-01-30 v3")