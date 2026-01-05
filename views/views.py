import asyncio
import discord
from discord.ext import commands
joined_users: set[int] = set()

class JoinButton(discord.ui.View):
    def __init__(self, title):
        super().__init__() # Optional: set a timeout for the view
        self.title = title

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success, row=0)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        # prevent double-join
        if user.id in joined_users:
            await interaction.response.send_message(
                "You already joined.",
                ephemeral=True
            )
            return

        joined_users.add(interaction.user.id)

        # rebuild embed
        embed = interaction.message.embeds[0]
        embed.set_field_at(
            0,
            name="👥 Joined",
            value=str(len(joined_users)),
            inline=False
        )

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.defer()  # no visible reply

        try:
            await interaction.response.send_message(
                f"📩 You joined the **{self.title}** event!\n📩 I’ve sent you a DM!",
                ephemeral=True
            )
            dm = await user.create_dm()
            msg = await dm.send(
                f"👋 Hi! You joined **{self.title}** event.\n📩 Here’s your private scheduler form."
            )
            await asyncio.sleep(1800)
            await msg.delete()
        except discord.Forbidden:
            # User has DMs closed
            await interaction.response.send_message(
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