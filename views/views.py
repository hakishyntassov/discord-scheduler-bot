import asyncio
import math
from datetime import timedelta, datetime, timezone
from math import floor

import discord
from discord.ext import commands
from db import add_join, count_joins, user_in_event, save_availability, find_overlaps, submit_availability, \
    get_count_submits, get_channel_id, get_count_members, get_joins, get_message_id, get_title, add_rsvp, user_in_rsvp, \
    change_rsvp, get_rsvp, count_status, get_start_timep, get_end_timep
from time_parse import to_minutes, minutes_to_label, time_to_label, parse_time_wd, get_next_day
from config import DAY_NAMES

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
            await self.remove_add_user(interaction, 3)
        else:
            await interaction.followup.send("> You can't rsvp to this event", ephemeral=True)

    @discord.ui.button(label="❔", style=discord.ButtonStyle.primary, row=0)
    async def maybe_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if interaction.user in self.participants:
            await self.remove_add_user(interaction, 4)
        else:
            await interaction.followup.send("> You can't rsvp to this event", ephemeral=True)

    @discord.ui.button(label="❌", style=discord.ButtonStyle.primary, row=0)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if interaction.user in self.participants:
            await self.remove_add_user(interaction, 5)
        else:
            await interaction.followup.send("> You can't rsvp to this event", ephemeral=True)

    # @discord.ui.button(label="Edit", style=discord.ButtonStyle.primary, row=0)
    # async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     await interaction.response.defer(ephemeral=True)


    async def remove_add_user(self, interaction, new_status: int):
        user = interaction.user.id
        members = get_count_members(self.event_id)

        channel = interaction.client.get_channel(get_channel_id(self.event_id))
        message = await channel.fetch_message(get_message_id(self.event_id))
        embed = message.embeds[0]

        if user_in_rsvp(self.event_id, user):
            old_status = int(get_rsvp(self.event_id, user))

            if old_status == new_status:
                await interaction.followup.send(
                    "> You already RSVP'd to this event",
                    ephemeral=True
                )
                return

            change_rsvp(self.event_id, user, new_status)

            field = embed.fields[old_status]
            lines = [l for l in field.value.splitlines() if l.strip() != f"> <@{user}>"]
            old_count = count_status(self.event_id, old_status)

            embed.set_field_at(
                old_status,
                name=f"{field.name.split('(')[0]}({old_count}/{members})",
                value="\n".join(lines) if lines else "> -",
                inline=True
            )

        else:
            add_rsvp(self.event_id, user, new_status)

        field = embed.fields[new_status]
        lines = [] if field.value == "> -" else field.value.splitlines()
        lines.append(f"> <@{user}>")

        new_count = count_status(self.event_id, new_status)
        embed.set_field_at(
            new_status,
            name=f"{field.name.split('(')[0]}({new_count}/{members})",
            value="\n".join(lines),
            inline=True
        )

        await message.edit(embed=embed)

class ScheduleView(discord.ui.View):
    def __init__(self, title, event_id, channel_id, participants):
        super().__init__(timeout=None)
        self.title = title
        self.event_id = event_id
        self.channel_id = channel_id
        self.participants = participants

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success, row=0)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)  # no visible reply
        user = interaction.user
        #print(user.roles)
        if user in self.participants:
        #if self.role in user.roles:
            # prevent double-join
            if user_in_event(self.event_id, user.id):
                await interaction.followup.send(
                    "> You already joined.",
                    ephemeral=True
                )
                return
            else:
                try:
                    guild = interaction.guild
                    add_join(self.event_id, user.id)
                    count = count_joins(self.event_id)
                    list_joins = get_joins(self.event_id)
                    user_ids = [join[0] for join in list_joins]
                    names = []
                    for user_id in user_ids:
                        names.append(f"> <@{user_id}>")
                    embed = interaction.message.embeds[0]
                    embed.set_field_at(
                        3,
                        name="🧙‍♂️ Joined",
                        value="\n".join(names) if names else "-",
                        inline=False
                    )
                    await interaction.message.edit(embed=embed, view=self)

                    dm = await user.create_dm()
                    msg = await dm.send(
                        f"👋 Hi! You joined **{self.title}** event :)"
                    )

                    start_date = get_start_timep(self.event_id)
                    end_date = get_end_timep(self.event_id)
                    start_date_strp = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
                    end_date_strp = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
                    start_dt_formatted = start_date_strp.strftime("%A %B %d, %Y")
                    await dm.send(
                        f"📅 Let’s set your availability for **{start_dt_formatted}**.",
                        view=AvailabilityView(
                            event_id=self.event_id,
                            user_id=user.id,
                            date1=start_date_strp,
                            end_date=end_date_strp,
                            day_id=start_date_strp.weekday()
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

        results = find_overlaps(self.event_id, 1)

        if not results:
            await interaction.followup.send(
                "> No overlapping availability found.",
                ephemeral=True
            )
            return
        else:
            lines = ["📊 **Best available times**"]
            count_members = get_count_members(self.event_id)
            threshold = 0.75 * int(count_members)
            min_people = round(threshold)
            print(f"Minimum {min_people} people")
            limit = 0
            for weekday, start, end, count, pref_count in results:
                if limit < 5:
                    if count >= min_people & limit < 5:
                        count_word = "people" if count != 1 else "person"
                        pref_word = "people" if pref_count != 1 else "person"
                        lines.append(
                            f"> {DAY_NAMES[weekday - 1]}: **{minutes_to_label(start)}–{minutes_to_label(end)}** for **{count}** {count_word} and preferred for **{pref_count}** {pref_word}."
                        )
                    limit += 1
                else:
                    break

            await interaction.followup.send("\n".join(lines), ephemeral=True)

        #await interaction.followup.send("Results posted!", ephemeral=True)

class AvailabilityView(discord.ui.View):
    def __init__(self, event_id, user_id, date1, end_date, day_id):
        super().__init__(timeout=None)
        self.event_id = event_id
        self.user_id = user_id
        self.date1 = date1
        self.end_date = end_date
        self.day_id = day_id

    async def cycle(self, interaction: discord.Interaction):
        if self.day_id == 6:
            next_day_id = 0
        else:
            next_day_id = self.day_id + 1
        next_day = get_next_day(self.date1)
        next_day_formatted = datetime.strftime(next_day, "%A %B %d, %Y")
        if next_day <= self.end_date:
            await interaction.followup.send(
                f"📅 Let’s set your availability for **{next_day_formatted}**",
                view=AvailabilityView(self.event_id, self.user_id, next_day, self.end_date, next_day_id)
            )
        else:
            submit_availability(event_id=self.event_id, user_id=self.user_id)

            channel_id = get_channel_id(self.event_id)
            message_id = get_message_id(self.event_id)
            print(f"Channel: {channel_id}, Message: {message_id}")
            channel = interaction.client.get_channel(channel_id)
            message = await channel.fetch_message(message_id)
            embed = message.embeds[0]
            if embed.fields[1].value not in ("-", "", None):
                updated_value = embed.fields[1].value + f"\n> <@{self.user_id}>"
            else:
                updated_value = f"> <@{self.user_id}>"
            print(embed.fields[1].value)
            print(updated_value)
            embed.set_field_at(
                4,
                name="☑️ Submitted",
                value=updated_value,
                inline=False
            )

            await message.edit(embed=embed)
            await interaction.followup.send(
                "✅ Your availability is submitted! When everyone submits their selections, I'll post results in your channel!",
                ephemeral=True
            )

            # automatic send results
            title = get_title(self.event_id)
            count_submits = get_count_submits(self.event_id)
            count_members = get_count_members(self.event_id)
            threshold = 0.75 * int(count_members)
            min_people = math.floor(threshold)
            print(f"Minimum {min_people}")
            results = find_overlaps(self.event_id, min_people)
            if count_submits == count_members:
                print(f"Count: {results[0][3]}")
                start_dt = parse_time_wd(results[0][0], results[0][1], user_tz="America/New_York")
                end_dt = parse_time_wd(results[0][0], results[0][2], user_tz="America/New_York")
                if results[0][3] == count_members:
                    list_joins = get_joins(self.event_id)
                    user_ids = [join[0] for join in list_joins]
                    names = []
                    for user_id in user_ids:
                        names.append(f"> <@{user_id}>")
                    embed = discord.Embed(
                        title=f"**Event**: {title}",
                        description="Good news! Everybody is free :)",
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="**Time**",
                        #value=f"{formatted_start_time} - {formatted_end_time}",
                        #value=f"> {DAY_NAMES[results[0][0] - 1]}: {minutes_to_label(results[0][1])} - {minutes_to_label(results[0][2])}",
                        value=f"> {discord.utils.format_dt(start_dt, style='F')} - {discord.utils.format_dt(end_dt, style='F')}",
                        inline=False
                    )
                    embed.add_field(
                        name="**Participants**",
                        value="\n".join(names),
                        inline=False
                    )
                    view = resultsView(title, results)
                    await channel.send(embed=embed,view=view)
                    await message.delete()
                else:
                    try:
                        poll_obj = discord.Poll(
                            question="🤔 Results are in! Pick the best time",
                            duration=timedelta(hours=24)
                        )
                        limit = 0
                        for weekday, start, end, count, pref_count in results:
                            if limit < 5:
                                if count >= min_people:
                                    count_word = "people" if count != 1 else "person"
                                    time_option = f"{discord.utils.format_dt(start_dt, style='F')} - {discord.utils.format_dt(end_dt, style='F')} | {count} {count_word}"
                                    poll_obj.add_answer(text=time_option)
                                    limit += 1
                            else:
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
                event_id=self.event_id,
                user_id=self.user_id,
                date1=self.date1,
                end_date=self.end_date,
                day_id=self.day_id,
                is_preferred=False
            )
        )

    @discord.ui.button(label="⭐ Preferred", style=discord.ButtonStyle.success, row=0)
    async def preferred(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            AvailabilityModal(
                event_id=self.event_id,
                user_id=self.user_id,
                date1=self.date1,
                end_date=self.end_date,
                day_id=self.day_id,
                is_preferred=True
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
        save_availability(
            event_id=self.event_id,
            user_id=self.user_id,
            weekday=self.day_id + 1,
            date1=self.date1,
            raw_input="12am",
            is_preferred=True
        )
        try:
            await interaction.message.delete()
        except discord.NotFound:
            pass
        await self.cycle(interaction)

class AvailabilityModal(discord.ui.Modal):
    def __init__(self, event_id, user_id, date1, end_date, day_id, is_preferred):
        super().__init__(title=f"{DAY_NAMES[day_id]} Availability")
        self.event_id = event_id
        self.user_id = user_id
        self.date1 = date1
        self.end_date = end_date
        self.day_id = day_id
        self.is_preferred = is_preferred

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

        save_availability(
            event_id=self.event_id,
            user_id=self.user_id,
            weekday=self.day_id + 1,
            date1=self.date1,
            raw_input=self.times.value,
            is_preferred=self.is_preferred
        )
        try:
            await interaction.message.delete()
        except discord.NotFound:
            pass

        await AvailabilityView(self.event_id, self.user_id, self.date1, self.end_date, self.day_id).cycle(interaction)

class resultsView(discord.ui.View):
    def __init__(self, title: str, results):
        super().__init__(timeout=None)
        self.title = title
        self.results = results

    @discord.ui.button(label="Add event", style=discord.ButtonStyle.primary, row=0)
    async def event_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        start_dt = parse_time_wd(self.results[0][0], self.results[0][1], user_tz="America/New_York")
        end_dt = parse_time_wd(self.results[0][0], self.results[0][2], user_tz="America/New_York")
        await interaction.guild.create_scheduled_event(
            name=f"{self.title}",
            start_time=start_dt,
            end_time=end_dt,
            privacy_level=discord.PrivacyLevel.guild_only,
            entity_type=discord.EntityType.external,
            location="location"
        )
        await interaction.followup.send("> I added this event - check the events tab!")