import re, discord, logging
from discord.ext import commands
from config import TOKEN
from views.views import rsvpView
from views.schedule_views import (
    PickTimesButton, PeekButton, LockInButton, AddEventButton, RescheduleButton,
    build_open_embed, open_view,
)
from time_parse import parse_time, parse_dur, parse_day
from datetime import timedelta, timezone, datetime, time as dtime
from database import init_db, add_event, create_schedule_event, get_event
from scheduling import TZ, parse_hour_window
from config import DEFAULT_HOURS, MAX_DAYS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

async def setup_hook():
    await init_db()
    logger.info("Database initialized")
    # lets the schedule buttons keep working after the bot restarts
    bot.add_dynamic_items(PickTimesButton, PeekButton, LockInButton, AddEventButton, RescheduleButton)
    await bot.tree.sync()

bot.setup_hook = setup_hook

@bot.event
async def on_ready():
    logger.info("Application ID: %s", bot.application_id)
    logger.info("Logged in as %s", bot.user)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"> You're doing that too fast. Try again in **{error.retry_after:.1f}s**.",
            ephemeral=True
        )
    else:
        logger.error("Unhandled app command error: %s", error, exc_info=True)
        if not interaction.response.is_done():
            await interaction.response.send_message("> Something went wrong.", ephemeral=True)

@bot.tree.command(name="rsvp", description="RSVP")
@discord.app_commands.checks.cooldown(1, 30.0, key=lambda i: i.user.id)
async def rsvp(interaction: discord.Interaction,
               title: str,
               time: str,
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

    logger.debug("rsvp participants (%d): %s", len(participants), [m.id for m in participants])

    # TIME PARSING
    start_base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_dt = await parse_time(time, start_base)
    logger.debug("rsvp start_dt: %s", start_dt)
    formatted_time = discord.utils.format_dt(start_dt, style='F')
    logger.debug("rsvp formatted_time: %s", formatted_time)
    if duration is None:
        end_dt = None
        formatted_end = ""
    else:
        end_dt = await parse_dur(start_dt, duration)
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
        value="",
        inline=True
    )
    # MAYBE LIST
    embed.add_field(
        name=f"\❔**Maybe** (0/{len(participants)})",
        value="",
        inline=True
    )
    # DECLINED LIST
    embed.add_field(
        name=f"\❌ **Declined** (0/{len(participants)})",
        value="",
        inline=True
    )
    message = await interaction.followup.send(f"> {','.join(m.mention for m in participants)} RSVP to this event :)", wait=True)
    # DISPLAY EMBED AND BUTTONS
    event_id = await add_event(
        title=title,
        channel_id=interaction.channel.id,
        guild_id=interaction.guild.id,
        message_id=message.id,
        count_members=len(participants),
        start_timep=start_dt,
        end_timep=end_dt
    )
    # BUTTONS
    view = rsvpView(
        title=title,
        event_id=event_id,
        participants=participants
    )
    await message.edit(embed=embed, view=view)

@bot.tree.command(name="schedule", description="Find the best time for a group")
@discord.app_commands.describe(
    title="What's the event",
    start="First day to consider, like 'friday' or 'nov 20'",
    end="Last day to consider (defaults to a week)",
    hours="Hours to show each day, like '10am-12am' or '6pm-2am'",
    role="Who to schedule with",
    users="Or @ specific people",
)
@discord.app_commands.checks.cooldown(1, 30.0, key=lambda i: i.user.id)
async def schedule(interaction: discord.Interaction,
                   title: str,
                   start: str,
                   end: str | None = None,
                   hours: str | None = None,
                   role: discord.Role | None = None,
                   users: str | None = None,
                   description: str | None = None):
    # HOURS (checked before deferring so errors can be private)
    try:
        day_start_hour, day_end_hour = parse_hour_window(hours or DEFAULT_HOURS)
    except ValueError as e:
        await interaction.response.send_message(f"> {e}", ephemeral=True)
        return
    await interaction.response.defer()

    # PERIOD
    base = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    start_day = await parse_day(start, base)
    end_day = await parse_day(end, base) if end else None
    if start_day is None or (end and end_day is None):
        await interaction.followup.send("> I couldn't read those dates, try something like `friday` or `nov 20`.", ephemeral=True)
        return
    if end_day is None:
        end_day = start_day + timedelta(days=6)
    if end_day < start_day:
        end_day = end_day + timedelta(days=7)
    if (end_day - start_day).days + 1 > MAX_DAYS:
        await interaction.followup.send(f"> That's too many days, max is {MAX_DAYS}.", ephemeral=True)
        return
    start_timep = datetime.combine(start_day, dtime(0, 0), tzinfo=TZ)
    end_timep = datetime.combine(end_day, dtime(23, 59, 59), tzinfo=TZ)

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
    if not participants:
        await interaction.followup.send("> Nobody to schedule with, try a role or some @mentions.", ephemeral=True)
        return

    mentions = ",".join(m.mention for m in participants)
    message = await interaction.followup.send(f"> {mentions} pick your times below :)", wait=True)
    event_id = await create_schedule_event(
        title=title,
        channel_id=interaction.channel.id,
        guild_id=interaction.guild.id,
        message_id=message.id,
        creator_id=interaction.user.id,
        description=description,
        location=None,
        start_timep=start_timep,
        end_timep=end_timep,
        day_start_hour=day_start_hour,
        day_end_hour=day_end_hour,
        participant_ids=[m.id for m in participants],
    )
    event = await get_event(event_id)
    embed = build_open_embed(event, [m.id for m in participants], [])
    await message.edit(embed=embed, view=open_view(event_id))
    logger.info("Created schedule event '%s' (id=%s) in guild %s", title, event_id, interaction.guild.id)

bot.run(TOKEN) # RUN THE BOT