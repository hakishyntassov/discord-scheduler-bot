import os
import discord
from discord.ext import commands
from discord import app_commands

class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.content.startswith('hello'):
            await message.channel.send('Hi there!')

intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix='/', intents=intents)

@client.tree.command(name="Hello", description="Say hi!")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("Hi there!")

client.run('MTQ1NTM3ODMzMzg0MjgwNDkwNQ.GCYITz.GUOKZS0A-chZuNcgADrw83a-57SEbAMxx6wJV0')