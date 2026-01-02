# Medical Bot Test Suite

This directory contains the comprehensive test suite for the Medical Bot application.

## Test Structure

```
tests/
├── __init__.py                          # Test package init
├── conftest.py                          # Shared fixtures
├── pytest.ini                           # Pytest configuration (in project root)
├── fixtures/                            # Test data and fixtures
│   ├── __init__.py
│   └── user_data_samples.py            # Sample user data constants
├── unit/                                # Unit tests
│   ├── __init__.py
│   ├── test_llm_client.py              # LLM client tests (16 tests)
│   ├── test_data_storage.py            # Data storage tests (10+ tests)
│   └── test_notification_manager.py    # Notification manager tests (10+ tests)
└── integration/                         # Integration tests
    ├── __init__.py
    ├── test_notification_flow.py       # Notification flow tests (7+ tests)
    └── test_add_medication_flow.py     # End-to-end flow tests (7+ tests)
```

## Setup

### 1. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install all dependencies including test dependencies
pip install -r requirements.txt
```

Or install test dependencies separately:

```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov freezegun faker
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_llm_client.py

# Run specific test
pytest tests/unit/test_llm_client.py::test_detect_add_command
```

### Run with Coverage

```bash
# Run tests with coverage report
pytest --cov=src --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Run with Verbose Output

```bash
# Verbose output
pytest -v

# Very verbose with print statements
pytest -vv -s

# Show local variables in tracebacks
pytest -l
```

### Run Specific Markers

```bash
# Run only unit tests (if marked)
pytest -m unit

# Run only integration tests (if marked)
pytest -m integration

# Run only slow tests (if marked)
pytest -m slow
```

## Test Coverage

The test suite provides comprehensive coverage of:

### 1. LLM Response Processing (16+ tests)
- **TC-LLM-001 to TC-LLM-011**: Command detection and parameter extraction
  - Add medication commands (single/multiple times/medications)
  - Delete medication commands
  - Time change commands
  - Dose change commands
  - Timezone change commands
  - Done commands
- **TC-LLM-ERR-001 to TC-LLM-ERR-005**: Error handling
  - Timeout errors
  - Rate limit errors
  - Insufficient funds errors
  - Invalid JSON responses
  - Retry logic

### 2. Data Storage (10+ tests)
- **TC-STORAGE-001 to TC-STORAGE-010**: File operations
  - Create new user
  - Load existing user
  - Atomic write success
  - Atomic write failure recovery
  - Corrupted file recovery
  - Add/delete/update medication file updates
  - Mark taken updates file
  - Concurrent write safety

### 3. Notification Manager (10+ tests)
- **TC-NOTIF-001 to TC-NOTIF-010**: Notification logic
  - Get medications to remind
  - Should send reminder checks
  - Format reminder messages
  - Create reminder keyboards
  - Set/clear reminder message IDs
  - Delete previous reminders

### 4. Notification Flow Integration (7+ tests)
- **TC-NOTIF-INT-001 to TC-NOTIF-INT-007**: End-to-end notification flow
  - Complete reminder flow
  - Multiple medications grouped
  - Previous reminder deletion
  - Callback button handling
  - Timezone handling
  - No reminder if already taken
  - Repeat reminders

### 5. Add Medication Flow (7+ tests)
- **TC-INT-001**: Complete add medication flow
- Additional flows for:
  - Multiple medications
  - Multiple times
  - Delete medication
  - Time change
  - Dose change
  - List medications

## Test Fixtures

### Shared Fixtures (conftest.py)

- `temp_data_dir`: Temporary directory for test data
- `data_manager`: DataManager instance with temp directory
- `schedule_manager`: ScheduleManager instance
- `notification_manager`: NotificationManager instance
- `mock_groq_client`: Mocked LLM client
- `mock_bot`: Mocked Telegram Bot
- `mock_message`: Mocked Telegram Message
- `mock_callback_query`: Mocked Telegram CallbackQuery

### Sample Data (fixtures/user_data_samples.py)

- `SAMPLE_USER_EMPTY`: User with no medications
- `SAMPLE_USER_SINGLE_MED`: User with single medication
- `SAMPLE_USER_WITH_MEDS`: User with multiple medications
- `SAMPLE_USER_MED_TAKEN`: User with medication taken today
- `SAMPLE_USER_WITH_REMINDER`: User with reminder sent
- `SAMPLE_USER_SAME_TIME`: Multiple medications at same time
- `SAMPLE_USER_SAME_MED_DIFF_TIMES`: Same medication at different times

## Writing New Tests

### Unit Test Example

```python
import pytest

@pytest.mark.asyncio
async def test_my_feature(data_manager):
    """Test description."""
    # Given: Setup test data
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # When: Execute the feature
    result = await my_feature(user_id)
    
    # Then: Verify the result
    assert result is not None
```

### Integration Test Example

```python
import pytest
from freezegun import freeze_time

@pytest.mark.asyncio
@freeze_time("2024-01-01 10:00:00")
async def test_my_integration(scheduler, data_manager, mock_bot):
    """Test integration flow."""
    # Given: Setup complete scenario
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # When: Execute the flow
    await scheduler.check_and_send_reminders()
    
    # Then: Verify end-to-end behavior
    assert mock_bot.send_message.called
```

## Continuous Integration

The test suite is designed to run in CI/CD pipelines. Example GitHub Actions workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Troubleshooting

### Import Errors

If you get import errors, make sure:
1. You're in the project root directory
2. The virtual environment is activated
3. All dependencies are installed

### Async Test Errors

If async tests fail, ensure:
1. `pytest-asyncio` is installed
2. Tests are marked with `@pytest.mark.asyncio`
3. `asyncio_mode = auto` is set in pytest.ini

### Fixture Not Found

If fixtures are not found:
1. Check that `conftest.py` is in the tests directory
2. Verify the fixture name matches the parameter name
3. Ensure pytest can discover the conftest.py file

## Coverage Goals

- **Overall Coverage**: > 80%
- **Critical Paths**: > 95%
  - LLM response processing
  - File write operations
  - Notification scheduling

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain or improve coverage
4. Update this README if needed

## Test Execution Time

Approximate execution times:
- Unit tests: ~5-10 seconds
- Integration tests: ~10-20 seconds
- Full suite: ~15-30 seconds

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [freezegun documentation](https://github.com/spulec/freezegun)
- [Testing Strategy Document](../plans/testing_strategy.md)
