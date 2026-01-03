import discord
from discord.ext import commands

from config import TOKEN
from views.signup_view import SignupView

class SchedulerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # ONLY persistent view
        self.add_view(SignupView())

        await self.load_extension("cogs.scheduling")
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user}")

bot = SchedulerBot()
bot.run(TOKEN)