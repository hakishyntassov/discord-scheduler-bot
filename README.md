# Discord Scheduler Bot

A Discord bot that helps you and your friends coordinate schedules and organize events by finding the best time that works for everyone.

## Features

### 📅 Schedule Command (`/schedule`)
- **Collaborative scheduling**: Find the optimal time that works for all participants
- **Flexible time ranges**: Set custom start and end dates for availability collection
- **Smart participant selection**: Target specific roles, users, or everyone in the channel
- **DM-based availability**: Participants submit their availability privately through DMs
- **Automatic overlap detection**: The bot finds the best time slots that work for everyone
- **Real-time status tracking**: See who has joined and submitted their availability

### 🎯 RSVP Command (`/rsvp`)
- **Quick event creation**: Create events with specific date and time
- **RSVP responses**: Participants can respond with Accept, Maybe, or Decline
- **Event details**: Add descriptions, duration, and location information
- **Live attendance tracking**: Real-time updates showing response counts
- **Flexible invitations**: Invite specific roles, users, or channel members

### Additional Features
- **Natural language time parsing**: Use natural language like "tomorrow at 3pm" or "next Friday"
- **Duration support**: Specify event durations in various formats
- **Rate limiting**: Built-in cooldowns to prevent spam (30 seconds per user)
- **Database persistence**: All events and responses are stored securely
- **Interactive UI**: Discord buttons and embeds for seamless interaction

## Prerequisites

- Python 3.8 or higher
- Discord Bot Token ([Create one here](https://discord.com/developers/applications))
- Database (PostgreSQL recommended for production, SQLite for development)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/discord-scheduler-bot.git
   cd discord-scheduler-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   Create a `.env` file in the project root:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   DATABASE_PUBLIC_URL=your_database_url_here  # Optional, defaults to SQLite
   ```

4. **Invite the bot to your server**

   Generate an invite link with the following permissions:
   - Send Messages
   - Embed Links
   - Read Message History
   - View Channels
   - Use Slash Commands
   - Mention Everyone (for participant notifications)

5. **Run the bot**
   ```bash
   python bot.py
   ```

## Usage

### Creating a Schedule Event

```
/schedule title:"Team Gaming Session" start:"Monday" end:"Sunday" role:@gamers
```

This creates a week-long scheduling poll where members with the @gamers role can submit their availability.

**Parameters:**
- `title` (required): Name of the event
- `start` (required): Start date for availability collection
- `end` (optional): End date (defaults to 6 days after start)
- `role` (optional): Target specific role
- `users` (optional): Target specific users with mentions
- `description` (optional): Event description
- `location` (optional): Event location

### Creating an RSVP Event

```
/rsvp title:"Movie Night" time:"Friday 8pm" duration:"3 hours" location:"Discord Theater"
```

This creates an RSVP event for a specific date and time.

**Parameters:**
- `title` (required): Name of the event
- `time` (required): Event date and time
- `description` (optional): Event description
- `duration` (optional): Event duration
- `location` (optional): Event location
- `role` (optional): Target specific role
- `users` (optional): Target specific users with mentions

## Project Structure

```
discord-scheduler-bot/
│
├── bot.py              # Main bot file with command handlers
├── config.py           # Configuration and environment variables
├── database.py         # Database operations and models
├── time_parse.py       # Natural language time parsing utilities
├── requirements.txt    # Python dependencies
└── views/
    └── views.py        # Discord UI components (buttons, embeds)
```

## Technologies Used

- **discord.py**: Discord API wrapper for Python
- **asyncpg/aiosqlite**: Async database drivers
- **dateparser**: Natural language date/time parsing
- **durations-nlp**: Natural language duration parsing
- **python-dotenv**: Environment variable management

## Database

The bot supports multiple database backends:
- **SQLite**: Default for development (automatic)
- **PostgreSQL**: Recommended for production (via asyncpg)
- **MySQL**: Alternative option (via mysql-connector-python)

Database tables are automatically initialized on first run.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.

## Acknowledgments

- Discord.py community for the excellent library and documentation
- Contributors and users who help improve the bot