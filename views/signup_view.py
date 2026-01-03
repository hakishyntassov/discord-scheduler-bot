# views/signup_view.py
import discord
from config import DAY_NAMES
from views.day_view import DayView

class SignupView(discord.ui.View):
    def __init__(
        self,
        channel_id: int | None = None,
        allowed_role_id: int | None = None,
        allowed_user_ids: list[int] | None = None,
    ):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.allowed_role_id = allowed_role_id
        self.allowed_user_ids = allowed_user_ids

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.channel_id and interaction.channel_id != self.channel_id:
            await interaction.response.send_message(
                "❌ This scheduler is restricted to its original channel.",
                ephemeral=True,
            )
            return False

        if self.allowed_user_ids and interaction.user.id not in self.allowed_user_ids:
            await interaction.response.send_message(
                "❌ You are not required to fill out this scheduler.",
                ephemeral=True,
            )
            return False

        if self.allowed_role_id:
            if not isinstance(interaction.user, discord.Member):
                return False
            if self.allowed_role_id not in [r.id for r in interaction.user.roles]:
                await interaction.response.send_message(
                    "❌ You do not have the required role.",
                    ephemeral=True,
                )
                return False

        return True

    @discord.ui.button(
        label="Sign Up",
        style=discord.ButtonStyle.success,
        custom_id="schedule:signup",
    )
    async def signup(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.edit_message(
            content=f"### {DAY_NAMES[0]}\nSet your availability:",
            view=DayView(
                user_id=interaction.user.id,
                day_index=0,
                channel_id=self.channel_id,
                allowed_role_id=self.allowed_role_id,
                allowed_user_ids=self.allowed_user_ids,
            ),
        )
