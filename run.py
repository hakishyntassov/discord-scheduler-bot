# # main.py
# import discord
# from discord.ext import commands
#
# from config import TOKEN
# import scheduler.db as db
# from scheduler.views import SessionView
#
# class Client(commands.Bot):
#     def __init__(self):
#         intents = discord.Intents.default()
#         intents.message_content = True  # only needed if you still want "hello" message triggers
#         super().__init__(command_prefix="!", intents=intents)
#
#     async def setup_hook(self):
#         # DB
#         await db.init_db()
#
#         # Persistent buttons survive restarts (custom_id-based)
#         self.add_view(SessionView())
#
#         # Load scheduling cog
#         await self.load_extension("cogs.scheduling")
#
#         # Sync slash commands
#         await self.tree.sync()
#
#     async def on_ready(self):
#         print(f"Logged in as {self.user} (id={self.user.id})")
#
# client = Client()
#
# if TOKEN == "TOKEN_HERE" or not TOKEN:
#     raise RuntimeError("Set DISCORD_TOKEN env var or put your token in config.py")
#
# client.run(TOKEN)

import time

print("🚀 Railway started successfully")

while True:
    time.sleep(10)