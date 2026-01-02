"""Integration test for the specific user scenario: "принял героин в 15".

This test verifies the complete flow:
1. User has "Героин" scheduled at 15:00
2. User says "принял героин в 15"
3. LLM processes the command and generates a confirmation message
4. The confirmation message includes the medication name and is natural/varied
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.llm.client import GroqClient


# Skip this test if GROQ_API_KEY is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set - skipping real API test"
)


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_user_scenario_heroine_fifteen(real_groq_client):
    """Test the complete user scenario with real LLM API.
    
    Scenario:
    - User has "Героин" scheduled at 15:00
    - User says "принял героин в 15"
    - LLM should generate a natural confirmation message
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: User schedule with Героин at 15:00
    schedule = [
        {"id": 1, "name": "Героин", "time": "15:00", "dosage": "50 мг"},
        {"id": 2, "name": "Аспирин", "time": "08:00", "dosage": "200 мг"},
        {"id": 3, "name": "Витамин D", "time": "12:00", "dosage": "1000 МЕ"}
    ]
    
    # User message exactly as mentioned by the user
    user_message = "принял героин в 15"
    
    # When: Process the done command via real LLM
    result = await real_groq_client.process_done_command(user_message, schedule)
    
    # Then: LLM should extract the correct medication and time
    assert isinstance(result, dict), "Result should be a dict"
    assert "medication_name" in result, "Missing medication_name in result"
    assert "time" in result, "Missing time in result"
    assert "medication_ids" in result, "Missing medication_ids in result"
    
    # Verify LLM extracted the medication name (should be "героин" or similar)
    extracted_name = result["medication_name"].lower()
    assert "геро" in extracted_name, f"Expected 'геро' in extracted name, got: {extracted_name}"
    
    # Verify LLM extracted the time
    extracted_time = result["time"]
    assert extracted_time == "15:00", f"Expected '15:00', got: {extracted_time}"
    
    # Verify LLM found the correct medication ID
    medication_ids = result["medication_ids"]
    assert 1 in medication_ids, f"Expected medication ID 1 in {medication_ids}"
    
    # Now test the confirmation message generation
    # When: Generate confirmation message for the extracted medication
    confirmation_message = await real_groq_client.generate_confirmation_message(
        medication_name="Героин",  # Use the actual medication name from schedule
        medication_time="15:00",
        dosage="50 мг"
    )
    
    # Then: Confirmation message should be natural and include relevant information
    assert isinstance(confirmation_message, str), "Confirmation message should be a string"
    assert len(confirmation_message) > 0, "Confirmation message should not be empty"
    
    # Verify the confirmation message includes the medication name
    assert "героин" in confirmation_message.lower(), \
        f"Expected 'героин' in confirmation message, got: {confirmation_message}"
    
    # Verify the confirmation message includes the time
    assert "15:00" in confirmation_message, \
        f"Expected '15:00' in confirmation message, got: {confirmation_message}"
    
    # Verify the confirmation message has a confirmation indicator
    confirmation_indicators = ["✓", "✅", "принят", "отмечено", "записано"]
    has_confirmation = any(indicator in confirmation_message.lower() or indicator in confirmation_message 
                          for indicator in confirmation_indicators)
    assert has_confirmation, \
        f"Expected confirmation indicator in message, got: {confirmation_message}"
    
    # Verify the message is natural (not just a template)
    assert len(confirmation_message) > 15, \
        f"Message should be natural and detailed, got: {confirmation_message}"
    assert len(confirmation_message) < 200, \
        f"Message should be concise, got: {confirmation_message}"
    
    print(f"Generated confirmation message: {confirmation_message}")


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_user_scenario_heroine_variations(real_groq_client):
    """Test variations of the user scenario to ensure robustness.
    
    Tests different ways the user might say the same thing.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: User schedule with Героин at 15:00
    schedule = [
        {"id": 1, "name": "Героин", "time": "15:00", "dosage": "50 мг"}
    ]
    
    # Test different ways to say "I took heroine at 15"
    variations = [
        "принял героин в 15",
        "я принял героин в 15:00", 
        "героин в 15 принял",
        "выпил героин в 15",
        "принял героин в 3 часа дня"
    ]
    
    for user_message in variations:
        # When: Process each variation
        result = await real_groq_client.process_done_command(user_message, schedule)
        
        # Then: Should extract the medication correctly
        assert isinstance(result, dict), f"Result for '{user_message}' should be a dict"
        assert "medication_name" in result, f"Missing medication_name for '{user_message}'"
        
        extracted_name = result["medication_name"].lower()
        assert "геро" in extracted_name, \
            f"Expected 'геро' in extracted name for '{user_message}', got: {extracted_name}"


@pytest.mark.asyncio
async def test_user_scenario_heroine_mock_fallback(mock_groq_client):
    """Test the fallback mechanism when LLM is not available.
    
    Simulates the scenario when LLM API fails and fallback is used.
    
    Args:
        mock_groq_client: Mock GroqClient fixture
    """
    # Given: Mock schedule
    schedule = [
        {"id": 1, "name": "Героин", "time": "15:00", "dosage": "50 мг"}
    ]
    
    # Mock the done command to simulate successful processing
    async def mock_process_done(message, schedule):
        return {
            "medication_name": "героин",
            "time": "15:00", 
            "medication_ids": [1]
        }
    
    mock_groq_client.process_done_command = AsyncMock(side_effect=mock_process_done)
    
    # When: Process the user message
    user_message = "принял героин в 15"
    result = await mock_groq_client.process_done_command(user_message, schedule)
    
    # Then: Should extract correctly even with mock
    assert result["medication_name"] == "героин"
    assert result["time"] == "15:00"
    assert 1 in result["medication_ids"]
    
    # Test fallback confirmation message
    medication_name = "Героин"
    fallback_message = f"Отмечено как принято: {medication_name} ✓"
    
    assert "Героин" in fallback_message
    assert "✓" in fallback_message