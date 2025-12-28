# Setup Guide

This guide provides detailed step-by-step instructions for setting up the Medication Bot from scratch.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Getting Telegram Bot Token](#getting-telegram-bot-token)
- [Getting Groq API Key](#getting-groq-api-key)
- [Environment Setup](#environment-setup)
- [Configuration](#configuration)
- [First Run](#first-run)
- [Testing the Bot](#testing-the-bot)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, ensure you have the following installed:

### Required Software

1. **Python 3.11 or higher**
   ```bash
   # Check Python version
   python3 --version
   # Should output: Python 3.11.x or higher
   ```

   If you need to install Python:
   - **macOS**: `brew install python@3.11`
   - **Ubuntu/Debian**: `sudo apt install python3.11 python3.11-venv`
   - **Windows**: Download from [python.org](https://www.python.org/downloads/)

2. **pip** (Python package manager)
   ```bash
   # Check pip version
   pip3 --version
   ```

3. **Git** (for cloning the repository)
   ```bash
   # Check git version
   git --version
   ```

### System Requirements

- **RAM**: Minimum 512 MB, recommended 1 GB
- **Disk Space**: Minimum 100 MB for application + space for logs and user data
- **Network**: Stable internet connection for Telegram and Groq API

## Getting Telegram Bot Token

### Step 1: Open BotFather

1. Open Telegram app
2. Search for `@BotFather` (official bot with blue checkmark)
3. Start a conversation with `/start`

### Step 2: Create New Bot

1. Send command: `/newbot`
2. BotFather will ask for a name for your bot
   - Example: `My Medication Bot`
3. BotFather will ask for a username (must end with 'bot')
   - Example: `my_medication_bot`
   - Must be unique across all Telegram

### Step 3: Save Your Token

BotFather will respond with a message containing your bot token:

```
Done! Congratulations on your new bot. You will find it at t.me/my_medication_bot.
You can now add a description, about section and profile picture for your bot.

Use this token to access the HTTP API:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890

Keep your token secure and store it safely, it can be used by anyone to control your bot.
```

**Important**: 
- Copy and save this token securely
- Never share it publicly or commit it to version control
- If compromised, use `/revoke` command in BotFather to get a new token

### Step 4: Configure Bot Settings (Optional)

You can customize your bot:

```
/setdescription - Set bot description
/setabouttext - Set about text
/setuserpic - Set bot profile picture
/setcommands - Set bot commands for menu
```

Example commands to set:
```
stats - Show bot statistics
```

## Getting Groq API Key

### Step 1: Create Groq Account

1. Visit [Groq Console](https://console.groq.com)
2. Click "Sign Up" or "Get Started"
3. Sign up with:
   - Email and password, or
   - Google account, or
   - GitHub account

### Step 2: Verify Email

1. Check your email for verification link
2. Click the link to verify your account
3. Complete any additional profile information

### Step 3: Generate API Key

1. Log in to [Groq Console](https://console.groq.com)
2. Navigate to "API Keys" section (usually in left sidebar)
3. Click "Create API Key" or "New API Key"
4. Give your key a descriptive name:
   - Example: `Medication Bot Production`
5. Copy the generated API key immediately
   - **Important**: You won't be able to see it again!

### Step 4: Check API Limits

1. Review your account's API limits and quotas
2. Free tier typically includes:
   - Limited requests per minute
   - Limited tokens per day
3. Monitor usage in the Groq Console dashboard

### Step 5: Save API Key Securely

- Store in password manager
- Never commit to version control
- Keep separate keys for development and production

## Environment Setup

### Step 1: Clone Repository

```bash
# Clone the repository
git clone <repository-url>
cd medical_bot

# Or if you have the source code as archive
unzip medical_bot.zip
cd medical_bot
```

### Step 2: Create Virtual Environment

Creating a virtual environment isolates project dependencies:

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Your prompt should now show (venv) prefix
```

**Why use virtual environment?**
- Isolates project dependencies
- Prevents conflicts with system Python packages
- Makes deployment reproducible

### Step 3: Install Dependencies

```bash
# Ensure pip is up to date
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

Expected packages:
- `aiogram==3.15.0` - Telegram Bot framework
- `python-dotenv==1.0.1` - Environment configuration
- `loguru==0.7.2` - Logging
- `httpx==0.27.2` - HTTP client
- `aiofiles==24.1.0` - Async file I/O

### Step 4: Verify Installation

```bash
# Test Python imports
python3 -c "import aiogram; import loguru; import httpx; print('All imports successful')"
```

If you see "All imports successful", you're ready to proceed!

## Configuration

### Step 1: Create Environment File

```bash
# Copy example environment file
cp .env.example .env

# Open in your preferred editor
nano .env
# or
vim .env
# or
code .env  # VS Code
```

### Step 2: Configure Required Variables

Edit `.env` and set these **required** variables:

```env
# REQUIRED: Your Telegram Bot Token from BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890

# REQUIRED: Your Groq API Key
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 3: Configure Optional Variables

Customize these settings based on your needs:

```env
# Groq LLM Configuration
GROQ_MODEL=openai/gpt-oss-120b          # LLM model to use
GROQ_TIMEOUT=30                          # API timeout in seconds
GROQ_MAX_RETRIES=3                       # Max retry attempts

# Application Configuration
LOG_LEVEL=INFO                           # DEBUG, INFO, WARNING, ERROR
DATA_DIR=data/users                      # User data storage directory
SCHEDULER_INTERVAL_SECONDS=60            # How often to check for reminders
REMINDER_REPEAT_INTERVAL_HOURS=1         # Repeat reminder interval

# Timezone Configuration
DEFAULT_TIMEZONE_OFFSET=+03:00           # Default timezone for new users
```

### Step 4: Verify Configuration

```bash
# Test configuration loading
python3 -c "from src.config import settings; print('Config loaded successfully')"
```

If you see an error about missing variables, double-check your `.env` file.

### Step 5: Create Required Directories

```bash
# Create data directories
mkdir -p data/users
mkdir -p logs

# Verify structure
ls -la data/
ls -la logs/
```

## First Run

### Step 1: Start the Bot

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Start the bot
python -m src.main
```

### Step 2: Check Startup Logs

You should see output similar to:

```
2024-12-28 10:23:06.123 | INFO     | src.main:main:23 - ============================================================
2024-12-28 10:23:06.124 | INFO     | src.main:main:24 - Starting Medication Bot
2024-12-28 10:23:06.125 | INFO     | src.main:main:25 - ============================================================
2024-12-28 10:23:06.126 | INFO     | src.main:main:27 - Data directory: data/users
2024-12-28 10:23:06.127 | INFO     | src.main:main:28 - Default timezone: +03:00
2024-12-28 10:23:06.128 | INFO     | src.main:main:29 - Scheduler interval: 60s
2024-12-28 10:23:06.129 | INFO     | src.main:main:30 - Reminder repeat interval: 1h
2024-12-28 10:23:06.234 | INFO     | src.bot.bot:init_bot:61 - Bot initialized successfully
2024-12-28 10:23:06.345 | INFO     | src.main:main:49 - Scheduler initialized
2024-12-28 10:23:06.456 | INFO     | src.main:main:69 - Scheduler started successfully
2024-12-28 10:23:06.567 | INFO     | src.main:main:75 - Starting bot polling...
2024-12-28 10:23:06.678 | INFO     | src.bot.bot:on_startup:68 - Bot started
2024-12-28 10:23:06.789 | INFO     | src.bot.bot:on_startup:76 - Bot username: @my_medication_bot
2024-12-28 10:23:06.890 | INFO     | src.bot.bot:on_startup:77 - Bot ID: 1234567890
```

### Step 3: Verify Bot is Running

1. Check that no errors appear in the logs
2. Verify scheduler started: Look for "Scheduler started successfully"
3. Verify bot polling: Look for "Starting bot polling..."
4. Note the bot username from logs

### Step 4: Stop the Bot (for testing)

Press `Ctrl+C` to stop the bot. You should see:

```
2024-12-28 10:25:00.123 | INFO     | src.main:signal_handler:59 - Received signal 2, initiating graceful shutdown...
2024-12-28 10:25:00.234 | INFO     | src.main:main:86 - Shutdown signal received, stopping services...
2024-12-28 10:25:00.345 | INFO     | src.main:main:90 - Scheduler stopped
2024-12-28 10:25:00.456 | INFO     | src.main:main:99 - Bot polling stopped
2024-12-28 10:25:00.567 | INFO     | src.main:main:103 - Bot session closed
2024-12-28 10:25:00.678 | INFO     | src.main:main:122 - ============================================================
2024-12-28 10:25:00.789 | INFO     | src.main:main:123 - Medication Bot stopped
2024-12-28 10:25:00.890 | INFO     | src.main:main:124 - ============================================================
```

## Testing the Bot

### Step 1: Start the Bot

```bash
python -m src.main
```

### Step 2: Find Your Bot in Telegram

1. Open Telegram
2. Search for your bot username (from startup logs)
3. Click "Start" or send `/start`

### Step 3: Test Basic Interaction

The bot should send a welcome message. Try these commands:

#### Test 1: Set Timezone

```
моя часовая зона Москва
```

Expected response:
```
Часовой пояс изменен на +03:00
```

#### Test 2: Add Medication

```
Добавь аспирин 200 мг в 10:00
```

Expected response:
```
Добавлено: аспирин 200 мг в 10:00
```

#### Test 3: View Schedule

```
что я принимаю?
```

Expected response:
```
Вы принимаете:
1) в 10:00 — аспирин 200 мг
```

#### Test 4: Add Multiple Times

```
Принимаю парацетамол в 12:00 и 18:00
```

Expected response:
```
Добавлено: парацетамол в 12:00 и 18:00
```

#### Test 5: View Updated Schedule

```
список
```

Expected response:
```
Вы принимаете:
1) в 10:00 — аспирин 200 мг
2) в 12:00 и 18:00 — парацетамол
```

#### Test 6: Change Time

```
аспирин теперь в 11:00
```

Expected response:
```
Время приема изменено на 11:00
```

#### Test 7: Delete Medication

```
удали парацетамол
```

Expected response:
```
Удалено медикаментов: 2
```

#### Test 8: Statistics

```
/stats
```

Expected response:
```
📊 Статистика бота:

👥 Всего пользователей: 1
💊 Всего медикаментов: 1
🔔 Отправлено напоминаний: 0
⏱ Время работы: 0ч 5м
```

### Step 4: Test Reminders

To test reminders without waiting:

1. Add a medication for current time + 2 minutes:
   ```
   Добавь тест в 10:32
   ```
   (Replace 10:32 with current time + 2 minutes)

2. Wait for the scheduled time
3. You should receive a reminder with a button "Принял ✓"
4. Click the button to mark as taken

### Step 5: Check Logs

```bash
# View real-time logs
tail -f logs/medication_bot.log

# Search for specific user activity
grep "user_id=YOUR_TELEGRAM_ID" logs/medication_bot.log

# Check for errors
grep "ERROR" logs/medication_bot.log
```

### Step 6: Verify Data Storage

```bash
# Check user data file was created
ls -la data/users/

# View your user data (replace with your Telegram ID)
cat data/users/YOUR_TELEGRAM_ID.json
```

Expected JSON structure:
```json
{
  "user_id": 123456789,
  "timezone_offset": "+03:00",
  "medications": [
    {
      "id": 1,
      "name": "аспирин",
      "dosage": "200 мг",
      "time": "11:00",
      "last_taken": null,
      "reminder_message_id": null
    }
  ]
}
```

## Troubleshooting

### Bot doesn't start

**Error**: `ValueError: Required environment variable 'TELEGRAM_BOT_TOKEN' is not set`

**Solution**:
1. Check `.env` file exists: `ls -la .env`
2. Verify token is set: `grep TELEGRAM_BOT_TOKEN .env`
3. Ensure no extra spaces around `=`
4. Token should not have quotes

---

**Error**: `ModuleNotFoundError: No module named 'aiogram'`

**Solution**:
1. Activate virtual environment: `source venv/bin/activate`
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Verify installation: `pip list | grep aiogram`

---

**Error**: `Permission denied` when creating directories

**Solution**:
```bash
# Check permissions
ls -la

# Create directories with proper permissions
mkdir -p data/users logs
chmod 755 data logs
chmod 755 data/users
```

### Bot doesn't respond in Telegram

**Problem**: Bot shows online but doesn't respond to messages

**Solution**:
1. Check bot is running: `ps aux | grep python`
2. Check logs for errors: `tail -f logs/medication_bot.log`
3. Verify bot token: `curl https://api.telegram.org/bot<TOKEN>/getMe`
4. Ensure you haven't blocked the bot in Telegram
5. Try `/start` command first

---

**Problem**: Bot responds slowly

**Solution**:
1. Check Groq API response time in logs
2. Increase `GROQ_TIMEOUT` if needed
3. Check network connectivity
4. Monitor system resources: `htop`

### LLM Processing Issues

**Error**: `GroqInsufficientFundsError: Insufficient funds on Groq account`

**Solution**:
1. Check Groq Console for account status
2. Add credits or upgrade plan
3. Check API usage limits

---

**Error**: `GroqTimeoutError: Request timed out after all retries`

**Solution**:
1. Increase `GROQ_TIMEOUT` in `.env` (e.g., `60`)
2. Increase `GROQ_MAX_RETRIES` (e.g., `5`)
3. Check internet connection
4. Try different Groq model

---

**Problem**: Bot doesn't understand commands

**Solution**:
1. Use Russian language for commands
2. Be specific: include medication name and time
3. Check logs for LLM response
4. Try rephrasing the command
5. Examples:
   - ✅ "Добавь аспирин в 10:00"
   - ❌ "Add aspirin at 10"

### Reminder Issues

**Problem**: Reminders not sent

**Solution**:
1. Check scheduler is running: `grep "Scheduler started" logs/medication_bot.log`
2. Verify medication time is in the future
3. Check timezone setting: View user JSON file
4. Ensure `SCHEDULER_INTERVAL_SECONDS` is reasonable (60)
5. Check for Telegram API errors in logs

---

**Problem**: Duplicate reminders

**Solution**:
1. Check only one bot instance is running: `ps aux | grep python`
2. Kill duplicate processes if found
3. Restart bot cleanly

---

**Problem**: Reminders sent at wrong time

**Solution**:
1. Verify user timezone: Check JSON file
2. Update timezone: "моя часовая зона +3"
3. Check system time: `date`
4. Ensure `DEFAULT_TIMEZONE_OFFSET` is correct

### Data Issues

**Problem**: User data lost

**Solution**:
1. Check `data/users/` directory exists
2. Look for `.json.tmp` files (incomplete writes)
3. Check file permissions: `ls -la data/users/`
4. Review logs for "Corrupted JSON file" messages
5. Restore from backup if available

---

**Problem**: Cannot save data

**Solution**:
```bash
# Check disk space
df -h

# Check directory permissions
ls -la data/

# Fix permissions if needed
chmod 755 data/users
```

### Log Issues

**Problem**: No logs generated

**Solution**:
1. Check `logs/` directory exists: `ls -la logs/`
2. Create if missing: `mkdir -p logs`
3. Check permissions: `chmod 755 logs`
4. Verify `LOG_LEVEL` in `.env`

---

**Problem**: Log files too large

**Solution**:
1. Implement log rotation (see [`docs/DEPLOYMENT.md`](DEPLOYMENT.md))
2. Reduce `LOG_LEVEL` to `WARNING` or `ERROR`
3. Archive old logs:
   ```bash
   gzip logs/medication_bot.log
   mv logs/medication_bot.log.gz logs/archive/
   ```

## Next Steps

After successful setup:

1. **Production Deployment**: See [`docs/DEPLOYMENT.md`](DEPLOYMENT.md)
2. **Architecture Understanding**: See [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
3. **API Documentation**: See [`docs/API.md`](API.md)
4. **Customize**: Modify prompts in [`src/llm/prompts.py`](../src/llm/prompts.py)
5. **Monitor**: Set up monitoring and alerting

## Getting Help

If you encounter issues not covered here:

1. Check logs in `logs/medication_bot.log`
2. Enable DEBUG logging: `LOG_LEVEL=DEBUG` in `.env`
3. Review [GitHub Issues](https://github.com/your-repo/issues)
4. Create new issue with:
   - Error message
   - Relevant logs
   - Steps to reproduce
   - Environment details (OS, Python version)

## Security Notes

- Never commit `.env` file to version control
- Keep API keys secure
- Use different keys for development and production
- Regularly rotate API keys
- Monitor API usage for anomalies
- Restrict file permissions: `chmod 600 .env`
