import asyncio
import discord
from discord.ext import commands
from db import add_join, count_joins, user_in_event

class ScheduleView(discord.ui.View):
    def __init__(self, title, event_id):
        super().__init__() # Optional: set a timeout for the view
        self.title = title
        self.event_id = event_id

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
                    f"👋 Hi! You joined **{self.title}** event.\n📩 Here’s your private scheduler form."
                )
                # optional confirmation (ephemeral)
                await interaction.followup.send(
                    f"📩 I’ve sent you a DM for **{self.title}**.",
                    ephemeral=True
                )
                await asyncio.sleep(1800)
                await msg.delete()
            except discord.Forbidden:
                # User has DMs closed
                await interaction.followup.send(
                    "❌ I can’t DM you. Please enable DMs from server members.",
                    ephemeral=True
                )

    @discord.ui.button(label="Results", style=discord.ButtonStyle.danger, row=0)
    async def results_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        await interaction.response.send_message(
            f"📩 Here are the results for **{self.title}** event!",
            ephemeral=True
        )