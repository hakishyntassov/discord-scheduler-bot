# bot.py
import os
import discord
from discord import app_commands
from discord.ext import commands

from db import init_db, clear_day_ranges, insert_day_ranges
from parsing import parse_time_list
from flow import start_flow, advance_flow, get_current_day

from config import TOKEN

intents = discord.Intents.default()
intents.message_content = True  # REQUIRED for reading typed messages

bot = commands.Bot(command_prefix="!", intents=intents)

class Scheduler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="availability", description="Enter your availability Monday through Sunday (typed messages).")
    async def availability(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Use this in a server text channel.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Starting availability entry. I’ll prompt **Monday → Sunday** in order.",
            ephemeral=True
        )
        await start_flow(interaction.channel, interaction.guild.id, interaction.user.id)

async def setup_hook():
    await bot.add_cog(Scheduler(bot))

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print("Command sync failed:", e)

@bot.event
async def on_message(message: discord.Message):
    # Let commands still work
    await bot.process_commands(message)

    if message.author.bot or not message.guild or not isinstance(message.channel, discord.TextChannel):
        return

    current = get_current_day(message.guild.id, message.author.id)
    if not current:
        return  # user isn't in the flow

    day, idx = current

    # Parse one-line list
    try:
        ranges = parse_time_list(message.content)
    except ValueError as e:
        await message.channel.send(
            f"❌ {e}\nUse: `8pm` or `6pm, 8pm-11pm` or `18:00, 20:30-23:00` or `none`.",
            delete_after=10
        )
        return

    # Save: overwrite that day's ranges for this user
    clear_day_ranges(message.guild.id, message.author.id, day)
    insert_day_ranges(message.guild.id, message.author.id, day, ranges)

    # Confirm quickly (optional; keep chat clean)
    pretty = "none" if not ranges else ", ".join([f"{s}-{e}" for s, e in ranges])
    await message.channel.send(f"✅ Saved **{day}**.", delete_after=6)

    # Prompt next day
    await advance_flow(message.channel, message.guild.id, message.author.id)

async def main():
    if not TOKEN:
        raise RuntimeError("Missing DISCORD_TOKEN environment variable.")

    init_db()
    await setup_hook()
    await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
