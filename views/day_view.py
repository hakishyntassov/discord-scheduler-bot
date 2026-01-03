# views/day_view.py
import discord
from config import DAY_NAMES

class DayView(discord.ui.View):
    def __init__(
        self,
        user_id: int,
        day_index: int,
        channel_id: int | None = None,
        allowed_role_id: int | None = None,
        allowed_user_ids: list[int] | None = None,
    ):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.day_index = day_index
        self.channel_id = channel_id
        self.allowed_role_id = allowed_role_id
        self.allowed_user_ids = allowed_user_ids


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This scheduler is not for you.",
                ephemeral=True,
            )
            return False

        if self.channel_id and interaction.channel_id != self.channel_id:
            await interaction.response.send_message(
                "❌ Wrong channel.",
                ephemeral=True,
            )
            return False

        return True

    async def _advance(self, interaction: discord.Interaction):
        if self.day_index < 6:
            await interaction.message.edit(
                content=f"### {DAY_NAMES[self.day_index + 1]}\nSet your availability:",
                view=DayView(
                    user_id=self.user_id,
                    day_index=self.day_index + 1,
                    channel_id=self.channel_id,
                    allowed_role_id=self.allowed_role_id,
                    allowed_user_ids=self.allowed_user_ids,
                ),
            )
        else:
            await interaction.message.edit(
                content="✅ All days completed!",
                view=None,
            )

    @discord.ui.button(label="Unavailable", style=discord.ButtonStyle.danger, row=0)
    async def unavailable(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"{DAY_NAMES[self.day_index]} marked unavailable.",
            ephemeral=True,
        )
        await self._advance(interaction)

    @discord.ui.button(label="⭐", style=discord.ButtonStyle.secondary, row=1)
    async def star1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Low priority", ephemeral=True)
        await self._advance(interaction)

    @discord.ui.button(label="⭐⭐", style=discord.ButtonStyle.secondary, row=1)
    async def star2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Medium priority", ephemeral=True)
        await self._advance(interaction)

    @discord.ui.button(label="⭐⭐⭐", style=discord.ButtonStyle.secondary, row=1)
    async def star3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("High priority", ephemeral=True)
        await self._advance(interaction)
