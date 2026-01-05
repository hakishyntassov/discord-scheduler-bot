import discord
from discord.ext import commands
from config import TOKEN
from config import GUILD_ID
from views.views import ScheduleView
from db import init_db, add_event

intents = discord.Intents.default()
intents.members = True
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
    channel = interaction.channel
    members = channel.members
    count = len([m for m in channel.members if not m.bot])
    author = interaction.user.name
    embed = discord.Embed(
        title=f"Event: **{title}**",
        description=(
            f"Event created by **{author}**\n\n"
            "**Instructions**\n"
            "• Select the days you are available\n"
            "• Submit your selections\n"
            "• Results will be sent automatically\n\n"
            f"Number of members: **{count}**"
        ),
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="👥 Joined",
        value="0",
        inline=False
    )

    # 1️⃣ send embed FIRST (no view yet)
    await interaction.response.send_message(embed=embed)

    # 2️⃣ get the message object
    message = await interaction.original_response()
    event_id = add_event(
        title=title,
        channel_id=interaction.channel.id,
        message_id=message.id
    )
    view = ScheduleView(title=title, event_id=event_id)
    await message.edit(view=view)
init_db()
bot.run(TOKEN)