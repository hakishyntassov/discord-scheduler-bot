import discord

class ScheduleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # persistent view

    # button decorator (defines style)
    @discord.ui.button(
        label="Sign Up",
        style=discord.ButtonStyle.success,
        custom_id="schedule:signup"
    )
    async def signup(self,
                     button: discord.ui.Button,
                     interaction: discord.Interaction):
        await interaction.response.send_messsage(
            "You joined the schedule!",
            ephemeral=True
        )