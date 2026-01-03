# views/day_view.py
import discord

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

class DayView(discord.ui.View):
    def __init__(self, user_id: int, day_index: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.day_index = day_index

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.allowed_role_id is None:
            return True  # no restriction

        if not isinstance(interaction.user, discord.Member):
            return False

        if self.allowed_role_id not in [r.id for r in interaction.user.roles]:
            await interaction.response.send_message(
                "❌ You don’t have permission to fill out this scheduler.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Unavailable", style=discord.ButtonStyle.danger, row=0)
    async def unavailable(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"{DAY_NAMES[self.day_index]} marked unavailable.",
            ephemeral=True
        )
        await self._go_next(interaction)

    @discord.ui.button(label="⭐", style=discord.ButtonStyle.secondary, row=1)
    async def star1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"{DAY_NAMES[self.day_index]}: low priority",
            ephemeral=True
        )
        await self._go_next(interaction)

    @discord.ui.button(label="⭐⭐", style=discord.ButtonStyle.secondary, row=1)
    async def star2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"{DAY_NAMES[self.day_index]}: medium priority",
            ephemeral=True
        )
        await self._go_next(interaction)

    @discord.ui.button(label="⭐⭐⭐", style=discord.ButtonStyle.secondary, row=1)
    async def star3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"{DAY_NAMES[self.day_index]}: high priority",
            ephemeral=True
        )
        await self._go_next(interaction)

    async def _go_next(self, interaction: discord.Interaction):
        if self.day_index < 6:
            next_view = DayView(self.user_id, self.day_index + 1)
            await interaction.message.edit(
                content=f"### {DAY_NAMES[self.day_index + 1]}\nSet your availability:",
                view=next_view
            )
        else:
            await interaction.message.edit(
                content="✅ All days completed!",
                view=None
            )
