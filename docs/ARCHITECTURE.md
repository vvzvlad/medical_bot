# Architecture Documentation

This document provides a comprehensive overview of the Medication Bot's system architecture, design patterns, and implementation details.

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Layers](#architecture-layers)
- [Component Descriptions](#component-descriptions)
- [Data Flow](#data-flow)
- [Database Schema](#database-schema)
- [LLM Integration](#llm-integration)
- [Scheduler Logic](#scheduler-logic)
- [Error Handling Strategy](#error-handling-strategy)
- [Design Patterns](#design-patterns)
- [Scalability Considerations](#scalability-considerations)

## System Overview

The Medication Bot is built using a **layered architecture** pattern, separating concerns into distinct layers that communicate through well-defined interfaces. The system is designed to be:

- **Asynchronous**: Uses Python's `asyncio` for non-blocking I/O operations
- **Modular**: Clear separation of concerns with independent components
- **Resilient**: Comprehensive error handling and retry mechanisms
- **Maintainable**: Clean code structure with type hints and documentation

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Telegram Bot API                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Presentation Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Handlers   │  │  Callbacks   │  │   Commands   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 Business Logic Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Schedule   │  │  Scheduler   │  │ Notification │      │
│  │   Manager    │  │              │  │   Manager    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ LLM Layer   │  │ Data Layer  │  │ Utils Layer │
│             │  │             │  │             │
│ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │
│ │  Groq   │ │  │ │ Storage │ │  │ │ Logger  │ │
│ │ Client  │ │  │ │ Manager │ │  │ │         │ │
│ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │
│ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │
│ │ Prompts │ │  │ │ Models  │ │  │ │  Error  │ │
│ └─────────┘ │  │ └─────────┘ │  │ │ Handler │ │
└─────────────┘  └─────────────┘  │ └─────────┘ │
                                   │ ┌─────────┐ │
                                   │ │Timezone │ │
                                   │ └─────────┘ │
                                   └─────────────┘
```

## Architecture Layers

### 1. Presentation Layer (`src/bot/`)

**Responsibility**: Handle Telegram Bot API interactions

**Components**:
- [`bot.py`](../src/bot/bot.py): Bot initialization and lifecycle management
- [`handlers.py`](../src/bot/handlers.py): Message and callback handlers

**Key Features**:
- Receives user messages and commands
- Sends responses and notifications
- Manages inline keyboards
- Handles callback queries
- Provides user-facing error messages

**Communication**:
- **Inbound**: Telegram Bot API (webhooks/polling)
- **Outbound**: Business Logic Layer (service calls)

### 2. Business Logic Layer (`src/services/`)

**Responsibility**: Core application logic and orchestration

**Components**:
- [`schedule_manager.py`](../src/services/schedule_manager.py): CRUD operations for medication schedules
- [`scheduler.py`](../src/services/scheduler.py): Background reminder scheduler
- [`notification_manager.py`](../src/services/notification_manager.py): Notification logic and formatting

**Key Features**:
- Medication schedule management
- Reminder timing logic
- Notification formatting
- Business rule enforcement

**Communication**:
- **Inbound**: Presentation Layer
- **Outbound**: Data Layer, LLM Layer

### 3. LLM Integration Layer (`src/llm/`)

**Responsibility**: Natural language processing via Groq API

**Components**:
- [`client.py`](../src/llm/client.py): Groq API client with retry logic
- [`prompts.py`](../src/llm/prompts.py): LLM prompt templates

**Key Features**:
- Two-stage command processing
- Command type detection
- Parameter extraction
- Error handling and retries

**Communication**:
- **Inbound**: Business Logic Layer
- **Outbound**: Groq API (external)

### 4. Data Layer (`src/data/`)

**Responsibility**: Data persistence and models

**Components**:
- [`models.py`](../src/data/models.py): Data models (UserData, Medication)
- [`storage.py`](../src/data/storage.py): JSON file storage manager

**Key Features**:
- Atomic file writes
- Data validation
- Serialization/deserialization
- File-based persistence

**Communication**:
- **Inbound**: Business Logic Layer
- **Outbound**: File system

### 5. Infrastructure Layer (`src/utils/`, `src/config/`)

**Responsibility**: Cross-cutting concerns

**Components**:
- [`logger.py`](../src/utils/logger.py): Structured logging
- [`error_handler.py`](../src/utils/error_handler.py): Error formatting
- [`timezone.py`](../src/utils/timezone.py): Timezone utilities
- [`settings.py`](../src/config/settings.py): Configuration management

**Key Features**:
- Centralized logging
- Configuration loading
- Error formatting
- Timezone handling

## Component Descriptions

### Bot Initialization (`src/bot/bot.py`)

**Purpose**: Initialize and manage bot lifecycle

**Key Functions**:
```python
def init_bot() -> tuple[Bot, Dispatcher]:
    """Initialize bot and all services"""
    
async def on_startup():
    """Handler called when bot starts"""
    
async def on_shutdown():
    """Handler called when bot shuts down"""
```

**Initialization Flow**:
```
1. Load configuration from environment
2. Create Bot instance with token
3. Create Dispatcher for routing
4. Initialize DataManager
5. Initialize GroqClient
6. Initialize ScheduleManager
7. Initialize handlers with dependencies
8. Register router and lifecycle handlers
9. Return bot and dispatcher
```

### Message Handlers (`src/bot/handlers.py`)

**Purpose**: Process incoming messages and callbacks

**Handler Types**:

1. **Text Message Handler** (`handle_text_message`)
   - Entry point for all text messages
   - Checks if user exists (onboarding)
   - Delegates to LLM for command detection
   - Routes to specific command handlers

2. **Command Handlers**:
   - `handle_list_command`: Show medication schedule
   - `handle_add_command`: Add new medication
   - `handle_delete_command`: Delete medication
   - `handle_time_change_command`: Update medication time
   - `handle_dose_change_command`: Update dosage
   - `handle_timezone_change_command`: Update timezone
   - `handle_done_command`: Mark medication as taken
   - `handle_unknown_command`: Handle unrecognized input

3. **Callback Handler** (`handle_medication_taken_callback`)
   - Processes inline button clicks
   - Marks medication as taken
   - Updates message keyboard

**Processing Flow**:
```
User Message
    ↓
Check User Exists → No → Create User + Onboarding
    ↓ Yes
Detect Command Type (LLM Stage 1)
    ↓
Route to Specific Handler
    ↓
Process Command (LLM Stage 2 if needed)
    ↓
Update Data
    ↓
Send Response
```

### Schedule Manager (`src/services/schedule_manager.py`)

**Purpose**: CRUD operations for medication schedules

**Key Methods**:

```python
async def add_medication(user_id, name, times, dosage) -> list[Medication]:
    """Add medication(s) to schedule"""
    
async def delete_medications(user_id, medication_ids) -> bool:
    """Delete medication(s) by ID"""
    
async def update_medication_time(user_id, medication_id, new_times) -> list[Medication]:
    """Update medication time(s)"""
    
async def update_medication_dosage(user_id, medication_id, new_dosage) -> Medication:
    """Update medication dosage"""
    
async def mark_medication_taken(user_id, medication_id) -> None:
    """Mark medication as taken"""
    
async def get_user_schedule(user_id) -> list[Medication]:
    """Get user's medication schedule"""
    
def format_schedule_for_display(medications) -> str:
    """Format schedule for user display"""
```

**Business Rules**:
- Multiple times create separate medication entries
- Medications are identified by unique IDs
- Schedule is sorted by time for display
- Medications are grouped by name and dosage

### Reminder Scheduler (`src/services/scheduler.py`)

**Purpose**: Background task for sending reminders

**Architecture**:
```
Main Loop (every SCHEDULER_INTERVAL_SECONDS)
    ↓
Get All User Files
    ↓
For Each User:
    ↓
    Get Medications to Remind
    ↓
    Check Previous Reminders
    ↓
    Delete Old Reminders (if same medication)
    ↓
    Send New Reminder
    ↓
    Store Message ID
```

**Key Features**:
- Runs as background asyncio task
- Checks all users periodically
- Groups multiple medications in one message
- Handles Telegram API errors gracefully
- Supports graceful shutdown

**Reminder Logic**:
```python
def should_send_reminder(medication, user_timezone) -> bool:
    """
    Send reminder if:
    1. Current time matches medication time (±1 minute)
    2. Not already taken today
    3. No reminder sent in last REMINDER_REPEAT_INTERVAL_HOURS
    """
```

### Data Manager (`src/data/storage.py`)

**Purpose**: Manage user data persistence

**Storage Strategy**: File-based JSON storage
- One file per user: `data/users/{user_id}.json`
- Atomic writes using temp files
- Automatic corruption recovery

**Key Methods**:

```python
async def get_user_data(user_id) -> Optional[UserData]:
    """Load user data from JSON file"""
    
async def save_user_data(user_data) -> None:
    """Save user data with atomic write"""
    
async def create_user(user_id, timezone_offset) -> UserData:
    """Create new user file"""
    
def get_all_user_ids() -> list[int]:
    """Get list of all user IDs (for scheduler)"""
```

**Atomic Write Pattern**:
```
1. Write data to temporary file (.json.tmp)
2. Flush and sync to disk
3. Rename temp file to actual file (atomic operation)
4. Clean up temp file on error
```

**Benefits**:
- Prevents data corruption on crash
- Ensures data consistency
- Simple backup/restore

### LLM Client (`src/llm/client.py`)

**Purpose**: Interface with Groq API for NLP

**Two-Stage Processing**:

**Stage 1: Command Detection**
```python
async def detect_command_type(user_message) -> str:
    """
    Detect command type from user message
    Returns: add, delete, list, time_change, dose_change, 
             timezone_change, done, unknown
    """
```

**Stage 2: Parameter Extraction**
```python
async def process_add_command(user_message) -> dict:
    """Extract medication name, times, dosage"""
    
async def process_delete_command(user_message, schedule) -> dict:
    """Identify medications to delete"""
    
# ... other process_* methods
```

**Error Handling**:
- Automatic retries with exponential backoff
- Timeout handling
- Rate limit detection
- Insufficient funds detection
- JSON parsing validation

**Retry Logic**:
```
Attempt 1 → Fail → Wait 1s
Attempt 2 → Fail → Wait 2s
Attempt 3 → Fail → Wait 4s
Attempt 4 → Fail → Raise Error
```

## Data Flow

### Adding Medication Flow

```
User: "Добавь аспирин 200 мг в 10:00"
    ↓
[Handler] Receive message
    ↓
[Handler] Check user exists → Yes
    ↓
[LLM] Detect command type → "add"
    ↓
[Handler] Route to handle_add_command
    ↓
[LLM] Extract parameters:
    - medication_name: "аспирин"
    - times: ["10:00"]
    - dosage: "200 мг"
    ↓
[ScheduleManager] add_medication()
    ↓
[DataManager] Load user data
    ↓
[UserData] Add medication (generate ID)
    ↓
[DataManager] Save user data (atomic write)
    ↓
[Handler] Send response: "Добавлено: аспирин 200 мг в 10:00"
```

### Reminder Flow

```
[Scheduler] Timer triggers (every 60s)
    ↓
[Scheduler] Get all user IDs
    ↓
For each user:
    ↓
    [NotificationManager] Get medications to remind
        ↓
        [DataManager] Load user data
        ↓
        [NotificationManager] Check each medication:
            - Is it time? (current time ≈ medication time)
            - Not taken today?
            - No recent reminder?
        ↓
        Return list of medications
    ↓
    [Scheduler] Check previous reminders
        ↓
        If same medication name → Delete old reminder
    ↓
    [Scheduler] Format reminder message
    ↓
    [Scheduler] Create inline keyboard
    ↓
    [Bot] Send message to user
    ↓
    [Scheduler] Store message_id in medication
    ↓
    [DataManager] Save user data
```

### Callback Flow (Button Click)

```
User clicks "Принял ✓" button
    ↓
[Handler] Receive callback query
    ↓
[Handler] Parse callback_data → medication_id
    ↓
[DataManager] Load user data
    ↓
[Handler] Validate medication exists
    ↓
[Handler] Check not already taken today
    ↓
[ScheduleManager] mark_medication_taken()
    ↓
[Medication] Set last_taken = current_timestamp
    ↓
[DataManager] Save user data
    ↓
[Handler] Update message (remove button)
    ↓
[Handler] Send callback answer: "Отмечено ✓"
```

## Database Schema

### JSON File Structure

Each user has a JSON file: `data/users/{user_id}.json`

```json
{
  "user_id": 123456789,
  "timezone_offset": "+03:00",
  "medications": [
    {
      "id": 1,
      "name": "аспирин",
      "dosage": "200 мг",
      "time": "10:00",
      "last_taken": 1703750400,
      "reminder_message_id": 12345
    },
    {
      "id": 2,
      "name": "парацетамол",
      "dosage": null,
      "time": "18:00",
      "last_taken": null,
      "reminder_message_id": null
    }
  ]
}
```

### Data Models

**UserData**:
```python
@dataclass
class UserData:
    user_id: int                      # Telegram user ID
    timezone_offset: str              # e.g., "+03:00", "-05:00"
    medications: list[Medication]     # List of medications
```

**Medication**:
```python
@dataclass
class Medication:
    id: int                          # Unique ID (auto-increment per user)
    name: str                        # Medication name
    dosage: Optional[str]            # e.g., "200 мг", "2 таблетки"
    time: str                        # Time in "HH:MM" format (local)
    last_taken: Optional[int]        # Unix timestamp of last intake
    reminder_message_id: Optional[int]  # Telegram message ID of reminder
```

### Data Relationships

```
UserData (1) ──────── (N) Medication
    │
    └─ user_id (PK)
    └─ timezone_offset
    
Medication
    └─ id (PK within user)
    └─ name
    └─ dosage
    └─ time
    └─ last_taken (timestamp)
    └─ reminder_message_id (FK to Telegram message)
```

## LLM Integration

### Two-Stage Processing Pipeline

**Why Two Stages?**
1. **Efficiency**: Quick command type detection
2. **Context**: Stage 2 can use current schedule
3. **Clarity**: Separate concerns (what vs. how)
4. **Error Handling**: Better error messages

### Stage 1: Command Detection

**Input**: User message (raw text)

**Output**: Command type string

**Prompt Strategy**:
```python
"""
Определи тип команды пользователя.
Возможные типы:
- add: добавить медикамент
- delete: удалить медикамент
- list: показать расписание
- time_change: изменить время приема
- dose_change: изменить дозировку
- timezone_change: изменить часовой пояс
- done: отметить прием
- unknown: неизвестная команда

Сообщение: "{user_message}"

Ответ в JSON: {{"command_type": "..."}}
"""
```

**Examples**:
- "Добавь аспирин" → `{"command_type": "add"}`
- "Что я принимаю?" → `{"command_type": "list"}`
- "Удали парацетамол" → `{"command_type": "delete"}`

### Stage 2: Parameter Extraction

**Input**: User message + context (schedule if needed)

**Output**: Structured data (JSON)

**Example for Add Command**:

**Prompt**:
```python
"""
Извлеки информацию о медикаменте из сообщения.
Сообщение: "{user_message}"

Извлеки:
- medication_name: название медикамента
- times: список времен в формате HH:MM
- dosage: дозировка (если указана)

Ответ в JSON:
{{
  "medication_name": "...",
  "times": ["HH:MM", ...],
  "dosage": "..." или null
}}
"""
```

**Example**:
- Input: "Добавь аспирин 200 мг в 10:00 и 18:00"
- Output:
```json
{
  "medication_name": "аспирин",
  "times": ["10:00", "18:00"],
  "dosage": "200 мг"
}
```

### Clarification Handling

Some commands may need clarification:

**Example for Delete Command**:

If user says "удали лекарство" but has multiple medications:

**Output**:
```json
{
  "status": "clarification_needed",
  "message": "У вас несколько медикаментов. Уточните, какой именно удалить: аспирин, парацетамол, витамин D?"
}
```

### Error Handling

**Timeout Errors**:
- Retry with exponential backoff
- Max 3 retries
- User-friendly error message

**Rate Limit Errors**:
- Immediate failure (no retry)
- Inform user to try again later

**Insufficient Funds**:
- Immediate failure
- Alert administrator

**JSON Parse Errors**:
- Log full response
- Return generic error to user

## Scheduler Logic

### Timing Algorithm

**Check Interval**: Every 60 seconds (configurable)

**Reminder Decision**:
```python
def should_send_reminder(medication, current_time, user_timezone):
    # Convert times to user's timezone
    med_time = parse_time(medication.time, user_timezone)
    curr_time = current_time.astimezone(user_timezone)
    
    # Check if times match (within 1 minute)
    if abs(med_time - curr_time) > 1 minute:
        return False
    
    # Check if already taken today
    if medication.last_taken:
        last_taken_date = datetime.fromtimestamp(medication.last_taken).date()
        if last_taken_date == today:
            return False
    
    # Check if reminder already sent recently
    if medication.reminder_message_id:
        # Check if reminder was sent in last REMINDER_REPEAT_INTERVAL_HOURS
        # (Implementation in NotificationManager)
        pass
    
    return True
```

### Grouping Logic

Multiple medications at the same time are grouped:

```
Instead of:
  Message 1: "Время принять аспирин 200 мг"
  Message 2: "Время принять парацетамол"

Send:
  Message 1: "Время принять медикаменты:
              • аспирин 200 мг
              • парацетамол"
```

### Previous Reminder Handling

**Business Rule**: If same medication (by name) time comes again, delete previous reminder and consider it taken.

**Implementation**:
```python
async def _handle_previous_reminders(user_id, medications):
    for medication in medications:
        # Find previous reminder for same medication name
        message_id = await notification_manager.should_delete_previous_reminder(
            user_id, medication.name, medication.id
        )
        
        if message_id:
            # Delete old reminder message
            await bot.delete_message(user_id, message_id)
            
            # Mark old medication as taken
            await schedule_manager.mark_medication_taken(user_id, old_med_id)
```

### Repeat Reminders

If user doesn't respond to reminder:
- Send repeat reminder after REMINDER_REPEAT_INTERVAL_HOURS
- Keep sending until medication is marked as taken
- Or until end of day (midnight)

## Error Handling Strategy

### Error Categories

1. **User Errors**: Invalid input, missing data
2. **System Errors**: File I/O, network issues
3. **External Errors**: Telegram API, Groq API
4. **Data Errors**: Corruption, validation failures

### Error Handling Layers

**Layer 1: Try-Catch at Operation Level**
```python
try:
    result = await operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    # Handle or re-raise
```

**Layer 2: Service-Level Error Handling**
```python
async def add_medication(...):
    try:
        # Business logic
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise  # Re-raise for handler
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
```

**Layer 3: Handler-Level Error Handling**
```python
async def handle_add_command(...):
    try:
        await schedule_manager.add_medication(...)
    except GroqAPIError as e:
        await message.answer(format_error_for_user(e))
    except Exception as e:
        logger.error(f"Handler error: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")
```

### User-Facing Error Messages

**Principle**: Never show technical details to users

**Implementation**:
```python
def format_error_for_user(error: Exception) -> str:
    if isinstance(error, GroqTimeoutError):
        return "Сервис временно недоступен. Попробуйте через минуту."
    elif isinstance(error, GroqInsufficientFundsError):
        return "Сервис временно недоступен. Мы работаем над решением."
    elif isinstance(error, ValueError):
        return str(error)  # Validation errors are user-friendly
    else:
        return "Произошла ошибка. Попробуйте еще раз."
```

### Logging Strategy

**Structured Logging**:
```python
logger.error(
    f"Error processing command: {type(e).__name__}: {e}",
    exc_info=True,
    extra={
        "user_id": user_id,
        "command_type": command_type,
        "message_text": message_text[:100]
    }
)
```

**Log Levels**:
- `DEBUG`: Detailed flow information
- `INFO`: Important events (user actions, reminders sent)
- `WARNING`: Recoverable errors (API timeouts, retries)
- `ERROR`: Unrecoverable errors (data corruption, API failures)

## Design Patterns

### 1. Dependency Injection

Services are injected into handlers:

```python
def init_handlers(dm: DataManager, sm: ScheduleManager, gc: GroqClient):
    global data_manager, schedule_manager, groq_client
    data_manager = dm
    schedule_manager = sm
    groq_client = gc
```

**Benefits**:
- Testability (can inject mocks)
- Loose coupling
- Clear dependencies

### 2. Repository Pattern

DataManager acts as repository:

```python
class DataManager:
    async def get_user_data(user_id) -> UserData:
        """Abstract storage details"""
    
    async def save_user_data(user_data) -> None:
        """Abstract storage details"""
```

**Benefits**:
- Storage implementation can change
- Easy to add caching
- Testable with in-memory storage

### 3. Strategy Pattern

LLM processing uses strategy pattern:

```python
# Different strategies for different command types
await groq_client.process_add_command(message)
await groq_client.process_delete_command(message, schedule)
await groq_client.process_time_change_command(message, schedule)
```

### 4. Template Method Pattern

Scheduler loop follows template:

```python
async def _scheduler_loop(self):
    while self._running:
        try:
            await self.check_and_send_reminders()  # Template method
        except Exception as e:
            logger.error(f"Error: {e}")
        await asyncio.sleep(interval)
```

### 5. Singleton Pattern

Bot instance is singleton:

```python
bot: Optional[Bot] = None

def init_bot() -> Bot:
    global bot
    if bot is None:
        bot = Bot(token=...)
    return bot
```

## Scalability Considerations

### Current Limitations

1. **File-based storage**: Not suitable for >10,000 users
2. **Single process**: No horizontal scaling
3. **In-memory state**: Lost on restart
4. **Polling**: Less efficient than webhooks

### Scaling Strategies

**For 100-1,000 users** (Current):
- File-based storage is sufficient
- Single process handles load
- Polling is acceptable

**For 1,000-10,000 users**:
- Consider SQLite database
- Add connection pooling
- Implement caching layer
- Switch to webhooks

**For 10,000+ users**:
- PostgreSQL database
- Multiple worker processes
- Redis for caching and queues
- Load balancer
- Separate scheduler service

### Performance Optimizations

**Current**:
- Async I/O for non-blocking operations
- Batch processing in scheduler
- Efficient JSON serialization

**Future**:
- Database indexes on user_id, medication.time
- Caching frequently accessed data
- Connection pooling
- Message queuing for reminders

### Monitoring

**Metrics to Track**:
- Response time (handler → response)
- LLM API latency
- Scheduler cycle time
- Error rates by type
- Active users
- Reminders sent per hour

**Tools**:
- Prometheus for metrics
- Grafana for dashboards
- Sentry for error tracking
- ELK stack for log analysis

## Security Considerations

### Data Protection

- User data stored locally (no cloud)
- File permissions: 600 (owner read/write only)
- No sensitive data in logs
- API keys in environment variables

### API Security

- Rate limiting on Groq API
- Timeout protection
- Retry limits
- Error message sanitization

### Bot Security

- Input validation
- No command injection
- Sanitized error messages
- User isolation (separate files)

## Future Enhancements

### Planned Features

1. **Database Migration**: SQLite → PostgreSQL
2. **Web Dashboard**: Admin interface
3. **Analytics**: Usage statistics, adherence tracking
4. **Multi-language**: Support English, other languages
5. **Voice Commands**: Telegram voice message support
6. **Medication Database**: Drug interaction warnings
7. **Reminders History**: Track adherence over time
8. **Family Accounts**: Manage medications for family members

### Technical Improvements

1. **Testing**: Unit tests, integration tests
2. **CI/CD**: Automated testing and deployment
3. **Monitoring**: Prometheus + Grafana
4. **Caching**: Redis for frequently accessed data
5. **Webhooks**: Replace polling for better performance
6. **Containerization**: Docker Compose for easy deployment
7. **Documentation**: API docs with Swagger/OpenAPI

## Conclusion

The Medication Bot architecture is designed for:
- **Maintainability**: Clear separation of concerns
- **Reliability**: Comprehensive error handling
- **Scalability**: Can grow with user base
- **Extensibility**: Easy to add new features

The layered architecture and design patterns ensure the codebase remains clean and manageable as the project evolves.
