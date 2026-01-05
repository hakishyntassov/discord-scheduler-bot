import discord
from discord.ext import commands

class JoinButton(discord.ui.View):
    def __init__(self, title):
        super().__init__(timeout=180) # Optional: set a timeout for the view
        self.title = title

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success)
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"You joined the {self.title} event!", ephemeral=True)