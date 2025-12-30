# Medication Bot 💊

A Telegram bot for managing medication schedules with intelligent natural language processing powered by Groq LLM. The bot helps users track their medication intake, sends timely reminders, and provides a conversational interface for schedule management.

## Features

- 🤖 **Natural Language Processing**: Interact with the bot using natural Russian language commands
- ⏰ **Smart Reminders**: Automatic medication reminders at scheduled times
- 📅 **Flexible Scheduling**: Support for multiple medications with different times and dosages
- 🌍 **Timezone Support**: Configurable timezone for accurate reminder delivery
- 🔔 **Interactive Notifications**: One-click confirmation when medication is taken
- 📊 **Statistics**: Track bot usage and medication adherence
- 💾 **Persistent Storage**: JSON-based user data storage with atomic writes
- 🔄 **Graceful Shutdown**: Proper cleanup and signal handling

## Technology Stack

- **Python 3.11+**: Modern Python with type hints
- **aiogram 3.15**: Telegram Bot API framework
- **Groq API**: LLM for natural language understanding
- **httpx**: Async HTTP client for API requests
- **loguru**: Advanced logging with structured output
- **aiofiles**: Async file I/O operations
- **python-dotenv**: Environment configuration management

## Prerequisites

- Python 3.11 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Groq API Key (from [Groq Console](https://console.groq.com))
- Basic understanding of Telegram bots

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd medical_bot
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

**Important**: Always activate the virtual environment before running the bot or tests:
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GROQ_API_KEY=your_groq_api_key_here
```

See [Configuration](#configuration) section for all available options.

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token from BotFather | - | ✅ |
| `GROQ_API_KEY` | Groq API key for LLM processing | - | ✅ |
| `GROQ_MODEL` | Groq model to use | `openai/gpt-oss-120b` | ❌ |
| `GROQ_TIMEOUT` | API request timeout in seconds | `30` | ❌ |
| `GROQ_MAX_RETRIES` | Maximum retry attempts for API calls | `3` | ❌ |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` | ❌ |
| `DATA_DIR` | Directory for user data storage | `data/users` | ❌ |
| `SCHEDULER_INTERVAL_SECONDS` | Reminder check interval | `60` | ❌ |
| `REMINDER_REPEAT_INTERVAL_HOURS` | Repeat reminder interval | `1` | ❌ |
| `DEFAULT_TIMEZONE_OFFSET` | Default timezone for new users | `+03:00` | ❌ |

### Data Storage

User data is stored in JSON files at `data/users/{user_id}.json`. Each file contains:
- User timezone settings
- Medication list with schedules
- Last taken timestamps
- Reminder message IDs

## Usage

### Starting the Bot

**Important**: Always activate the virtual environment first:

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python -m src.main
```

The bot will:
1. Initialize all services
2. Start the reminder scheduler
3. Begin polling for Telegram updates
4. Log startup information

### Stopping the Bot

Press `Ctrl+C` or send `SIGTERM` signal. The bot will:
1. Stop accepting new messages
2. Complete ongoing operations
3. Stop the scheduler
4. Close all connections gracefully

## Bot Commands

### Natural Language Commands

The bot understands natural Russian language. Here are example commands:

#### Adding Medications

```
Добавь аспирин в 10:00
Принимаю парацетамол 200 мг в 12:00 и 18:00
Нужно пить витамин D по утрам в 9:00
```

#### Viewing Schedule

```
Что я принимаю?
Покажи мое расписание
Список медикаментов
```

#### Deleting Medications

```
Удали аспирин
Больше не принимаю парацетамол
Убери витамин D
```

#### Changing Time

```
Аспирин теперь в 11:00
Измени время приема парацетамола на 19:00
Перенеси витамин D на 10:00
```

#### Changing Dosage

```
Аспирин теперь 300 мг
Измени дозировку парацетамола на 400 мг
```

#### Setting Timezone

```
Моя часовая зона Москва
Я в Лондоне
Установи часовой пояс +5
```

#### Marking as Taken

```
Принял аспирин
Выпил парацетамол
Готово
```

### System Commands

- `/stats` - Show bot statistics (users, medications, uptime)

### Interactive Features

When a reminder is sent, the bot displays an inline button "Принял ✓". Clicking it:
- Marks the medication as taken
- Removes the button from the message
- Prevents duplicate reminders for the same day

## Project Structure

```
medical_bot/
├── src/
│   ├── main.py                 # Application entry point
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── bot.py              # Bot initialization
│   │   └── handlers.py         # Message and callback handlers
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py         # Configuration management
│   ├── data/
│   │   ├── __init__.py
│   │   ├── models.py           # Data models (UserData, Medication)
│   │   └── storage.py          # JSON storage manager
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py           # Groq API client
│   │   └── prompts.py          # LLM prompts
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scheduler.py        # Reminder scheduler
│   │   ├── schedule_manager.py # Schedule CRUD operations
│   │   └── notification_manager.py # Notification logic
│   └── utils/
│       ├── __init__.py
│       ├── logger.py           # Logging configuration
│       ├── error_handler.py    # Error formatting
│       └── timezone.py         # Timezone utilities
├── data/
│   └── users/                  # User data files (*.json)
├── logs/                       # Log files
├── docs/                       # Documentation
├── examples/                   # Example scripts
├── .env                        # Environment configuration (not in git)
├── .env.example                # Example environment file
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
└── README.md                   # This file
```

## Architecture Overview

The bot follows a layered architecture:

1. **Presentation Layer** ([`src/bot/`](src/bot/))
   - Telegram bot interface
   - Message handlers
   - Callback query handlers

2. **Business Logic Layer** ([`src/services/`](src/services/))
   - Schedule management
   - Reminder scheduling
   - Notification logic

3. **LLM Integration Layer** ([`src/llm/`](src/llm/))
   - Natural language processing
   - Command detection and parsing
   - Two-stage processing pipeline

4. **Data Layer** ([`src/data/`](src/data/))
   - Data models
   - JSON storage with atomic writes
   - User data management

5. **Infrastructure Layer** ([`src/utils/`](src/utils/), [`src/config/`](src/config/))
   - Logging
   - Configuration
   - Error handling
   - Timezone utilities

For detailed architecture documentation, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Troubleshooting

### Bot doesn't respond

1. Check if bot is running: `ps aux | grep python`
2. Verify Telegram token: Test with `curl https://api.telegram.org/bot<TOKEN>/getMe`
3. Check logs in `logs/` directory
4. Ensure bot is not blocked by user

### Reminders not sent

1. Verify scheduler is running (check logs for "Scheduler started")
2. Check `SCHEDULER_INTERVAL_SECONDS` setting
3. Verify user timezone is set correctly
4. Check for Telegram API errors in logs

### LLM errors

1. Verify Groq API key is valid
2. Check API quota/limits at [Groq Console](https://console.groq.com)
3. Review `GROQ_TIMEOUT` and `GROQ_MAX_RETRIES` settings
4. Check logs for specific error messages

### Data corruption

1. Check `data/users/` for `.json.tmp` files (incomplete writes)
2. Review logs for "Corrupted JSON file" messages
3. Backup and restore from previous version if needed
4. Bot automatically recreates corrupted files

### High memory usage

1. Check number of users: `ls data/users/*.json | wc -l`
2. Review log file sizes in `logs/`
3. Consider log rotation
4. Monitor with `htop` or similar tools

### Timezone issues

1. Verify timezone format: `+HH:MM` or `-HH:MM`
2. Check user's timezone setting in their JSON file
3. Test with `/stats` command
4. Update timezone: "моя часовая зона +3"

## Development

### Running Tests

**Important**: Always activate the virtual environment before running tests:

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

### Code Style

The project follows PEP 8 style guidelines:

```bash
# Format code
black src/

# Check style
flake8 src/

# Type checking
mypy src/
```

### Logging

Logs are written to:
- Console: `INFO` level and above (configurable)
- File: `logs/medication_bot.log` - All levels including `DEBUG`

Log format includes:
- Timestamp
- Level
- Module
- Message
- Structured context (user_id, operation, etc.)

## Docker Deployment

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for detailed deployment instructions including:
- Docker setup
- Systemd service configuration
- Production best practices
- Monitoring and logging

## Documentation

- [`docs/SETUP.md`](docs/SETUP.md) - Detailed setup guide
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - System architecture
- [`docs/API.md`](docs/API.md) - Module API documentation
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) - Deployment guide

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review existing issues on GitHub
- Create a new issue with detailed information

## Acknowledgments

- [aiogram](https://github.com/aiogram/aiogram) - Telegram Bot framework
- [Groq](https://groq.com) - LLM API provider
- [loguru](https://github.com/Delgan/loguru) - Logging library
