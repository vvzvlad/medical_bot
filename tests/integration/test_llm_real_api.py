"""Integration tests with real Groq LLM API calls.

These tests make actual API calls to Groq LLM to verify real-world behavior.
They are marked with @pytest.mark.llm_real and can be skipped with:
    pytest -m "not llm_real"

Requirements:
- GROQ_API_KEY must be set in .env file
- Tests will be skipped if API key is not available
- Each test has a timeout to prevent hanging
"""

import os
from typing import Any, Dict, List

import pytest

from src.llm.client import GroqClient, GroqAPIError


# Skip all tests in this module if GROQ_API_KEY is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set - skipping real API tests"
)


# ============================================================================
# GROUP 1: Command Type Detection (5 tests)
# ============================================================================


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_detect_add_command(real_groq_client):
    """Test real LLM detection of add medication command.
    
    Verifies that the LLM correctly identifies a simple add command
    with medication name and time.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: User message to add medication
    user_message = "Добавь аспирин в 10:00"
    
    # When: Detect command type via real LLM
    command_type = await real_groq_client.detect_command_type(user_message)
    
    # Then: Should detect as add command
    assert command_type == "add", f"Expected 'add', got '{command_type}'"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_detect_delete_command(real_groq_client):
    """Test real LLM detection of delete medication command.
    
    Verifies that the LLM correctly identifies a delete command.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: User message to delete medication
    user_message = "Удали парацетамол"
    
    # When: Detect command type via real LLM
    command_type = await real_groq_client.detect_command_type(user_message)
    
    # Then: Should detect as delete command
    assert command_type == "delete", f"Expected 'delete', got '{command_type}'"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_detect_list_command(real_groq_client):
    """Test real LLM detection of list medications command.
    
    Verifies that the LLM correctly identifies a list/show command.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: User message to list medications
    user_message = "Что я принимаю?"
    
    # When: Detect command type via real LLM
    command_type = await real_groq_client.detect_command_type(user_message)
    
    # Then: Should detect as list command
    assert command_type == "list", f"Expected 'list', got '{command_type}'"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_detect_time_change_command(real_groq_client):
    """Test real LLM detection of time change command.
    
    Verifies that the LLM correctly identifies a command to change
    medication intake time.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: User message to change medication time
    user_message = "Аспирин теперь в 11:00"
    
    # When: Detect command type via real LLM
    command_type = await real_groq_client.detect_command_type(user_message)
    
    # Then: Should detect as time_change command
    assert command_type == "time_change", f"Expected 'time_change', got '{command_type}'"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_detect_timezone_command(real_groq_client):
    """Test real LLM detection of timezone change command.
    
    Verifies that the LLM correctly identifies a timezone change command.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: User message to change timezone
    user_message = "Моя часовая зона Москва"
    
    # When: Detect command type via real LLM
    command_type = await real_groq_client.detect_command_type(user_message)
    
    # Then: Should detect as timezone_change command
    assert command_type == "timezone_change", f"Expected 'timezone_change', got '{command_type}'"


# ============================================================================
# GROUP 2: Parameter Extraction (5 tests)
# ============================================================================


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_add_single_medication(real_groq_client):
    """Test real LLM extraction of single medication parameters.
    
    Verifies that the LLM correctly extracts medication name, time,
    and dosage from a simple add command.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: User message with medication, time, and dosage
    user_message = "Добавь аспирин в 10:00, дозировка 200 мг"
    
    # When: Process add command via real LLM
    result = await real_groq_client.process_add_command(user_message)
    
    # Then: Should extract all parameters correctly
    # Note: API may return dict or list, handle both
    if isinstance(result, dict):
        medication = result
    elif isinstance(result, list):
        assert len(result) == 1, f"Expected 1 medication, got {len(result)}"
        medication = result[0]
    else:
        raise AssertionError(f"Result should be dict or list, got {type(result)}")
    assert "medication_name" in medication, "Missing medication_name"
    assert "times" in medication, "Missing times"
    assert "dosage" in medication, "Missing dosage"
    
    # Verify extracted values (case-insensitive for medication name)
    assert "аспирин" in medication["medication_name"].lower(), \
        f"Expected 'аспирин' in name, got '{medication['medication_name']}'"
    assert "10:00" in medication["times"], \
        f"Expected '10:00' in times, got {medication['times']}"
    assert "200" in medication["dosage"], \
        f"Expected '200' in dosage, got '{medication['dosage']}'"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_add_multiple_times(real_groq_client):
    """Test real LLM extraction of medication with multiple intake times.
    
    Verifies that the LLM correctly extracts multiple times for a
    single medication.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: User message with medication and multiple times
    user_message = "Добавь парацетамол в 9:00, 14:00 и 21:00"
    
    # When: Process add command via real LLM
    result = await real_groq_client.process_add_command(user_message)
    
    # Then: Should extract medication with all times
    # Note: API may return dict or list, handle both
    if isinstance(result, dict):
        medication = result
    elif isinstance(result, list):
        assert len(result) >= 1, "Should have at least 1 medication"
        medication = result[0]
    else:
        raise AssertionError(f"Result should be dict or list, got {type(result)}")
    assert "medication_name" in medication, "Missing medication_name"
    assert "times" in medication, "Missing times"
    assert "парацетамол" in medication["medication_name"].lower(), \
        f"Expected 'парацетамол' in name, got '{medication['medication_name']}'"
    
    # Should have 3 times
    times = medication["times"]
    assert len(times) == 3, f"Expected 3 times, got {len(times)}: {times}"
    assert "09:00" in times or "9:00" in times, f"Expected '09:00' in times, got {times}"
    assert "14:00" in times, f"Expected '14:00' in times, got {times}"
    assert "21:00" in times, f"Expected '21:00' in times, got {times}"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_add_without_dosage(real_groq_client):
    """Test real LLM extraction of medication without dosage.
    
    Verifies that the LLM correctly handles medications added without
    specifying dosage.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: User message without dosage
    user_message = "Добавь витамин D в 12:00"
    
    # When: Process add command via real LLM
    result = await real_groq_client.process_add_command(user_message)
    
    # Then: Should extract medication and time, dosage may be null/empty
    # Note: API may return dict or list, handle both
    if isinstance(result, dict):
        medication = result
    elif isinstance(result, list):
        assert len(result) == 1, f"Expected 1 medication, got {len(result)}"
        medication = result[0]
    else:
        raise AssertionError(f"Result should be dict or list, got {type(result)}")
    assert "medication_name" in medication, "Missing medication_name"
    assert "times" in medication, "Missing times"
    assert "витамин" in medication["medication_name"].lower(), \
        f"Expected 'витамин' in name, got '{medication['medication_name']}'"
    assert "12:00" in medication["times"], \
        f"Expected '12:00' in times, got {medication['times']}"
    
    # Dosage should be null, empty, or not present
    dosage = medication.get("dosage")
    assert dosage is None or dosage == "" or dosage == "не указано", \
        f"Expected null/empty dosage, got '{dosage}'"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_delete_specific_medication(real_groq_client):
    """Test real LLM extraction of specific medication to delete.
    
    Verifies that the LLM correctly identifies which medication to delete
    from the schedule.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: User message to delete specific medication
    user_message = "Удали аспирин"
    schedule = [
        {"id": 1, "name": "Аспирин", "time": "10:00", "dosage": "200 мг"},
        {"id": 2, "name": "Парацетамол", "time": "14:00", "dosage": "500 мг"}
    ]
    
    # When: Process delete command via real LLM
    result = await real_groq_client.process_delete_command(user_message, schedule)
    
    # Then: Should identify correct medication to delete
    assert isinstance(result, dict), "Result should be a dict"
    assert "status" in result, "Missing status field"
    
    if result["status"] == "success":
        assert "medication_ids" in result, "Missing medication_ids field"
        assert 1 in result["medication_ids"], \
            f"Expected medication ID 1 (Аспирин), got {result['medication_ids']}"
    else:
        # If clarification needed, that's also acceptable
        assert result["status"] == "clarification_needed", \
            f"Expected 'success' or 'clarification_needed', got '{result['status']}'"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_time_change_extraction(real_groq_client):
    """Test real LLM extraction of new medication time.
    
    Verifies that the LLM correctly extracts the medication and new time
    from a time change command.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: User message to change medication time
    user_message = "Аспирин теперь в 15:00"
    schedule = [
        {"id": 1, "name": "Аспирин", "time": "10:00", "dosage": "200 мг"}
    ]
    
    # When: Process time change command via real LLM
    result = await real_groq_client.process_time_change_command(user_message, schedule)
    
    # Then: Should extract medication and new time
    assert isinstance(result, dict), "Result should be a dict"
    assert "status" in result, "Missing status field"
    
    if result["status"] == "success":
        assert "medication_id" in result, "Missing medication_id field"
        assert "new_times" in result, "Missing new_times field"
        assert result["medication_id"] == 1, \
            f"Expected medication ID 1, got {result['medication_id']}"
        assert "15:00" in result["new_times"], \
            f"Expected '15:00' in new_times, got {result['new_times']}"
    else:
        # If clarification needed, that's also acceptable
        assert result["status"] == "clarification_needed", \
            f"Expected 'success' or 'clarification_needed', got '{result['status']}'"


# ============================================================================
# GROUP 3: Ambiguity Handling (3 tests)
# ============================================================================


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_delete_needs_clarification(real_groq_client):
    """Test real LLM handling of ambiguous delete command.
    
    Verifies that the LLM requests clarification when delete command
    doesn't specify which medication to delete.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: Ambiguous delete message with multiple medications
    user_message = "Удали лекарство"
    schedule = [
        {"id": 1, "name": "Аспирин", "time": "10:00", "dosage": "200 мг"},
        {"id": 2, "name": "Парацетамол", "time": "14:00", "dosage": "500 мг"},
        {"id": 3, "name": "Витамин D", "time": "12:00", "dosage": "1000 МЕ"}
    ]
    
    # When: Process delete command via real LLM
    result = await real_groq_client.process_delete_command(user_message, schedule)
    
    # Then: Should request clarification
    assert isinstance(result, dict), "Result should be a dict"
    assert "status" in result, "Missing status field"
    
    # Should either request clarification or successfully identify all medications
    assert result["status"] in ["clarification_needed", "success"], \
        f"Expected 'clarification_needed' or 'success', got '{result['status']}'"
    
    if result["status"] == "clarification_needed":
        assert "message" in result, "Missing clarification message"
        assert len(result["message"]) > 0, "Clarification message is empty"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_ambiguous_time_change(real_groq_client):
    """Test real LLM handling of ambiguous time change command.
    
    Verifies that the LLM requests clarification when time change command
    is ambiguous (e.g., multiple medications, unclear time).
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: Ambiguous time change message
    user_message = "Перенеси на вечер"
    schedule = [
        {"id": 1, "name": "Аспирин", "time": "10:00", "dosage": "200 мг"},
        {"id": 2, "name": "Парацетамол", "time": "14:00", "dosage": "500 мг"}
    ]
    
    # When: Process time change command via real LLM
    result = await real_groq_client.process_time_change_command(user_message, schedule)
    
    # Then: Should request clarification or interpret "вечер" as specific time
    assert isinstance(result, dict), "Result should be a dict"
    assert "status" in result, "Missing status field"
    
    # Either clarification or success is acceptable
    assert result["status"] in ["clarification_needed", "success"], \
        f"Expected 'clarification_needed' or 'success', got '{result['status']}'"
    
    if result["status"] == "clarification_needed":
        assert "message" in result, "Missing clarification message"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_unknown_command(real_groq_client):
    """Test real LLM handling of unrecognized command.
    
    Verifies that the LLM correctly identifies commands it cannot understand.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: Unrecognized command
    user_message = "Какая сегодня погода?"
    
    # When: Detect command type via real LLM
    command_type = await real_groq_client.detect_command_type(user_message)
    
    # Then: Should detect as unknown command
    assert command_type == "unknown", \
        f"Expected 'unknown' for weather question, got '{command_type}'"


# ============================================================================
# GROUP 4: Complex Scenarios (3 tests)
# ============================================================================


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_multiple_medications_in_one_message(real_groq_client):
    """Test real LLM extraction of multiple medications from one message.
    
    Verifies that the LLM can extract multiple medications with different
    times from a single user message.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: User message with multiple medications
    user_message = "Добавь аспирин в 10:00 и парацетамол в 18:00"
    
    # When: Process add command via real LLM
    result = await real_groq_client.process_add_command(user_message)
    
    # Then: Should extract both medications
    assert isinstance(result, list), "Result should be a list"
    assert len(result) == 2, f"Expected 2 medications, got {len(result)}"
    
    # Check first medication (аспирин)
    med1 = result[0]
    assert "medication_name" in med1, "Missing medication_name in first medication"
    assert "times" in med1, "Missing times in first medication"
    assert "аспирин" in med1["medication_name"].lower(), \
        f"Expected 'аспирин' in first medication, got '{med1['medication_name']}'"
    assert "10:00" in med1["times"], \
        f"Expected '10:00' in first medication times, got {med1['times']}"
    
    # Check second medication (парацетамол)
    med2 = result[1]
    assert "medication_name" in med2, "Missing medication_name in second medication"
    assert "times" in med2, "Missing times in second medication"
    assert "парацетамол" in med2["medication_name"].lower(), \
        f"Expected 'парацетамол' in second medication, got '{med2['medication_name']}'"
    assert "18:00" in med2["times"], \
        f"Expected '18:00' in second medication times, got {med2['times']}"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_natural_language_variations(real_groq_client):
    """Test real LLM handling of natural language variations.
    
    Verifies that the LLM correctly interprets different ways of expressing
    the same command.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: Different ways to express add command
    variations = [
        "Добавь аспирин в 10:00",
        "Я принимаю аспирин в 10:00",
        "Нужно добавить аспирин на 10 утра",
        "Буду пить аспирин в десять часов"
    ]
    
    # When/Then: All variations should be detected as add command
    for message in variations:
        command_type = await real_groq_client.detect_command_type(message)
        assert command_type == "add", \
            f"Expected 'add' for '{message}', got '{command_type}'"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_typos_and_errors(real_groq_client):
    """Test real LLM handling of typos and spelling errors.
    
    Verifies that the LLM can handle common typos and still extract
    correct information.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: User message with typos
    user_message = "Дабавь аспирн в 10:00"  # "Добавь аспирин"
    
    # When: Process add command via real LLM
    result = await real_groq_client.process_add_command(user_message)
    
    # Then: Should still extract medication despite typos
    # Note: API may return dict or list, handle both
    if isinstance(result, dict):
        medication = result
    elif isinstance(result, list):
        assert len(result) >= 1, "Should extract at least 1 medication"
        medication = result[0]
    else:
        raise AssertionError(f"Result should be dict or list, got {type(result)}")
    assert "medication_name" in medication, "Missing medication_name"
    assert "times" in medication, "Missing times"
    
    # Should recognize "аспирн" as "аспирин"
    med_name = medication["medication_name"].lower()
    assert "аспир" in med_name, \
        f"Expected 'аспир' in medication name, got '{medication['medication_name']}'"
    assert "10:00" in medication["times"], \
        f"Expected '10:00' in times, got {medication['times']}"


# ============================================================================
# Additional Edge Case Tests
# ============================================================================


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_api_error_handling(real_groq_client):
    """Test that API errors are properly raised.
    
    Verifies that the client properly handles and raises API errors.
    Note: This test may not trigger actual errors if API is working.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: Valid message (we can't force API errors easily)
    user_message = "Добавь аспирин в 10:00"
    
    # When/Then: Should either succeed or raise proper exception
    try:
        result = await real_groq_client.detect_command_type(user_message)
        # If successful, verify result is valid
        assert isinstance(result, str), "Result should be a string"
        assert len(result) > 0, "Result should not be empty"
    except GroqAPIError as e:
        # If error occurs, verify it's properly formatted
        assert str(e), "Error message should not be empty"
        assert isinstance(e, GroqAPIError), "Should be GroqAPIError instance"
