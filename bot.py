import re
import discord
from discord.ext import commands
from config import TOKEN
from views.views import ScheduleView, rsvpView
from db import init_db, add_event, find_overlaps
from time_parse import parse_time, parse_end_time, parse_end_day
from datetime import timedelta
from database import init_database, close_database

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

@bot.event
async def on_ready():
    await init_database()
    print("Database initialized")
    event_id = await add_event("first", "1", "1", "1",
                    "1", "2026-01-27 15:00:00", "2026-01-29 15:00:00")
    print(f"Event created: {event_id}")
    await bot.tree.sync()
    print("Application ID:", bot.application_id)
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

@bot.tree.command(name="rsvp", description="RSVP")
async def rsvp(interaction: discord.Interaction,
               title: str,
               datetime: str,
               description: str | None = None,
               duration: str | None = None,
               location: str | None = None,
               role: discord.Role | None = None,
               users: str | None = None):
    await interaction.response.defer()
    # PARTICIPANTS
    channel = interaction.channel
    participants = set()
    if role:
        participants.update(m for m in role.members if not m.bot)
    if users:
        user_ids = re.findall(r"<@!?(\d+)>", users)
        for uid in user_ids:
            member = interaction.guild.get_member(int(uid))
            if member and not member.bot:
                participants.add(member)
    if (role is None) and (users is None):
        participants.update(m for m in channel.members if not m.bot)

    print(f"Participants ({len(participants)}): {[m.id for m in participants]}")

    # TIME PARSING
    start_dt = parse_time(datetime)
    formatted_time = discord.utils.format_dt(start_dt, style='F')
    if duration is None:
        end_dt = None
        formatted_end = ""
    else:
        end_dt = parse_end_time(start_dt, duration)
        formatted_end = discord.utils.format_dt(end_dt, style='F')

    # EMBED
    embed = discord.Embed(
        title=f"Event: **{title}**",
        description=f"{description}" if description is not None else f"This event was created by <@{interaction.user.id}>",
        color=discord.Color.green()
    )
    # TIME FIELD
    embed.add_field(
        name="**Time**",
        value=f">>> From: {formatted_time}\nTo: {formatted_end}" if duration is not None else f"> {formatted_time}",
        inline=False
    )
    # LOCATION FIELD
    embed.add_field(
        name="**Location**",
        value=f"> {location}" if location is not None else f"> Not specified",
        inline=False
    )
    # PARTICIPANTS FIELD
    embed.add_field(
        name="**Participants**",
        value=f"> {','.join(m.mention for m in participants)}",
        inline=False
    )
    # ACCEPTED LIST
    embed.add_field(
        name=f"\✅ **Accepted** (0/{len(participants)})",
        value="> -",
        inline=True
    )
    # MAYBE LIST
    embed.add_field(
        name=f"\❔**Maybe** (0/{len(participants)})",
        value="> -",
        inline=True
    )
    # DECLINED LIST
    embed.add_field(
        name=f"\❌ **Declined** (0/{len(participants)})",
        value="> -",
        inline=True
    )
    # BUTTONS
    view = rsvpView(
        title=title,
        event_id=None,
        participants=participants
    )
    # DISPLAY EMBED AND BUTTONS
    message = await interaction.followup.send(embed=embed, view=view)
    event_id = add_event(
        title=title,
        channel_id=interaction.channel.id,
        guild_id=interaction.guild.id,
        message_id=message.id,
        count_members=len(participants),
        start_timep=start_dt,
        end_timep=end_dt
    )
    view.event_id = event_id


@bot.tree.command(name="schedule", description="Schedule an event")
async def schedule(interaction: discord.Interaction,
                   title: str,
                   start: str,
                   end: str | None = None,
                   role: discord.Role | None = None,
                   users: str | None = None,
                   description: str | None = None,
                   location: str | None = None):
    await interaction.response.defer()
    # PERIOD
    start_date = parse_time(start)
    print(start_date)
    start_date_formatted = discord.utils.format_dt(start_date, style='F')
    if end:
        end_date = parse_end_day(end)
    else:
        end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
    if start_date > end_date:
        end_date = end_date + timedelta(days=7)
    end_date_formatted = discord.utils.format_dt(end_date, style='F')
    # PARTICIPANTS
    channel = interaction.channel
    participants = set()
    if role:
        participants.update(m for m in role.members if not m.bot)
    if users:
        user_ids = re.findall(r"<@!?(\d+)>", users)
        for uid in user_ids:
            member = interaction.guild.get_member(int(uid))
            if member and not member.bot:
                participants.add(member)
    if (role is None) and (users is None):
        participants.update(m for m in channel.members if not m.bot)
    # DESCRIPTION
    if description is None:
        description = f"This event was created by <@{interaction.user.id}>"
    # LOCATION
    if location is None:
        location = "Not specified"
    # EMBED
    embed = discord.Embed(
        title=f"Event: **{title}**",
        description=(
            f"{description}\n\n"
            "**How it works**\n"
            "> In your DM, select the days/times\n"
            "> I will find the best time\n"
            "> Results will be posted here\n"
        ),
        color=discord.Color.blurple()
    )
    # PERIOD FIELD
    embed.add_field(
        name="**Schedule Period**",
        value=f">>> From: {start_date_formatted}\nTo: {end_date_formatted}",
        inline=False
    )
    # LOCATION FIELD
    embed.add_field(
        name="**Location**",
        value=f"> {location}",
        inline=False
    )
    # PARTICIPANTS FIELD
    embed.add_field(
        name="**Participants**",
        value=f"> {','.join(m.mention for m in participants)}",
        inline=False
    )
    # JOINED LIST
    embed.add_field(
        name="🧙‍♂️ Joined",
        value="",
        inline=False
    )
    # SUBMITTED LIST
    embed.add_field(
        name="☑️ Submitted",
        value="",
        inline=False
    )
    # BUTTONS
    view = ScheduleView(title=title, event_id=None, channel_id=channel.id, participants=participants)
    # ATTENTION MENTION
    # await channel.send(f"> {role.name} attention!" if role.name == "@everyone" else f"> {role.mention} attention!")
    # DISPLAY EMBED AND BUTTONS
    message = await interaction.followup.send(embed=embed, view=view)
    event_id = add_event(
        title=title,
        channel_id=interaction.channel.id,
        guild_id=interaction.guild.id,
        message_id=message.id,
        count_members=len(participants),
        start_timep=start_date,
        end_timep=end_date
    )
    view.event_id = event_id
    print(f'Created event: {title}')

init_db() # CREATE DATABASE TABLES
bot.run(TOKEN) # RUN THE BOT