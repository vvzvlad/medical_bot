# Implementation Guide: Medication Reminder Bot

## File Structure

```
medical_bot/
├── .env                          # Configuration (not in git)
├── .env.example                  # Template for .env
├── .gitignore
├── requirements.txt
├── README.md
├── data/
│   └── medications.db           # SQLite database (created at runtime)
├── src/
│   ├── __init__.py
│   ├── main.py                  # Entry point
│   ├── settings.py              # Configuration management
│   ├── database.py              # SQLite operations
│   ├── llm_client.py            # Groq API client
│   ├── llm_processor.py         # Two-stage LLM pipeline
│   ├── prompts.py               # All LLM prompts (reuse from src_old)
│   ├── telegram_bot.py          # Telegram bot handlers
│   ├── scheduler.py             # Notification scheduler
│   └── timezone_utils.py        # Timezone calculations
├── tests/
│   ├── unit/
│   └── integration/
└── plans/
    ├── architecture.md          # This document
    └── implementation_guide.md  # Step-by-step guide
```

---

## Implementation Order

### Step 1: Settings Module (`settings.py`)

**Purpose**: Load and validate configuration

**Implementation**:
```python
"""Configuration settings for medication bot."""

import os
from pathlib import Path
from dotenv import load_dotenv


class Settings:
    """Application settings from environment variables."""
    
    def __init__(self):
        # Load .env
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)
        
        # Telegram
        self.telegram_bot_token = self._get_required("TELEGRAM_BOT_TOKEN")
        
        # Groq LLM
        self.groq_api_key = self._get_required("GROQ_API_KEY")
        self.groq_model = self._get("GROQ_MODEL", "openai/gpt-oss-120b")
        self.groq_timeout = int(self._get("GROQ_TIMEOUT", "30"))
        self.groq_max_retries = int(self._get("GROQ_MAX_RETRIES", "3"))
        
        # Application
        self.log_level = self._get("LOG_LEVEL", "INFO")
        self.database_path = Path(self._get("DATABASE_PATH", "data/medications.db"))
        self.scheduler_interval = int(self._get("SCHEDULER_INTERVAL_SECONDS", "60"))
        self.reminder_interval_hours = int(self._get("REMINDER_REPEAT_INTERVAL_HOURS", "1"))
        self.default_timezone = self._get("DEFAULT_TIMEZONE_OFFSET", "+03:00")
        
        # Ensure data directory exists
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _get(self, key: str, default: str) -> str:
        return os.getenv(key, default)
    
    def _get_required(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required env var {key} not set")
        return value


# Global settings instance
settings = Settings()
```

**Test**: Create `.env` file and verify loading

---

### Step 2: Database Module (`database.py`)

**Purpose**: SQLite operations with proper schema

**Key Functions**:
1. `init_database()` - Create tables and indexes
2. `create_user(user_id, timezone_offset)` - New user
3. `get_user(user_id)` - Load user data
4. `add_medication(user_id, name, time, dosage)` - Add medication
5. `get_medications(user_id)` - Get all user medications
6. `check_duplicate(user_id, name, time)` - Deduplication check
7. `delete_medication(medication_id)` - Remove medication
8. `update_medication_time(medication_id, new_time)` - Change time
9. `update_medication_dosage(medication_id, new_dosage)` - Change dose
10. `get_intake_status(user_id, medication_id, date)` - Check if taken
11. `mark_as_taken(user_id, medication_id, date, taken_at)` - Record intake
12. `set_reminder_message_id(user_id, medication_id, date, message_id)` - Track reminder
13. `get_pending_reminders(user_id, date)` - Find active reminders
14. `get_all_users()` - For scheduler

**Implementation Pattern**:
```python
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
    
    async def init(self):
        """Initialize database with schema."""
        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for better concurrency
            await db.execute("PRAGMA journal_mode=WAL")
            
            # Create tables
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    timezone_offset TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS medications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    dosage TEXT,
                    time TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    UNIQUE(user_id, name, time),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS intake_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    medication_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    taken_at INTEGER,
                    reminder_message_id INTEGER,
                    UNIQUE(user_id, medication_id, date),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (medication_id) REFERENCES medications(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_medications_user_time "
                "ON medications(user_id, time)"
            )
            
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_intake_status_user_date "
                "ON intake_status(user_id, date)"
            )
            
            await db.commit()
    
    async def create_user(self, user_id: int, timezone_offset: str):
        """Create new user."""
        now = int(datetime.utcnow().timestamp())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, timezone_offset, created_at, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (user_id, timezone_offset, now, now)
            )
            await db.commit()
    
    async def add_medication(
        self, 
        user_id: int, 
        name: str, 
        time: str, 
        dosage: Optional[str] = None
    ) -> Optional[int]:
        """Add medication. Returns medication_id or None if duplicate."""
        now = int(datetime.utcnow().timestamp())
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute(
                    "INSERT INTO medications (user_id, name, dosage, time, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user_id, name.lower(), dosage, time, now)
                )
                await db.commit()
                return cursor.lastrowid
            except aiosqlite.IntegrityError:
                # Duplicate (user_id, name, time)
                return None
    
    async def check_duplicate(self, user_id: int, name: str, time: str) -> bool:
        """Check if medication already exists."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM medications "
                "WHERE user_id = ? AND name = ? AND time = ?",
                (user_id, name.lower(), time)
            )
            count = (await cursor.fetchone())[0]
            return count > 0
    
    # ... implement other methods
```

**Test**: Create database and verify tables/indexes

---

### Step 3: Timezone Utilities (`timezone_utils.py`)

**Purpose**: Timezone calculations

**Key Functions**:
```python
from datetime import datetime, timedelta, timezone


def parse_timezone_offset(offset_str: str) -> timedelta:
    """Parse '+03:00' or '-05:00' to timedelta."""
    sign = 1 if offset_str[0] == '+' else -1
    hours, minutes = map(int, offset_str[1:].split(':'))
    return timedelta(hours=sign * hours, minutes=sign * minutes)


def get_user_current_time(timezone_offset: str) -> datetime:
    """Get current time in user's timezone."""
    utc_now = datetime.now(timezone.utc)
    offset = parse_timezone_offset(timezone_offset)
    user_tz = timezone(offset)
    return utc_now.astimezone(user_tz)


def format_date_for_user(timezone_offset: str) -> str:
    """Get date string YYYY-MM-DD in user's timezone."""
    user_time = get_user_current_time(timezone_offset)
    return user_time.strftime("%Y-%m-%d")


def is_time_to_send_notification(
    medication_time: str,  # "HH:MM"
    user_timezone: str,
    already_sent_today: bool
) -> bool:
    """Check if notification should be sent now."""
    if already_sent_today:
        return False
    
    user_now = get_user_current_time(user_timezone)
    med_hour, med_minute = map(int, medication_time.split(':'))
    
    # Check if current time >= medication time
    current_minutes = user_now.hour * 60 + user_now.minute
    med_minutes = med_hour * 60 + med_minute
    
    return current_minutes >= med_minutes


def should_send_hourly_reminder(
    reminder_sent_at: int,  # Unix timestamp
    interval_hours: int = 1
) -> bool:
    """Check if hourly reminder should be sent."""
    now = datetime.utcnow().timestamp()
    hours_passed = (now - reminder_sent_at) / 3600
    return hours_passed >= interval_hours
```

**Test**: Verify timezone conversions across midnight

---

### Step 4: LLM Client (`llm_client.py`)

**Purpose**: Groq API communication

**Implementation**:
```python
import httpx
import json
from typing import Dict, Optional
from loguru import logger


class LLMClient:
    def __init__(self, api_key: str, model: str, timeout: int = 30, max_retries: int = 3):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
    
    async def complete(
        self, 
        system_prompt: str, 
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        json_mode: bool = False
    ) -> str:
        """Send completion request to Groq API."""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.base_url,
                        headers=headers,
                        json=payload
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    logger.debug(f"LLM response: {content[:100]}...")
                    return content
                    
            except httpx.TimeoutException:
                logger.warning(f"LLM timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    raise
            except httpx.HTTPStatusError as e:
                logger.error(f"LLM HTTP error: {e.response.status_code}")
                if e.response.status_code == 429:  # Rate limit
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
        
        raise Exception("LLM request failed after retries")
    
    async def complete_json(
        self,
        system_prompt: str,
        user_message: str
    ) -> Dict:
        """Request JSON response and parse it."""
        content = await self.complete(
            system_prompt, 
            user_message,
            json_mode=True
        )
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {content}")
            raise
```

**Test**: Make test call to Groq API

---

### Step 5: Prompts (`prompts.py`)

**Action**: Copy from `src_old/llm/prompts.py` and adapt as needed

**Changes**:
- Keep all prompt functions
- Ensure grammatical rules are preserved (genitive case, etc.)
- Validate JSON response formats

---

### Step 6: LLM Processor (`llm_processor.py`)

**Purpose**: Two-stage LLM pipeline

**Implementation**:
```python
from typing import Dict, List, Optional
from loguru import logger
from .llm_client import LLMClient
from .prompts import (
    get_command_detection_prompt,
    get_add_command_prompt,
    get_delete_command_prompt,
    get_done_command_prompt,
    # ... other prompt functions
)


class LLMProcessor:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    async def classify_intent(self, user_message: str) -> str:
        """Stage 1: Classify command type."""
        prompt = get_command_detection_prompt(user_message)
        response = await self.llm.complete_json(prompt, user_message)
        
        command_type = response.get("command_type", "unknown")
        logger.info(f"Classified intent: {command_type}")
        return command_type
    
    async def process_add(self, user_message: str) -> List[Dict]:
        """Parse ADD command."""
        prompt = get_add_command_prompt(user_message)
        response = await self.llm.complete_json(prompt, user_message)
        
        # Expected: [{"medication_name": "...", "times": [...], "dosage": "..."}]
        return response if isinstance(response, list) else [response]
    
    async def process_done(
        self, 
        user_message: str, 
        user_schedule: List[Dict]
    ) -> Dict:
        """Parse DONE command with schedule context."""
        prompt = get_done_command_prompt(user_message, user_schedule)
        response = await self.llm.complete_json(prompt, user_message)
        
        # Expected: {"medication_name": "...", "time": "...", "medication_ids": [...]}
        return response
    
    async def process_delete(
        self,
        user_message: str,
        user_schedule: List[Dict]
    ) -> Dict:
        """Parse DELETE command."""
        prompt = get_delete_command_prompt(user_message, user_schedule)
        response = await self.llm.complete_json(prompt, user_message)
        
        # Expected: {"status": "...", "medication_name": "...", "medication_ids": [...]}
        return response
    
    async def process_time_change(
        self,
        user_message: str,
        user_schedule: List[Dict]
    ) -> Dict:
        """Parse TIME_CHANGE command."""
        prompt = get_time_change_command_prompt(user_message, user_schedule)
        response = await self.llm.complete_json(prompt, user_message)
        return response
    
    async def process_dose_change(
        self,
        user_message: str,
        user_schedule: List[Dict]
    ) -> Dict:
        """Parse DOSE_CHANGE command."""
        prompt = get_dose_change_command_prompt(user_message, user_schedule)
        response = await self.llm.complete_json(prompt, user_message)
        return response
    
    async def process_timezone_change(self, user_message: str) -> Dict:
        """Parse TIMEZONE_CHANGE command."""
        prompt = get_timezone_change_command_prompt(user_message)
        response = await self.llm.complete_json(prompt, user_message)
        return response
```

**Test**: Mock LLM responses and verify parsing

---

### Step 7: Telegram Bot (`telegram_bot.py`)

**Purpose**: Handle Telegram interactions

**Key Components**:
```python
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from loguru import logger


class MedicationBot:
    def __init__(self, token: str, llm_processor, database):
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.llm = llm_processor
        self.db = database
        
        # Setup handlers
        router = Router()
        router.message.register(self.handle_message)
        router.callback_query.register(
            self.handle_taken_callback,
            F.data.startswith("taken:")
        )
        self.dp.include_router(router)
    
    async def handle_message(self, message: Message):
        """Process incoming text message."""
        user_id = message.from_user.id
        text = message.text
        
        logger.info(f"Message from {user_id}: {text}")
        
        # Ensure user exists
        await self.db.create_user(user_id, "+03:00")  # Default timezone
        
        try:
            # Stage 1: Classify
            command_type = await self.llm.classify_intent(text)
            
            # Stage 2: Process
            if command_type == "add":
                await self._handle_add(message, text)
            elif command_type == "done":
                await self._handle_done(message, text)
            elif command_type == "delete":
                await self._handle_delete(message, text)
            elif command_type == "time_change":
                await self._handle_time_change(message, text)
            elif command_type == "dose_change":
                await self._handle_dose_change(message, text)
            elif command_type == "timezone_change":
                await self._handle_timezone_change(message, text)
            elif command_type == "list":
                await self._handle_list(message)
            elif command_type == "help":
                await self._handle_help(message)
            else:
                await message.reply("Извините, я не понял команду. Напишите 'помощь' для справки.")
        
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await message.reply("Произошла ошибка. Попробуйте еще раз.")
    
    async def _handle_add(self, message: Message, text: str):
        """Handle ADD command."""
        user_id = message.from_user.id
        
        # Parse medications
        medications = await self.llm.process_add(text)
        
        added = []
        duplicates = []
        
        for med_data in medications:
            name = med_data["medication_name"]
            dosage = med_data.get("dosage")
            times = med_data["times"]
            
            for time in times:
                # Check duplicate
                if await self.db.check_duplicate(user_id, name, time):
                    duplicates.append(f"{name} в {time}")
                else:
                    med_id = await self.db.add_medication(user_id, name, time, dosage)
                    if med_id:
                        added.append(f"{name} в {time}")
        
        # Format response
        response_parts = []
        if added:
            response_parts.append("Добавлено:\n" + "\n".join(f"✓ {item}" for item in added))
        if duplicates:
            response_parts.append("Уже в расписании:\n" + "\n".join(f"• {item}" for item in duplicates))
        
        await message.reply("\n\n".join(response_parts))
    
    async def _handle_done(self, message: Message, text: str):
        """Handle DONE command."""
        user_id = message.from_user.id
        
        # Load schedule
        medications = await self.db.get_medications(user_id)
        schedule = [
            {"id": m["id"], "name": m["name"], "time": m["time"], "dosage": m["dosage"]}
            for m in medications
        ]
        
        # Parse
        result = await self.llm.process_done(text, schedule)
        medication_ids = result.get("medication_ids", [])
        
        if not medication_ids:
            await message.reply(f"{result['medication_name']} не найден в расписании")
            return
        
        # Mark as taken
        user_date = format_date_for_user("+03:00")  # TODO: Load user timezone
        now = int(datetime.utcnow().timestamp())
        
        for med_id in medication_ids:
            await self.db.mark_as_taken(user_id, med_id, user_date, now)
        
        # Generate confirmation message
        await message.reply(f"Отмечено: {result['medication_name']} принят ✓")
    
    async def _handle_list(self, message: Message):
        """Handle LIST command."""
        user_id = message.from_user.id
        medications = await self.db.get_medications(user_id)
        
        if not medications:
            await message.reply("Ваше расписание пусто. Добавьте медикаменты.")
            return
        
        # Sort by time
        medications.sort(key=lambda m: m["time"])
        
        lines = ["Ваше расписание:"]
        for med in medications:
            dosage_str = f" ({med['dosage']})" if med["dosage"] else ""
            lines.append(f"• {med['time']} - {med['name'].capitalize()}{dosage_str}")
        
        await message.reply("\n".join(lines))
    
    async def handle_taken_callback(self, callback: CallbackQuery):
        """Handle 'Принял' button press."""
        # Parse callback data: "taken:{medication_id}:{date}"
        parts = callback.data.split(":")
        medication_id = int(parts[1])
        date = parts[2]
        user_id = callback.from_user.id
        
        # Mark as taken
        now = int(datetime.utcnow().timestamp())
        await self.db.mark_as_taken(user_id, medication_id, date, now)
        
        # Edit message
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ Принято",
            reply_markup=None
        )
        
        await callback.answer("Отмечено!")
    
    async def start(self):
        """Start bot."""
        logger.info("Starting bot...")
        await self.dp.start_polling(self.bot)
```

**Test**: Send test messages to bot

---

### Step 8: Scheduler (`scheduler.py`)

**Purpose**: Notification and reminder system

**Implementation**:
```python
import asyncio
from datetime import datetime
from loguru import logger
from .database import Database
from .telegram_bot import MedicationBot
from .timezone_utils import (
    get_user_current_time,
    format_date_for_user,
    is_time_to_send_notification,
    should_send_hourly_reminder
)


class NotificationScheduler:
    def __init__(
        self, 
        database: Database, 
        bot: MedicationBot,
        interval_seconds: int = 60,
        reminder_interval_hours: int = 1
    ):
        self.db = database
        self.bot = bot
        self.interval = interval_seconds
        self.reminder_interval = reminder_interval_hours
        self.running = False
    
    async def start(self):
        """Start scheduler loop."""
        self.running = True
        logger.info("Scheduler started")
        
        while self.running:
            try:
                await self._check_and_send_notifications()
                await self._check_and_send_reminders()
            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)
            
            await asyncio.sleep(self.interval)
    
    def stop(self):
        """Stop scheduler."""
        self.running = False
        logger.info("Scheduler stopped")
    
    async def _check_and_send_notifications(self):
        """Check for medications that need initial notification."""
        users = await self.db.get_all_users()
        
        for user in users:
            user_id = user["user_id"]
            timezone = user["timezone_offset"]
            user_date = format_date_for_user(timezone)
            
            medications = await self.db.get_medications(user_id)
            
            for med in medications:
                # Check if it's time to send
                status = await self.db.get_intake_status(
                    user_id, 
                    med["id"], 
                    user_date
                )
                
                already_sent = status is not None
                should_send = is_time_to_send_notification(
                    med["time"],
                    timezone,
                    already_sent
                )
                
                if should_send:
                    await self._send_notification(user_id, med, user_date)
    
    async def _send_notification(self, user_id: int, medication: dict, date: str):
        """Send initial notification for medication."""
        logger.info(f"Sending notification: {medication['name']} to user {user_id}")
        
        # Format message
        dosage_str = f" ({medication['dosage']})" if medication["dosage"] else ""
        text = f"Надо принять:\n{medication['name'].capitalize()}{dosage_str}"
        
        # Create button
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="Принял",
                callback_data=f"taken:{medication['id']}:{date}"
            )]
        ])
        
        # Send message
        message = await self.bot.bot.send_message(
            user_id,
            text,
            reply_markup=keyboard
        )
        
        # Create intake_status record
        await self.db.create_intake_status(
            user_id,
            medication["id"],
            date,
            message.message_id
        )
    
    async def _check_and_send_reminders(self):
        """Check for pending reminders (hourly repeats)."""
        users = await self.db.get_all_users()
        
        for user in users:
            user_id = user["user_id"]
            timezone = user["timezone_offset"]
            user_date = format_date_for_user(timezone)
            
            # Get pending reminders
            pending = await self.db.get_pending_reminders(user_id, user_date)
            
            for status in pending:
                # Check if hour has passed
                if status["reminder_sent_at"]:
                    should_remind = should_send_hourly_reminder(
                        status["reminder_sent_at"],
                        self.reminder_interval
                    )
                    
                    if should_remind:
                        await self._send_hourly_reminder(
                            user_id,
                            status,
                            user_date
                        )
    
    async def _send_hourly_reminder(
        self, 
        user_id: int, 
        status: dict, 
        date: str
    ):
        """Send or edit hourly reminder."""
        logger.info(f"Sending hourly reminder for medication {status['medication_id']}")
        
        medication = await self.db.get_medication(status["medication_id"])
        
        dosage_str = f" ({medication['dosage']})" if medication["dosage"] else ""
        text = f"Напоминание:\n{medication['name'].capitalize()}{dosage_str}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="Принял",
                callback_data=f"taken:{medication['id']}:{date}"
            )]
        ])
        
        # Try to edit existing message
        if status["reminder_message_id"]:
            try:
                await self.bot.bot.edit_message_text(
                    text,
                    user_id,
                    status["reminder_message_id"],
                    reply_markup=keyboard
                )
            except Exception:
                # Message not found, send new
                message = await self.bot.bot.send_message(
                    user_id,
                    text,
                    reply_markup=keyboard
                )
                await self.db.update_reminder_message_id(
                    status["id"],
                    message.message_id
                )
        
        # Update timestamp
        await self.db.update_reminder_sent_at(
            status["id"],
            int(datetime.utcnow().timestamp())
        )
```

**Test**: Mock time and verify notifications sent

---

### Step 9: Main Entry Point (`main.py`)

**Purpose**: Initialize and run application

**Implementation**:
```python
import asyncio
from loguru import logger
from .settings import settings
from .database import Database
from .llm_client import LLMClient
from .llm_processor import LLMProcessor
from .telegram_bot import MedicationBot
from .scheduler import NotificationScheduler


async def main():
    """Main application entry point."""
    
    # Configure logging
    logger.add(
        "logs/bot_{time}.log",
        rotation="1 day",
        retention="7 days",
        level=settings.log_level
    )
    
    logger.info("Starting Medication Reminder Bot")
    
    # Initialize components
    database = Database(settings.database_path)
    await database.init()
    logger.info("Database initialized")
    
    llm_client = LLMClient(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        timeout=settings.groq_timeout,
        max_retries=settings.groq_max_retries
    )
    logger.info("LLM client initialized")
    
    llm_processor = LLMProcessor(llm_client)
    
    bot = MedicationBot(
        token=settings.telegram_bot_token,
        llm_processor=llm_processor,
        database=database
    )
    logger.info("Telegram bot initialized")
    
    scheduler = NotificationScheduler(
        database=database,
        bot=bot,
        interval_seconds=settings.scheduler_interval,
        reminder_interval_hours=settings.reminder_interval_hours
    )
    
    # Start scheduler and bot concurrently
    await asyncio.gather(
        scheduler.start(),
        bot.start()
    )


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Testing Strategy

### Unit Tests

1. **Database Operations** (`tests/unit/test_database.py`)
   - Create/read/update/delete operations
   - Duplicate detection
   - Foreign key constraints

2. **Timezone Utilities** (`tests/unit/test_timezone_utils.py`)
   - Timezone parsing
   - Time conversions
   - Date formatting

3. **LLM Response Parsing** (`tests/unit/test_llm_processor.py`)
   - Mock LLM responses
   - Test each command parser
   - Handle malformed JSON

### Integration Tests

1. **Command Flows** (`tests/integration/test_commands.py`)
   - Add → list → delete flow
   - Done command with multiple medications
   - Time change → verify update

2. **Notification Flow** (`tests/integration/test_notifications.py`)
   - Mock time advancement
   - Verify notification sent at correct time
   - Test hourly reminders

3. **Recovery** (`tests/integration/test_recovery.py`)
   - Simulate downtime
   - Verify missed notifications sent

### LLM Tests

Use existing tests in `tests/integration/` as baseline. Ensure:
- High classification accuracy (>95%)
- Correct parameter extraction
- Edge cases handled

---

## Deployment Checklist

- [ ] Set up `.env` file with API keys
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Initialize database: `python -m src.database init`
- [ ] Test LLM connection
- [ ] Test Telegram bot connection
- [ ] Run unit tests: `pytest tests/unit/`
- [ ] Run integration tests: `pytest tests/integration/`
- [ ] Configure logging directory
- [ ] Set up systemd service (for production)
- [ ] Configure database backups
- [ ] Monitor logs for errors

---

## Development Tips

1. **Iterate on Prompts**: Use `tests/integration/test_llm_real_api.py` to test prompts
2. **Test with Real Data**: Create test user and medication schedule
3. **Mock Time**: Use `freezegun` for testing time-dependent features
4. **Database Inspection**: Use `sqlite3 data/medications.db` to inspect data
5. **Logging**: Use DEBUG level during development for detailed logs

---

## Common Issues and Solutions

### Issue: LLM returns invalid JSON
**Solution**: Add retry logic with more explicit instructions in prompt

### Issue: Timezone confusion
**Solution**: Always store in user's local time, convert only when comparing

### Issue: Missed notifications not sent
**Solution**: Check scheduler logic in `_check_and_send_notifications()`

### Issue: Duplicate medications created
**Solution**: Verify UNIQUE constraint on database, check lowercase normalization

### Issue: Reminder message not edited
**Solution**: Handle MessageNotFound exception, send new message instead

---

## Performance Optimization

1. **Database Queries**:
   - Use indexes for common queries
   - Batch operations when possible
   - Optimize scheduler queries with date filtering

2. **LLM Calls**:
   - Cache system prompts (not applicable for dynamic prompts)
   - Use lower temperature for classification (0.3-0.5)
   - Reduce max_tokens for simple responses

3. **Telegram API**:
   - Use connection pooling (handled by aiogram)
   - Handle rate limits gracefully
   - Batch notifications if multiple medications

---

## Next Steps After Implementation

1. **User Feedback**: Test with real users
2. **Prompt Refinement**: Improve classification accuracy based on errors
3. **Feature Additions**: 
   - Period field for non-daily medications
   - Statistics on adherence
   - Export schedule to PDF
4. **Production Hardening**:
   - Add health check endpoint
   - Implement graceful shutdown
   - Add metrics and monitoring
5. **Documentation**: Write user guide in Russian

---

This guide provides a complete roadmap for implementing the medication reminder bot. Follow the steps sequentially, testing each component before moving to the next.
