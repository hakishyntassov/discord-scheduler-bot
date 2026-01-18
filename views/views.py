import asyncio
import discord
from discord.ext import commands
from db import add_join, count_joins, user_in_event, save_availability, find_overlaps, submit_availability, count_members, count_submits, get_channel_id
from time_parse import to_minutes, minutes_to_label
from config import DAY_NAMES

class ScheduleView(discord.ui.View):
    def __init__(self, title, event_id, channel_id):
        super().__init__(timeout=None)
        self.title = title
        self.event_id = event_id
        self.channel_id = channel_id

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success, row=0)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)  # no visible reply
        user = interaction.user
        # prevent double-join
        if user_in_event(self.event_id, user.id):
            await interaction.followup.send(
                "You already joined.",
                ephemeral=True
            )
            return
        else:
            try:
                add_join(self.event_id, user.id)
                count = count_joins(self.event_id)
                embed = interaction.message.embeds[0]
                embed.set_field_at(
                    0,
                    name="👥 Joined",
                    value=count,
                    inline=False
                )
                await interaction.message.edit(embed=embed, view=self)

                dm = await user.create_dm()
                msg = await dm.send(
                    f"👋 Hi! You joined **{self.title}** event.\n"
                    f"📌 Select appropriate button if you're available that day, if you prefer that day, or if you're unavailable.\n\n"
                    "📅 Let’s set your availability for **Monday**.\n\n",
                    view=AvailabilityView(
                        event_id=self.event_id,
                        user_id=user.id,
                        day_id=0
                    )
                )
                # optional confirmation (ephemeral)
                await interaction.followup.send(
                    f"📩 I’ve sent you a DM to submit your availability for **{self.title}**.",
                    ephemeral=True
                )

            except discord.Forbidden:
                # User has DMs closed
                await interaction.followup.send(
                    "❌ I can’t DM you. Please enable DMs from server members.",
                    ephemeral=True
                )

    @discord.ui.button(label="Results", style=discord.ButtonStyle.danger, row=0)
    async def results_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        await interaction.response.defer(ephemeral=True)

        results = find_overlaps(self.event_id, 2)

        if not results:
            await interaction.followup.send(
                "No overlapping availability found.",
                ephemeral=True
            )
            return
        else:
            lines = ["📊 **Best available times**"]

            for weekday, start, end, count, pref_count in results:
                lines.append(
                    f"{DAY_NAMES[weekday - 1]}: "
                    f"**{minutes_to_label(start)}–{minutes_to_label(end)}** "
                    f"(for **{count}** people, preferred for **{pref_count}** people).)"
                )

            await interaction.followup.send("\n".join(lines))

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
            await interaction.followup.send(
                "✅ Your availability is submitted! When everyone submits their selections, I'll post results in your channel!",
                ephemeral=True
            )
            count1 = count_submits(self.event_id)
            count2 = count_members(self.event_id)

            if count1 == count2:
                channel_id = get_channel_id(self.event_id)
                channel = interaction.client.get_channel(channel_id)
                results = find_overlaps(self.event_id, count2)
                lines = ["📊 **Best available times**"]
                for weekday, start, end, count, pref_count in results:
                    lines.append(
                        f"{DAY_NAMES[weekday - 1]}: "
                        f"**{minutes_to_label(start)}–{minutes_to_label(end)}** "
                        f"for **{count}** people and preferred for **{pref_count}** people"
                    )
                await channel.send("\n".join(lines))

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
        save_availability(
            event_id=self.event_id,
            user_id=self.user_id,
            weekday=self.day_id + 1,
            raw_input=self.times.value,
            is_preferred=self.is_preferred
        )

        await interaction.response.defer()
        await AvailabilityView(self.event_id, self.user_id, self.day_id).cycle(interaction)