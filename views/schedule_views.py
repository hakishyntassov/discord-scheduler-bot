import discord
from views.day_views import DayView, DAY_NAMES

class SignupView(discord.ui.View):
    def __init__(self, allowed_role_id: int | None):
        super().__init__(timeout=None)  # persistent view
        self.allowed_role_id = allowed_role_id

    # button decorator (defines style)
    @discord.ui.button(
        label="Sign Up",
        style=discord.ButtonStyle.primary,
        custom_id="schedule:signup"
    )
    async def signup(self,
                     interaction: discord.Interaction,
                     button: discord.ui.Button
                     ):
        await interaction.response.edit_message(
            content=f"### {DAY_NAMES[0]}\nSet your availability:",
            view=DayView(interaction.user.id, 0)
        )