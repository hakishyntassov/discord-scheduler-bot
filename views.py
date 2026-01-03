# views.py
import discord
from db import toggle_preferred

class PreferredDayView(discord.ui.View):
    def __init__(self, day: str):
        super().__init__(timeout=None)
        self.day = day

    @discord.ui.button(
        label="⭐ Preferred",
        style=discord.ButtonStyle.secondary,
        custom_id="preferred_toggle"  # fine for non-persistent; if you persist, include day in id
    )
    async def preferred(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_val = toggle_preferred(interaction.guild.id, interaction.user.id, self.day)
        state = "ON" if new_val == 1 else "OFF"
        await interaction.response.send_message(
            f"⭐ Preferred for **{self.day}** is now **{state}**.",
            ephemeral=True
        )
