import discord
from discord.ext import commands

class JoinButton(discord.ui.View):
    def __init__(self, title):
        super().__init__(timeout=180) # Optional: set a timeout for the view
        self.title = title

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success)
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        try:
            dm = await user.create_dm()
            await dm.send(
                f"👋 Hi! You joined **{self.title}** event. Here’s your private scheduler form."
            )
            await interaction.response.send_message(
                f"📩 You joined the **{self.title}** event!\n📩 I’ve sent you a DM!",
                ephemeral=True
            )
        except discord.Forbidden:
            # User has DMs closed
            await interaction.response.send_message(
                "❌ I can’t DM you. Please enable DMs from server members.",
                ephemeral=True
            )