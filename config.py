import os

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_PUBLIC_URL = os.getenv("DATABASE_PUBLIC_URL")

DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

# /schedule picker settings
EVENT_TZ = "America/New_York"   # the hour buttons are shown in this time zone
DEFAULT_HOURS = "10am-12am"     # used when /schedule doesn't get an hours option
MAX_SLOTS_PER_DAY = 20          # 4 rows of 5 buttons, the 5th row is navigation
MAX_DAYS = 31
