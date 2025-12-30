"""Unit tests for LLM client."""

import pytest
from unittest.mock import AsyncMock

from src.llm.client import (
    GroqClient,
    GroqAPIError,
    GroqTimeoutError,
    GroqRateLimitError,
    GroqInsufficientFundsError,
)


# TC-LLM-001: Successful Command Detection
@pytest.mark.asyncio
async def test_detect_add_command(mock_groq_client):
    """Test detection of add medication command."""
    # Given: User message requesting to add medication
    user_message = "Добавь аспирин в 10:00"
    
    # When: LLM detects command type
    command_type = await mock_groq_client.detect_command_type(user_message)
    
    # Then: Command type should be 'add'
    assert command_type == "add"


# TC-LLM-002: Multiple Command Types
@pytest.mark.parametrize("message,expected_type", [
    ("Добавь аспирин в 10:00", "add"),
    ("Удали парацетамол", "delete"),
    ("Что я принимаю?", "list"),
    ("Аспирин теперь в 11:00", "time_change"),
    ("Аспирин теперь 300 мг", "dose_change"),
    ("Моя часовая зона Москва", "timezone_change"),
    ("Принял аспирин", "done"),
    ("Привет как дела", "unknown"),
])
@pytest.mark.asyncio
async def test_detect_various_commands(mock_groq_client, message, expected_type):
    """Test detection of various command types."""
    command_type = await mock_groq_client.detect_command_type(message)
    assert command_type == expected_type


# TC-LLM-003: Add Command Parameter Extraction
@pytest.mark.asyncio
async def test_process_add_command_single_time(mock_groq_client):
    """Test extraction of medication parameters - single time."""
    # Given: User message with medication details
    user_message = "Добавь аспирин 200 мг в 10:00"
    
    # When: LLM processes add command
    result = await mock_groq_client.process_add_command(user_message)
    
    # Then: Parameters should be correctly extracted
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0]["medication_name"] == "аспирин"
    assert result[0]["times"] == ["10:00"]
    assert result[0]["dosage"] == "200 мг"


# TC-LLM-004: Add Command Multiple Times
@pytest.mark.asyncio
async def test_process_add_command_multiple_times():
    """Test extraction of medication with multiple times."""
    # This test would need a real LLM client or more sophisticated mock
    # For now, we test the structure
    client = GroqClient()
    
    # Mock the _make_request method
    async def mock_request(prompt):
        return [{
            "medication_name": "парацетамол",
            "times": ["12:00", "18:00"],
            "dosage": None
        }]
    
    client._make_request = AsyncMock(side_effect=mock_request)
    
    user_message = "Принимаю парацетамол в 12:00 и 18:00"
    result = await client.process_add_command(user_message)
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0]["medication_name"] == "парацетамол"
    assert result[0]["times"] == ["12:00", "18:00"]
    assert result[0]["dosage"] is None


# TC-LLM-005: Add Command Multiple Medications
@pytest.mark.asyncio
async def test_process_add_command_multiple_medications():
    """Test extraction of multiple medications in one message."""
    client = GroqClient()
    
    # Mock the _make_request method
    async def mock_request(prompt):
        return [
            {"medication_name": "аспирин", "times": ["10:00"], "dosage": None},
            {"medication_name": "парацетамол", "times": ["18:00"], "dosage": None}
        ]
    
    client._make_request = AsyncMock(side_effect=mock_request)
    
    user_message = "Добавь аспирин в 10:00 и парацетамол в 18:00"
    result = await client.process_add_command(user_message)
    
    # Result should be a list of medications
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["medication_name"] == "аспирин"
    assert result[1]["medication_name"] == "парацетамол"


# TC-LLM-006: Delete Command with Clarification
@pytest.mark.asyncio
async def test_process_delete_command_needs_clarification(mock_groq_client):
    """Test delete command when clarification is needed."""
    user_message = "Удали лекарство"
    schedule = [
        {"id": 1, "name": "аспирин", "time": "10:00"},
        {"id": 2, "name": "парацетамол", "time": "18:00"}
    ]
    
    result = await mock_groq_client.process_delete_command(user_message, schedule)
    
    assert result["status"] == "clarification_needed"
    assert "message" in result
    assert "аспирин" in result["message"] or "парацетамол" in result["message"]


# TC-LLM-007: Delete Command Success
@pytest.mark.asyncio
async def test_process_delete_command_success(mock_groq_client):
    """Test successful delete command."""
    user_message = "Удали аспирин"
    schedule = [
        {"id": 1, "name": "аспирин", "time": "10:00"},
        {"id": 2, "name": "парацетамол", "time": "18:00"}
    ]
    
    result = await mock_groq_client.process_delete_command(user_message, schedule)
    
    assert result["status"] == "success"
    assert result["medication_ids"] == [1]


# TC-LLM-008: Time Change Command
@pytest.mark.asyncio
async def test_process_time_change_command(mock_groq_client):
    """Test time change command processing."""
    user_message = "Аспирин теперь в 11:00"
    schedule = [
        {"id": 1, "name": "аспирин", "time": "10:00"},
    ]
    
    result = await mock_groq_client.process_time_change_command(user_message, schedule)
    
    assert result["status"] == "success"
    assert result["medication_id"] == 1
    assert result["new_times"] == ["11:00"]


# TC-LLM-009: Dose Change Command
@pytest.mark.asyncio
async def test_process_dose_change_command(mock_groq_client):
    """Test dose change command processing."""
    user_message = "Аспирин теперь 300 мг"
    schedule = [
        {"id": 1, "name": "аспирин", "dosage": "200 мг", "time": "10:00"},
    ]
    
    result = await mock_groq_client.process_dose_change_command(user_message, schedule)
    
    assert result["status"] == "success"
    assert result["medication_id"] == 1
    assert result["new_dosage"] == "300 мг"


# TC-LLM-010: Timezone Change Command
@pytest.mark.asyncio
async def test_process_timezone_change_command(mock_groq_client):
    """Test timezone change command processing."""
    user_message = "Моя часовая зона Москва"
    
    result = await mock_groq_client.process_timezone_change_command(user_message)
    
    assert result["status"] == "success"
    assert result["timezone_offset"] == "+03:00"


# TC-LLM-011: Done Command
@pytest.mark.asyncio
async def test_process_done_command(mock_groq_client):
    """Test done command processing."""
    user_message = "Принял аспирин"
    schedule = [
        {"id": 1, "name": "аспирин", "time": "10:00"},
        {"id": 2, "name": "парацетамол", "time": "18:00"}
    ]
    
    result = await mock_groq_client.process_done_command(user_message, schedule)
    
    assert "medication_ids" in result
    assert 1 in result["medication_ids"]


# TC-LLM-ERR-001: Timeout Error
@pytest.mark.asyncio
async def test_llm_timeout_error():
    """Test handling of LLM API timeout."""
    # Given: LLM API times out
    client = GroqClient()
    client._make_request = AsyncMock(side_effect=GroqTimeoutError("Timeout"))
    
    # When/Then: Should raise GroqTimeoutError
    with pytest.raises(GroqTimeoutError):
        await client.detect_command_type("test message")


# TC-LLM-ERR-002: Rate Limit Error
@pytest.mark.asyncio
async def test_llm_rate_limit_error():
    """Test handling of rate limit error."""
    client = GroqClient()
    client._make_request = AsyncMock(side_effect=GroqRateLimitError("Rate limit"))
    
    with pytest.raises(GroqRateLimitError):
        await client.detect_command_type("test message")


# TC-LLM-ERR-003: Insufficient Funds Error
@pytest.mark.asyncio
async def test_llm_insufficient_funds_error():
    """Test handling of insufficient funds error."""
    client = GroqClient()
    client._make_request = AsyncMock(side_effect=GroqInsufficientFundsError("No funds"))
    
    with pytest.raises(GroqInsufficientFundsError):
        await client.detect_command_type("test message")


# TC-LLM-ERR-004: Invalid JSON Response
@pytest.mark.asyncio
async def test_llm_invalid_json_response():
    """Test handling of invalid JSON in LLM response."""
    # Given: LLM returns invalid JSON
    client = GroqClient()
    client._make_request = AsyncMock(side_effect=GroqAPIError("Invalid JSON"))
    
    # When/Then: Should raise GroqAPIError
    with pytest.raises(GroqAPIError):
        await client.detect_command_type("test message")


# TC-LLM-ERR-005: Retry Logic
@pytest.mark.asyncio
async def test_llm_retry_logic():
    """Test retry logic on transient errors."""
    from unittest.mock import patch, AsyncMock, MagicMock
    import httpx
    
    # Given: First two attempts timeout, third succeeds
    client = GroqClient()
    
    call_count = 0
    
    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise httpx.TimeoutException("Timeout")
        
        # Third attempt succeeds
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"command_type": "add"}'}}]
        }
        return mock_response
    
    # When: Calling detect_command_type with mocked httpx client
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = mock_post
        mock_client_class.return_value = mock_client
        
        result = await client.detect_command_type("test message")
    
    # Then: Should succeed after retries
    assert result == "add"
    assert call_count == 3
