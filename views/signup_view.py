import discord
from config import DAY_NAMES
from views.day_view import DayView

class SignupView(discord.ui.View):
    def __init__(self, channel_id: int | None = None):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.channel_id and interaction.channel_id != self.channel_id:
            await interaction.response.send_message(
                "❌ This scheduler can only be used in its original channel.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(
        label="Sign Up",
        style=discord.ButtonStyle.success,
        custom_id="schedule:signup"
    )
    async def signup(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content=f"### {DAY_NAMES[0]}\nSet your availability:",
            view=DayView(
                user_id=interaction.user.id,
                day_index=0,
                channel_id=self.channel_id
            )
        )