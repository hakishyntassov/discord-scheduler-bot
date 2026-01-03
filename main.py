import discord
from discord.ext import commands
from discord import app_commands
from config import TOKEN

class SchedulerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user} (id={self.user.id})")

bot = SchedulerBot()

@bot.tree.command(name="schedule", description="Create a scheduling session")
@app_commands.describe(title="Title of the event")
async def schedule(interaction: discord.Interaction, title: str):
    await interaction.response.send_message(
        f"📅 **Schedule created**\n\n**Event:** {title}",
        ephemeral=False
    )

bot.run(TOKEN)
print("BOT VERSION: 2025-01-30 v3")