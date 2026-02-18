import math
import logging
from datetime import timedelta, datetime, timezone
import discord
from database import add_join, user_in_event, save_availability, find_overlaps, submit_availability, \
    get_count_submits, get_count_members, get_joins, set_rsvp, get_rsvp_users, get_times, get_channel_message
from time_parse import to_minutes, minutes_to_label, time_to_label, parse_time_wd, get_next_day
from config import DAY_NAMES

logger = logging.getLogger(__name__)

class rsvpView(discord.ui.View):
    def __init__(self, title, event_id, participants):
        super().__init__(timeout=None)
        self.title = title
        self.event_id = event_id
        self.participants = participants

    @discord.ui.button(label="✅", style=discord.ButtonStyle.primary, row=0)
    async def rsvp_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if interaction.user in self.participants:
            await self.set_user(interaction, 3)
        else:
            await interaction.followup.send("> You can't RSVP to this event", ephemeral=True)

    @discord.ui.button(label="❔", style=discord.ButtonStyle.primary, row=0)
    async def maybe_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if interaction.user in self.participants:
            await self.set_user(interaction, 4)
        else:
            await interaction.followup.send("> You can't RSVP to this event", ephemeral=True)

    @discord.ui.button(label="❌", style=discord.ButtonStyle.primary, row=0)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if interaction.user in self.participants:
            await self.set_user(interaction, 5)
        else:
            await interaction.followup.send("> You can't RSVP to this event", ephemeral=True)

    async def set_user(self, interaction, new_status: int):
        if not await set_rsvp(self.event_id, interaction.user.id, new_status):
            await interaction.followup.send(
                "> You already RSVP'd to this event",
                ephemeral=True
            )
            return

        embed = interaction.message.embeds[0]
        total = len(self.participants)

        rows = await get_rsvp_users(self.event_id)

        accepted = []
        maybe = []
        declined = []

        for user_id, status in rows:
            if status == 3:
                accepted.append(f"> <@{user_id}>")
            elif status == 4:
                maybe.append(f"> <@{user_id}>")
            elif status == 5:
                declined.append(f"> <@{user_id}>")

        embed.set_field_at(
            3,
            name=f"✅ Accepted ({len(accepted)}/{total})",
            value="\n".join(accepted),
            inline=True
        )

        embed.set_field_at(
            4,
            name=f"❔ Maybe ({len(maybe)}/{total})",
            value="\n".join(maybe),
            inline=True
        )

        embed.set_field_at(
            5,
            name=f"❌ Declined ({len(declined)}/{total})",
            value="\n".join(declined),
            inline=True
        )

        await interaction.message.edit(embed=embed)

class ScheduleView(discord.ui.View):
    def __init__(self, title: str, event_id: int, channel_id: int, participants, location: str):
        super().__init__(timeout=None)
        self.title = title
        self.event_id = event_id
        self.channel_id = channel_id
        self.participants = participants
        self.location = location

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success, row=0)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)  # no visible reply
        user = interaction.user
        if user in self.participants:
            # prevent double-join
            if await user_in_event(self.event_id, user.id):
                await interaction.followup.send(
                    "> You already joined.",
                    ephemeral=True
                )
                return
            else:
                try:
                    await add_join(self.event_id, user.id)
                    joins = await get_joins(self.event_id)
                    #user_ids = [join[0] for join in list_joins]
                    names = []
                    for user_id in joins:
                        names.append(f"> <@{user_id}>")
                    embed = interaction.message.embeds[0]
                    embed.set_field_at(
                        3,
                        name="🧙‍♂️ Joined",
                        value="\n".join(names) if names else "-",
                        inline=False
                    )
                    if len(joins) >= len(self.participants):
                        self.join_button.disabled = True
                        self.join_button.label = "Everyone joined"
                        self.join_button.style = discord.ButtonStyle.secondary
                    await interaction.message.edit(embed=embed, view=self)

                    dm = await user.create_dm()
                    msg = await dm.send(
                        f"> Hi! You joined **{self.title}** event :)"
                    )

                    #times = await get_times(self.event_id)
                    #start_date_strp = datetime.strptime(times[0][0], "%Y-%m-%d %H:%M:%S")
                    #end_date_strp = datetime.strptime(times[0][1], "%Y-%m-%d %H:%M:%S")

                    start_date_strp, end_date_strp = await get_times(self.event_id)
                    start_dt_formatted = start_date_strp.strftime("%A %B %d, %Y")

                    await dm.send(
                        f"> Let’s set your availability for **{start_dt_formatted}**.",
                        view=AvailabilityView(
                            title = self.title,
                            event_id=self.event_id,
                            user_id=user.id,
                            start_date=start_date_strp,
                            end_date=end_date_strp,
                            day_id=start_date_strp.weekday(),
                            location=self.location
                        )
                    )
                    # optional confirmaon (ephemeral)
                    await interaction.followup.send(
                        f"> I’ve sent you a DM to submit your availability for **{self.title}**.",
                        ephemeral=True
                    )

                except discord.Forbidden:
                    # User has DMs closed
                    await interaction.followup.send(
                        "> I can’t DM you. Please enable DMs from server members.",
                        ephemeral=True
                    )
        else:
            await interaction.followup.send(
                "> Sorry, you are not allowed to join this event.",
                ephemeral=True
            )

    @discord.ui.button(label="Results", style=discord.ButtonStyle.danger, row=0)
    async def results_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        await interaction.response.defer(ephemeral=True)

        results = await find_overlaps(self.event_id, 1)

        if not results:
            await interaction.followup.send(
                "> No overlapping availability found.",
                ephemeral=True
            )
            return
        else:
            embed = discord.Embed(
                title="Top Availability",
                color=discord.Color.blurple()
            )

            shown = 0
            for weekday, start, end, count, pref_count, sd in results:
                date_formatted = sd.strftime("%a %m/%d/%y")
                count_word = "person" if count == 1 else "people"
                pref_word = "person" if pref_count == 1 else "people"
                embed.add_field(
                    name=f"{date_formatted}",
                    value=(
                        f"> {minutes_to_label(start)}–{minutes_to_label(end)}\n"
                        f"> ✅ {count} {count_word} available · ⭐ {pref_count} {pref_word} preferred"
                    ),
                    inline=False
                )
                shown += 1
                if shown == 5:
                    break

            await interaction.followup.send(embed=embed, ephemeral=True)

class AvailabilityView(discord.ui.View):
    def __init__(self, title: str, event_id: int, user_id: int, start_date: datetime, end_date: datetime, day_id: int, location: str):
        super().__init__(timeout=None)
        self.title = title
        self.event_id = event_id
        self.user_id = user_id
        self.start_date = start_date
        self.end_date = end_date
        self.day_id = day_id
        self.location = location

    async def cycle(self, interaction: discord.Interaction):
        if self.day_id == 6:
            next_day_id = 0
        else:
            next_day_id = self.day_id + 1
        next_day = self.start_date + timedelta(days=1)
        next_day_formatted = datetime.strftime(next_day, "%A %B %d, %Y")
        if next_day <= self.end_date:
            await interaction.followup.send(
                f"> Let’s set your availability for **{next_day_formatted}**",
                view=AvailabilityView(self.title, self.event_id, self.user_id, next_day, self.end_date, next_day_id, self.location)
            )
        else:
            await submit_availability(event_id=self.event_id, user_id=self.user_id)
            channel_message = await get_channel_message(self.event_id)
            logger.debug("submit — channel_id=%s message_id=%s", channel_message[0][0], channel_message[0][1])
            channel = interaction.client.get_channel(channel_message[0][0])
            message = await channel.fetch_message(channel_message[0][1])
            embed = message.embeds[0]
            if embed.fields[4].value not in ("-", "", None, "> Not specified"):
                updated_value = embed.fields[4].value + f"\n> <@{self.user_id}>"
            else:
                updated_value = f"> <@{self.user_id}>"
            embed.set_field_at(
                4,
                name="☑️ Submitted",
                value=updated_value,
                inline=False
            )

            await message.edit(embed=embed)
            await interaction.followup.send(
                "> Your availability is submitted! When everyone submits their selections, I'll post results in your channel!",
                ephemeral=True
            )

            # automatic send results
            count_submits = await get_count_submits(self.event_id)
            count_members = await get_count_members(self.event_id)
            threshold = 0.75 * int(count_members)
            min_people = math.floor(threshold)
            results = await find_overlaps(self.event_id, min_people)
            if count_submits == count_members:
                logger.debug(
                    "all submitted — top result date=%s start=%s end=%s",
                    results[0][5], results[0][1], results[0][2]
                )
                start = results[0][5] + timedelta(minutes=results[0][1])
                end = results[0][5] + timedelta(minutes=results[0][2])
                if results[0][3] == count_members:
                    joins = await get_joins(self.event_id)
                    names = []
                    for user_id in joins:
                        names.append(f"> <@{user_id}>")
                    embed = discord.Embed(
                        title=f"**Event**: {self.title}",
                        description="Good news! Everybody is free :)",
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="**Time**",
                        value=f"> From: {discord.utils.format_dt(start, 'F')}\n> To: {discord.utils.format_dt(end, 'F')}",
                        inline=False
                    )
                    embed.add_field(
                        name="**Participants**",
                        value="\n".join(names),
                        inline=False
                    )
                    view = ResultsView(self.title, start, end, self.location)
                    await channel.send(embed=embed,view=view)
                    #await message.delete()
                else:
                    try:
                        poll_obj = discord.Poll(
                            question="🤔 Results are in! Pick the best time",
                            duration=timedelta(hours=24)
                        )
                        shown = 0
                        for weekday, start, end, count, pref_count, sd in results:
                            start_formatted = sd.strftime("%a %m/%d/%y")
                            count_word = "person" if count == 1 else "people"
                            time_option = f"{start_formatted} · {minutes_to_label(start)}-{minutes_to_label(end)} · {count} {count_word} · {pref_count} pref."
                            poll_obj.add_answer(text=time_option)
                            shown += 1
                            if shown == 5:
                                break
                        await channel.send(poll=poll_obj)
                    except discord.Forbidden:
                        await channel.send("> I do not have the 'Create Polls' permission in this channel.")
                    except Exception as e:
                        await channel.send(f"> An error occurred: {e}")

    @discord.ui.button(label="✅ Available", style=discord.ButtonStyle.primary, row=0)
    async def fill_times_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            AvailabilityModal(
                title=self.title,
                event_id=self.event_id,
                user_id=self.user_id,
                start_date=self.start_date,
                end_date=self.end_date,
                day_id=self.day_id,
                is_preferred=False,
                location=self.location
            )
        )

    @discord.ui.button(label="⭐ Preferred", style=discord.ButtonStyle.success, row=0)
    async def preferred(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            AvailabilityModal(
                title=self.title,
                event_id=self.event_id,
                user_id=self.user_id,
                start_date=self.start_date,
                end_date=self.end_date,
                day_id=self.day_id,
                is_preferred=True,
                location=self.location
            )
        )

    @discord.ui.button(label="🚫 Unavailable", style=discord.ButtonStyle.secondary, row=0)
    async def unavailable(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
        try:
            await interaction.message.delete()
        except discord.NotFound:
            pass
        await self.cycle(interaction)

    @discord.ui.button(label="♾️All Day", style=discord.ButtonStyle.secondary, row=0)
    async def always(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
        await save_availability(
            event_id=self.event_id,
            user_id=self.user_id,
            weekday=self.day_id+1,
            start_date=self.start_date,
            raw_input="12am",
            is_preferred=True
        )
        try:
            await interaction.message.delete()
        except discord.NotFound:
            pass
        await self.cycle(interaction)

class AvailabilityModal(discord.ui.Modal):
    def __init__(self, title: str, event_id: int, user_id: int, start_date: datetime, end_date: datetime, day_id: int, is_preferred: bool, location: str):
        super().__init__(title=f"{DAY_NAMES[day_id]} Availability")
        self.title = title
        self.event_id = event_id
        self.user_id = user_id
        self.start_date = start_date
        self.end_date = end_date
        self.day_id = day_id
        self.is_preferred = is_preferred
        self.location = location

        self.times = discord.ui.TextInput(
            label="Enter your available times",
            placeholder="e.g. 7pm-10pm, 8am-12pm",
            required=True
        )
        self.add_item(self.times)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.response.is_done():
            return
        await interaction.response.defer()

        await save_availability(
            event_id=self.event_id,
            user_id=self.user_id,
            weekday=self.day_id+1,
            start_date=self.start_date,
            raw_input=self.times.value,
            is_preferred=self.is_preferred
        )
        try:
            await interaction.message.delete()
        except discord.NotFound:
            pass

        await AvailabilityView(self.title, self.event_id, self.user_id, self.start_date, self.end_date, self.day_id, self.location).cycle(interaction)

class ResultsView(discord.ui.View):
    def __init__(self, title: str, start: datetime, end: datetime, location: str):
        super().__init__(timeout=None)
        self.title = title
        self.start = start
        self.end = end
        self.location = location

    @discord.ui.button(label="Add event", style=discord.ButtonStyle.primary, row=0)
    async def event_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await interaction.guild.create_scheduled_event(
            name=f"{self.title}",
            start_time=self.start,
            end_time=self.end,
            privacy_level=discord.PrivacyLevel.guild_only,
            entity_type=discord.EntityType.external,
            location=self.location
        )
        button.disabled = True
        button.label = "Event added"
        button.style = discord.ButtonStyle.secondary
        await interaction.message.edit(view=self)
        await interaction.followup.send("> I added this event - check the events tab!", ephemeral=True)