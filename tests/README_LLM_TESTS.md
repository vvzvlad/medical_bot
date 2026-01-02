# LLM Message Recognition Test Suite

This comprehensive test suite verifies that the LLM (Language Model) correctly recognizes and processes user messages, comparing actual LLM responses against expected JSON outputs. The tests are designed to ensure the medication bot properly handles Russian language user inputs for medication management.

## Test Files Overview

### 1. `test_llm_message_recognition.py`
**Purpose**: Core LLM message recognition tests with mocked responses
**Coverage**: 
- Command type detection (add, delete, done, list, time_change, unknown)
- Parameter extraction from natural language
- Confirmation message generation
- Error handling and edge cases

### 2. `test_llm_heroine_scenario.py`
**Purpose**: Specific tests for the user scenario "принял героин в 15"
**Coverage**:
- Exact phrase recognition
- Parameter extraction for the specific scenario
- Confirmation message generation for heroine
- Variations of the phrase
- Edge cases and error handling

### 3. `test_llm_real_responses.py`
**Purpose**: Integration tests with real LLM API calls
**Coverage**:
- Real API command detection
- Real parameter extraction
- Real confirmation message generation
- JSON response validation
- Consistency testing across multiple calls

### 4. `conftest.py`
**Purpose**: Shared fixtures and test configuration
**Coverage**:
- Mock objects setup
- Test data generators
- Utility functions
- Russian language processing helpers

## Test Categories

### Command Type Detection Tests
```python
# Test that LLM correctly identifies command types
test_cases = [
    "я принимаю аспирин в 10:00" -> "add"
    "удали аспирин" -> "delete" 
    "принял героин в 15" -> "done"
    "что я принимаю?" -> "list"
    "аспирин теперь в 11:00" -> "time_change"
    "какая погода?" -> "unknown"
]
```

### Parameter Extraction Tests
```python
# Test that LLM extracts medication parameters correctly
expected_response = {
    "medication_name": "аспирин",
    "times": ["10:00"],
    "dosage": "200 мг"
}
```

### Confirmation Message Tests
```python
# Test that LLM generates appropriate confirmation messages
expected_response = {
    "message": "Отмечено: аспирин (200 мг) принят в 10:00 ✓"
}
```

### Real API Tests
Tests that make actual API calls to verify real-world behavior (skipped if `GROQ_API_KEY` not set).

## Running the Tests

### Run all LLM tests
```bash
source .venv/bin/activate
python -m pytest tests/test_llm_message_recognition.py tests/test_llm_heroine_scenario.py -v
```

### Run specific test file
```bash
python -m pytest tests/test_llm_message_recognition.py -v
```

### Run tests with real API (requires GROQ_API_KEY)
```bash
export GROQ_API_KEY="your_api_key_here"
python -m pytest tests/test_llm_real_responses.py -v
```

### Run specific test scenario
```bash
python -m pytest tests/test_llm_heroine_scenario.py::TestHeroineScenarioDetection::test_detect_done_command_heroine_fifteen -v
```

## Test Structure

### Mock Tests
- Use `MagicMock` to simulate LLM responses
- Fast execution
- Predictable results
- Good for development and CI/CD

### Real API Tests
- Make actual calls to Groq API
- Verify real-world behavior
- Slower execution
- Require API key
- Good for validation and debugging

## Expected JSON Formats

### Command Detection Response
```json
{
    "command_type": "add|delete|done|list|time_change|unknown"
}
```

### Add Command Response
```json
[
    {
        "medication_name": "string",
        "times": ["HH:MM"],
        "dosage": "string"
    }
]
```

### Done Command Response
```json
{
    "medication_name": "string",
    "time": "HH:MM",
    "medication_ids": [1, 2, 3]
}
```

### Confirmation Message Response
```json
{
    "message": "string with confirmation text and ✓ indicator"
}
```

## Russian Language Support

The tests include comprehensive Russian language processing:
- Cyrillic character handling
- Natural language variations
- Case sensitivity
- Confirmation indicators (принят, отмечено, ✓)
- Time format recognition (15:00, 15, 3 часа дня)

## Error Handling

Tests cover various error scenarios:
- JSON decode errors
- Empty responses
- Missing fields
- API timeouts
- Invalid responses

## Integration with Existing Tests

The new LLM tests integrate with existing test infrastructure:
- Use same pytest configuration
- Share fixtures when possible
- Follow existing naming conventions
- Compatible with CI/CD pipeline

## Key Features Verified

1. **Message Recognition**: LLM correctly identifies user intent
2. **Parameter Extraction**: LLM extracts medication name, time, and dosage
3. **JSON Validation**: Responses match expected structure
4. **Russian Language**: Proper handling of Cyrillic text
5. **Edge Cases**: Graceful handling of errors and unusual inputs
6. **Real API Integration**: Tests work with actual LLM API when available

## Test Data

Sample test messages for different scenarios:
- "принял героин в 15" (the specific user case)
- "я принимаю аспирин в 10:00"
- "добавь парацетамол 400 мг в 18:00"
- "удали аспирин"
- "что я принимаю?"

## Maintenance

When modifying LLM prompts or adding new features:
1. Update the expected JSON formats if needed
2. Add new test cases for new scenarios
3. Run both mock and real API tests
4. Verify Russian language handling
5. Test edge cases and error conditions