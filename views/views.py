import asyncio
import math
from datetime import timedelta, datetime
from math import floor

import discord
from discord.ext import commands
from db import add_join, count_joins, user_in_event, save_availability, find_overlaps, submit_availability, \
    get_count_submits, get_channel_id, get_count_members, get_joins, get_message_id, get_title
from time_parse import to_minutes, minutes_to_label, time_to_label
from config import DAY_NAMES

class rsvpView(discord.ui.View):
    def __init__(self, title, event_id, role: discord.Role):
        super().__init__(timeout=None)
        self.title = title
        self.event_id = event_id
        self.role = role

    @discord.ui.button(label="✅ RSVP", style=discord.ButtonStyle.success, row=0)
    async def rsvp_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user.id
        if user_in_event(self.event_id, interaction.user.id):
            await interaction.followup.send("> You already RSVP'd to this event")
        else:
            add_join(self.event_id, user)
            message_id = get_message_id(self.event_id)
            channel_id = get_channel_id(self.event_id)
            channel = interaction.client.get_channel(channel_id)
            message = await channel.fetch_message(message_id)
            embed = message.embeds[0]
            updated_value = f"{embed.fields[1].value}\n> <@{user}>" if embed.fields[1].value not in (None, "") else f"> <@{user}>"
            embed.set_field_at(
                1,
                name="\✅ **Accepted**",
                value=updated_value,
                inline=True
            )
            await message.edit(embed=embed)

    @discord.ui.button(label="❔ Maybe", style=discord.ButtonStyle.secondary, row=0)
    async def maybe_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user.id
        if user_in_event(self.event_id, interaction.user.id):
            await interaction.followup.send("> You already RSVP'd to this event")
        else:
            add_join(self.event_id, user)
            message_id = get_message_id(self.event_id)
            channel_id = get_channel_id(self.event_id)
            channel = interaction.client.get_channel(channel_id)
            message = await channel.fetch_message(message_id)
            embed = message.embeds[0]
            updated_value = f"{embed.fields[2].value}\n> <@{user}>" if embed.fields[2].value not in (None, "") else f"> <@{user}>"
            embed.set_field_at(
                2,
                name="\❔**Maybe**",
                value=updated_value,
                inline=True
            )
            await message.edit(embed=embed)

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger, row=0)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user.id
        if user_in_event(self.event_id, interaction.user.id):
            await interaction.followup.send("> You already RSVP'd to this event", ephemeral=True)
        else:
            add_join(self.event_id, user)
            message_id = get_message_id(self.event_id)
            channel_id = get_channel_id(self.event_id)
            channel = interaction.client.get_channel(channel_id)
            message = await channel.fetch_message(message_id)
            embed = message.embeds[0]
            updated_value = f"{embed.fields[3].value}\n> <@{user}>" if embed.fields[3].value not in (None, "") else f"> <@{user}>"
            embed.set_field_at(
                3,
                name="\❌ **Declined**",
                value=updated_value,
                inline=True
            )
            await message.edit(embed=embed)

class ScheduleView(discord.ui.View):
    def __init__(self, title, event_id, channel_id, role: discord.Role):
        super().__init__(timeout=None)
        self.title = title
        self.event_id = event_id
        self.channel_id = channel_id
        self.role = role

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success, row=0)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)  # no visible reply
        user = interaction.user
        #print(user.roles)
        if self.role in user.roles:
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
                        0,
                        name="🧙‍♂️ Joined",
                        value="\n".join(names) if names else "-",
                        inline=False
                    )
                    await interaction.message.edit(embed=embed, view=self)

                    dm = await user.create_dm()
                    await dm.send(
                        f"👋 Hi! You joined **{self.title}** event :)"
                    )

                    msg = await dm.send(
                        "📅 Let’s set your availability for **Monday**.",
                        view=AvailabilityView(
                            event_id=self.event_id,
                            user_id=user.id,
                            day_id=0
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
    def __init__(self, event_id, user_id, day_id):
        super().__init__(timeout=None)
        self.event_id = event_id
        self.user_id = user_id
        self.day_id = day_id

    async def cycle(self, interaction):
        next = self.day_id + 1
        if next < 7:
            await interaction.followup.send(
                f"📅 Let’s set your availability for **{DAY_NAMES[next]}**",
                view=AvailabilityView(self.event_id, self.user_id, next)
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
                1,
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
                if results[0][3] == count_members:
                    list_joins = get_joins(self.event_id)
                    user_ids = [join[0] for join in list_joins]
                    names = []

                    #event_start_time = time_to_label(results[0][0], results[0][1])
                    #event_end_time = time_to_label(results[0][0], results[0][2])
                    #formatted_start_time = discord.utils.format_dt(event_start_time)
                    #formatted_end_time = discord.utils.format_dt(event_end_time)

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
                        value=f"> {DAY_NAMES[results[0][0] - 1]}: {minutes_to_label(results[0][1])} - {minutes_to_label(results[0][2])}",
                        inline=False
                    )
                    embed.add_field(
                        name="**Participants**",
                        value="\n".join(names),
                        inline=False
                    )
                    await channel.send(embed=embed)
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
                                    time_option = f"{DAY_NAMES[weekday - 1]}: {minutes_to_label(start)}–{minutes_to_label(end)} | {count} {count_word}"
                                    poll_obj.add_answer(text=time_option)
                                    limit += 1
                            else:
                                break
                        await channel.send(poll=poll_obj)
                    except discord.Forbidden:
                        await channel.send("> I do not have the 'Create Polls' permission in this channel.")
                    except Exception as e:
                        await channel.send(f"> An error occurred: {e}")

                    # for weekday, start, end, count, pref_count in results:
                    #     if count >= min_people & limit < 5:
                    #         time_option = f"{DAY_NAMES[weekday - 1]}: {minutes_to_label(start)}–{minutes_to_label(end)} for {count} people and preferred for {pref_count} people."
                    #         limit += 1
                    #         lines.append(
                    #             f"{DAY_NAMES[weekday - 1]}: "
                    #             f"**{minutes_to_label(start)}–{minutes_to_label(end)}** "
                    #             f"for **{count}** people and preferred for **{pref_count}** people."
                    #         )
                    # await channel.send("\n".join(lines))

    @discord.ui.button(label="✅ Available", style=discord.ButtonStyle.primary, row=0)
    async def fill_times_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            AvailabilityModal(
                event_id=self.event_id,
                user_id=self.user_id,
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
            raw_input="12am",
            is_preferred=True
        )
        try:
            await interaction.message.delete()
        except discord.NotFound:
            pass
        await self.cycle(interaction)

class AvailabilityModal(discord.ui.Modal):
    def __init__(self, event_id, user_id, day_id, is_preferred):
        super().__init__(title=f"{DAY_NAMES[day_id]} Availability")
        self.event_id = event_id
        self.user_id = user_id
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
            raw_input=self.times.value,
            is_preferred=self.is_preferred
        )
        try:
            await interaction.message.delete()
        except discord.NotFound:
            pass

        await AvailabilityView(self.event_id, self.user_id, self.day_id).cycle(interaction)