import discord
from discord.ext import commands
from config import TOKEN
from config import GUILD_ID

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

@bot.tree.command(name="schedule", description = "Schedule an event", guild=discord.Object(id=GUILD_ID))
async def schedule(interaction: discord.Interaction, title: str):
    await interaction.response.send_message(f"{bot.user} created event: {title}")

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

bot.run(TOKEN)