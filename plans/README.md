# Medication Reminder Bot - Architecture and Implementation Plan

## Overview

This directory contains comprehensive architecture and implementation documentation for a Telegram medication reminder bot built with Python, SQLite, and LLM-powered natural language processing.

## Documents

### 1. [`architecture.md`](architecture.md)
**Complete system architecture document**

Contents:
- System overview and core principles
- Technology stack
- High-level component diagrams
- Module structure (7 modules)
- Database schema (SQLite with 3 tables)
- Data flow diagrams
- Command processing workflows
- Fault tolerance and recovery mechanisms
- API integration specifications
- Security and performance considerations
- Testing strategy
- Implementation phases (3 weeks)

Key highlights:
- Two-stage LLM pipeline (classifier → parser)
- Stateless fault-tolerant notification system
- Deduplication by design (medication key = name + time)
- Natural language interface (no traditional menus)
- Comprehensive Mermaid diagrams for visualization

### 2. [`implementation_guide.md`](implementation_guide.md)
**Step-by-step implementation instructions**

Contents:
- Complete file structure
- Implementation order (9 steps)
- Detailed code examples for each module
- Database schema with SQL scripts
- Testing strategy (unit, integration, LLM tests)
- Deployment checklist
- Development tips
- Common issues and solutions
- Performance optimization techniques

Provides:
- Ready-to-use code snippets
- Testing approaches
- Troubleshooting guide
- Best practices

## Quick Start

1. **Review Architecture**: Read [`architecture.md`](architecture.md) to understand system design
2. **Follow Implementation**: Use [`implementation_guide.md`](implementation_guide.md) for step-by-step coding
3. **Adapt as Needed**: Modify based on your specific requirements

## Key Architecture Decisions

### Two-Stage LLM Processing
```
User Message → Classifier LLM → Intent → Parser LLM → Parameters → Business Logic
```

Benefits:
- Clear separation of concerns
- Easier prompt optimization
- Better error handling
- Context-aware parameter extraction

### Database Schema

**Users Table**:
- `user_id` (PK)
- `timezone_offset`
- `created_at`, `updated_at`

**Medications Table**:
- `id` (PK)
- `user_id` (FK)
- `name`, `dosage`, `time`
- **UNIQUE constraint**: `(user_id, name, time)` for deduplication

**Intake Status Table**:
- `id` (PK)
- `user_id` (FK)
- `medication_id` (FK)
- `date`, `taken_at`, `reminder_message_id`
- **UNIQUE constraint**: `(user_id, medication_id, date)` for daily tracking

### Module Structure

```
src/
├── main.py              # Entry point
├── settings.py          # Configuration
├── database.py          # SQLite operations
├── llm_client.py        # Groq API adapter
├── llm_processor.py     # Two-stage LLM pipeline
├── prompts.py           # All LLM prompts (reused from src_old)
├── telegram_bot.py      # Telegram integration
├── scheduler.py         # Notification system
└── timezone_utils.py    # Timezone calculations
```

### Notification Logic

**Daily Cycle**:
1. At medication time: Send notification with "Принял" button
2. If not taken: Hourly reminders until taken
3. Multi-dose handling: Auto-mark first dose when second dose time arrives
4. Next day: Reset cycle

**Fault Tolerance**:
- After restart: Check database for missed notifications
- Send missed notifications with "(пропущено)" marker
- Resume normal operation from current point
- No reliance on in-memory state

### Command Types

| Command | Classifier | Parser | Example |
|---------|-----------|---------|---------|
| **add** | Recognize add intent | Extract name, time(s), dosage | "я принимаю аспирин в 19:00" |
| **done** | Recognize done intent | Match medication by name/time | "я принял аспирин" |
| **delete** | Recognize delete intent | Identify medications to remove | "удали аспирин" |
| **time_change** | Recognize time change | Extract medication and new time | "измени время аспирина на 20:00" |
| **dose_change** | Recognize dose change | Extract medication and new dose | "измени дозировку аспирина на 300 мг" |
| **timezone_change** | Recognize timezone change | Parse timezone from city/offset | "моя часовая зона Москва" |
| **list** | Recognize list intent | Hard logic (no LLM) | "что я принимаю" |
| **help** | Recognize help intent | Predefined message (no LLM) | "помощь" |
| **unknown** | Default fallback | "Не понял" message | Any unrecognized input |

## Implementation Timeline

### Week 1: Foundation
- Settings, database, timezone utilities
- Basic Telegram bot setup
- LLM client and prompts

### Week 2: Core Features
- LLM processor (two-stage pipeline)
- Command handlers (add, delete, done, etc.)
- Notification scheduler
- Hourly reminders

### Week 3: Polish
- Multi-dose medication logic
- Fault tolerance and recovery
- Testing (unit, integration, LLM)
- Bug fixes and edge cases

## Technologies

- **Python 3.11+**: Modern async/await syntax
- **aiogram 3.15**: Telegram Bot framework
- **SQLite3**: Embedded database
- **aiosqlite**: Async SQLite driver
- **Groq API**: LLM provider (OpenAI-compatible)
- **httpx**: Async HTTP client
- **python-dotenv**: Environment configuration
- **loguru**: Structured logging
- **pytest**: Testing framework

## Design Principles

1. **Simplicity**: No excessive OOP, one module = one file
2. **Statelessness**: Database as source of truth, no in-memory state
3. **Natural Language**: Users communicate naturally, not with commands
4. **Fault Tolerance**: Recovers gracefully from downtime
5. **Deduplication**: Hard logic enforces uniqueness (name + time)
6. **Pragmatism**: Not enterprise-grade, suitable for personal use

## Testing Approach

### Unit Tests
- Database CRUD operations
- Timezone calculations
- LLM response parsing

### Integration Tests
- Full command flows
- Notification scheduling
- Recovery scenarios
- Multi-dose logic

### LLM Tests
- Intent classification accuracy (>95% target)
- Parameter extraction correctness
- Edge case handling (ambiguous inputs)

Reuse existing tests in `/tests/integration/` as baseline.

## Security Notes

- **API Keys**: Store in `.env`, never commit
- **SQL Injection**: Always use parameterized queries
- **Input Validation**: Validate time format, timezone offset
- **User Privacy**: No data sharing between users
- **Telegram Security**: Use HTTPS webhook (optional, polling is simpler)

## Performance Considerations

### Database
- Indexes on `(user_id, time)` and `(user_id, date)`
- WAL mode for better concurrency
- Connection pooling with aiosqlite

### LLM
- Retry with exponential backoff
- Timeout handling (30 seconds default)
- Temperature tuning (0.3-0.5 for classification)

### Telegram
- Handle rate limits gracefully
- Batch notifications when possible
- Efficient message editing (not re-sending)

## Next Steps

1. **Read** [`architecture.md`](architecture.md) for complete system design
2. **Follow** [`implementation_guide.md`](implementation_guide.md) step-by-step
3. **Test** each module as you implement it
4. **Iterate** on prompts based on real usage
5. **Deploy** to production with monitoring

## Questions?

Review the documents for detailed explanations. If you need clarification on any aspect, refer to:
- **Architecture details**: [`architecture.md`](architecture.md)
- **Implementation steps**: [`implementation_guide.md`](implementation_guide.md)
- **Existing code examples**: `/src_old/` (prompts can be reused)
- **Test patterns**: `/tests/integration/`

---

**Status**: Architecture and implementation plan complete, ready for implementation phase.

**Recommended Next Action**: Switch to Code mode to start implementing the modules following the implementation guide.
