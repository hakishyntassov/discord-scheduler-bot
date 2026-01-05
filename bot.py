import discord
from discord.ext import commands
from config import TOKEN
from config import GUILD_ID
from views.views import JoinButton

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

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

@bot.tree.command(name="schedule", description = "Schedule an event", guild=discord.Object(id=GUILD_ID))
async def schedule(interaction: discord.Interaction, title: str):
    view = JoinButton(title=title)
    author = interaction.user.name
    await interaction.response.send_message(f"{author} created an event: {title}", view=view)

bot.run(TOKEN)