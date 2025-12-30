# config.py
import os

TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = os.getenv("DB_PATH", "scheduler.db")

SERVER_TZ_NAME = os.getenv("SERVER_TZ_NAME", "America/New_York")
SCHEDULE_EXPIRE_HOURS = int(os.getenv("SCHEDULE_EXPIRE_HOURS", "24"))
DEFAULT_DURATION_MINUTES = int(os.getenv("DEFAULT_DURATION_MINUTES", "240"))
TOP_RESULTS = int(os.getenv("TOP_RESULTS", "10"))