import discord
from discord.ext import commands
from config import TOKEN
from config import GUILD_ID
from views.views import ScheduleView, rsvpView
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

@bot.tree.command(name="rsvp", description="RSVP")
async def rsvp(interaction: discord.Interaction, title: str, datetime: str, role: discord.Role):
    await interaction.response.defer()
    channel = interaction.channel
    members = [m for m in role.members if not m.bot]
    author = interaction.user.id
    role_mention = role.mention

    embed = discord.Embed(
        title=f"Event: **{title}**",
        description=f"<@{author}> *invites you to RSVP*",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="**Time**",
        value=f"> {datetime}",
        inline=False
    )

    embed.add_field(
        name="\✅ **Accepted**",
        value="",
        inline=True
    )

    embed.add_field(
        name="\❔**Maybe**",
        value="",
        inline=True
    )

    embed.add_field(
        name="\❌ **Declined**",
        value="",
        inline=True
    )

    view = rsvpView(
        title=title,
        event_id=None,
        role=role
    )

    message = await interaction.followup.send(embed=embed, view=view)
    event_id = add_event(
        title=title,
        channel_id=interaction.channel.id,
        guild_id=interaction.guild.id,
        message_id=message.id,
        count_members=len(members)
    )
    view.event_id = event_id


@bot.tree.command(name="schedule", description="Schedule an event")
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
            "**How it works**\n"
            "> In your DM, select the days/times\n"
            "> I will find the best time\n"
            "> Results will be posted here\n"
            f"Members included: {mentions}"
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🧙‍♂️ Joined",
        value="",
        inline=False
    )

    embed.add_field(
        name="☑️ Submitted",
        value="",
        inline=False
    )

    view = ScheduleView(title=title, event_id=None, channel_id=channel.id, role=role)
    mention_msg = await channel.send(f"> {role.name} attention!" if role.name == "@everyone" else f"> {role.mention} attention!")
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