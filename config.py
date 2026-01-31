import os

TOKEN = os.getenv("DISCORD_TOKEN")
MYSQL_PUBLIC_URL = os.getenv("MYSQL_PUBLIC_URL")
MYSQL_HOST = os.getenv("MYSQLHOST")
MYSQL_PORT = int(os.getenv("MYSQLPORT"))
MYSQL_USER = os.getenv("MYSQLUSER")
MYSQL_PASSWORD = os.getenv("MYSQLPASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
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