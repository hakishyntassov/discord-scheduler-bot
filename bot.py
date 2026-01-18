import discord
from discord.ext import commands
from config import TOKEN
from config import GUILD_ID
from views.views import ScheduleView
from db import init_db, add_event, find_overlaps

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Application ID:", bot.application_id)
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

@bot.tree.command(name="schedule", description = "Schedule an event")
async def schedule(interaction: discord.Interaction, title: str, role: discord.Role):
    await interaction.response.defer()

    channel = interaction.channel
    members = [m for m in role.members if not m.bot]
    count = len(members)
    author = interaction.user.name
    mentions = ", ".join(m.mention for m in members)

    embed = discord.Embed(
        title=f"Event: **{title}**",
        description=(
            "**Instructions**\n"
            "• Select the days/times you are available\n"
            "• Submit your selections\n"
            "• Results will be sent automatically\n\n"
            f"Members included: {mentions}"
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👥 Joined",
        value="0",
        inline=False
    )

    view = ScheduleView(title=title, event_id=None, channel_id=channel.id)

    message = await interaction.followup.send(embed=embed, view=view)
    event_id = add_event(
        title=title,
        channel_id=interaction.channel.id,
        guild_id=interaction.guild.id,
        message_id=message.id,
        count_members=count
    )
    view.event_id = event_id
    print(f'Created event: {title}')

init_db()
bot.run(TOKEN)