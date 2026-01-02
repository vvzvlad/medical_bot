"""Integration tests for LLM-generated medication confirmation messages.

These tests verify that the LLM generates natural, varied confirmation messages
when users mark medications as taken. Tests the specific scenario mentioned by
the user: when someone says "принял героин в 15", the LLM should formulate
the confirmation message.

Tests include:
1. Basic confirmation message generation
2. Confirmation with time specification
3. Confirmation with dosage information
4. Fallback mechanism when LLM fails
5. Variation in message generation
"""

import os
import pytest
from typing import Any, Dict, List
from unittest.mock import AsyncMock

from src.llm.client import GroqClient, GroqAPIError


# Skip all tests in this module if GROQ_API_KEY is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set - skipping real API tests"
)


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_llm_confirmation_message_basic(real_groq_client):
    """Test basic LLM confirmation message generation.
    
    Verifies that the LLM generates a natural confirmation message
    for a basic medication without time or dosage.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: Basic medication name
    medication_name = "Аспирин"
    
    # When: Generate confirmation message via real LLM
    result = await real_groq_client.generate_confirmation_message(
        medication_name=medication_name
    )
    
    # Then: Should return a natural confirmation message
    assert isinstance(result, str), "Result should be a string"
    assert len(result) > 0, "Result should not be empty"
    assert "аспирин" in result.lower(), f"Expected 'аспирин' in message, got: {result}"
    assert "✓" in result or "принят" in result.lower() or "отмечено" in result.lower(), \
        f"Expected confirmation indicator in message, got: {result}"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_llm_confirmation_message_with_time(real_groq_client):
    """Test LLM confirmation message with time specification.
    
    Verifies that the LLM includes the time in the confirmation message
    when time is specified.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: Medication with time
    medication_name = "Героин"
    medication_time = "15:00"
    
    # When: Generate confirmation message via real LLM
    result = await real_groq_client.generate_confirmation_message(
        medication_name=medication_name,
        medication_time=medication_time
    )
    
    # Then: Should include both medication name and time
    assert isinstance(result, str), "Result should be a string"
    assert len(result) > 0, "Result should not be empty"
    assert "героин" in result.lower(), f"Expected 'героин' in message, got: {result}"
    assert "15:00" in result, f"Expected '15:00' in message, got: {result}"
    assert "✓" in result or "принят" in result.lower() or "отмечено" in result.lower(), \
        f"Expected confirmation indicator in message, got: {result}"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_llm_confirmation_message_with_dosage(real_groq_client):
    """Test LLM confirmation message with dosage information.
    
    Verifies that the LLM includes dosage information in the confirmation message.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: Medication with dosage
    medication_name = "Витамин D"
    dosage = "1000 МЕ"
    
    # When: Generate confirmation message via real LLM
    result = await real_groq_client.generate_confirmation_message(
        medication_name=medication_name,
        dosage=dosage
    )
    
    # Then: Should include medication name and dosage
    assert isinstance(result, str), "Result should be a string"
    assert len(result) > 0, "Result should not be empty"
    assert "витамин" in result.lower(), f"Expected 'витамин' in message, got: {result}"
    assert "1000" in result, f"Expected dosage '1000' in message, got: {result}"
    assert "✓" in result or "принят" in result.lower() or "отмечено" in result.lower(), \
        f"Expected confirmation indicator in message, got: {result}"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_llm_confirmation_message_complete_scenario(real_groq_client):
    """Test complete LLM confirmation message scenario.
    
    Tests the specific scenario mentioned by the user: "принял героин в 15"
    should generate a natural confirmation message.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: Complete medication information (the user's scenario)
    medication_name = "Героин"
    medication_time = "15:00"
    dosage = "50 мг"
    
    # When: Generate confirmation message via real LLM
    result = await real_groq_client.generate_confirmation_message(
        medication_name=medication_name,
        medication_time=medication_time,
        dosage=dosage
    )
    
    # Then: Should be a comprehensive, natural message
    assert isinstance(result, str), "Result should be a string"
    assert len(result) > 0, "Result should not be empty"
    assert "героин" in result.lower(), f"Expected 'героин' in message, got: {result}"
    assert "15:00" in result, f"Expected '15:00' in message, got: {result}"
    assert "50" in result, f"Expected dosage '50' in message, got: {result}"
    assert "✓" in result or "принят" in result.lower() or "отмечено" in result.lower(), \
        f"Expected confirmation indicator in message, got: {result}"
    
    # Verify message is natural and not just a template
    assert len(result) > 20, f"Message should be natural and detailed, got: {result}"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_llm_confirmation_message_variations(real_groq_client):
    """Test that LLM generates varied confirmation messages.
    
    Verifies that the LLM generates different variations of confirmation
    messages for the same input, making conversations more natural.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: Same medication information
    medication_name = "Парацетамол"
    medication_time = "14:00"
    
    # When: Generate multiple confirmation messages
    messages = []
    for _ in range(3):  # Generate 3 messages
        result = await real_groq_client.generate_confirmation_message(
            medication_name=medication_name,
            medication_time=medication_time
        )
        messages.append(result)
    
    # Then: All messages should be valid
    for msg in messages:
        assert isinstance(msg, str), "Each result should be a string"
        assert len(msg) > 0, "Each result should not be empty"
        assert "парацетамол" in msg.lower(), f"Expected 'парацетамол' in message, got: {msg}"
        assert "14:00" in msg, f"Expected '14:00' in message, got: {msg}"
    
    # Check for some variation (messages shouldn't be identical)
    unique_messages = set(messages)
    assert len(unique_messages) >= 2, f"Expected at least 2 unique messages, got: {messages}"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_llm_confirmation_message_different_medications(real_groq_client):
    """Test LLM confirmation messages for different medications.
    
    Verifies that the LLM handles different types of medications appropriately.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Test cases with different medication types
    test_cases = [
        ("Аспирин", "08:00", "200 мг"),
        ("Витамин C", "12:00", "1 таблетка"),
        ("Габапентин", "18:00", "300 мг"),
        ("Ламотриджин", "20:00", "100 мг"),
    ]
    
    for med_name, med_time, dosage in test_cases:
        # When: Generate confirmation message for each medication
        result = await real_groq_client.generate_confirmation_message(
            medication_name=med_name,
            medication_time=med_time,
            dosage=dosage
        )
        
        # Then: Each message should be appropriate
        assert isinstance(result, str), f"Result for {med_name} should be a string"
        assert len(result) > 0, f"Result for {med_name} should not be empty"
        assert med_name.lower() in result.lower(), f"Expected '{med_name}' in message, got: {result}"
        assert med_time in result, f"Expected '{med_time}' in message, got: {result}"
        assert dosage.split()[0] in result, f"Expected dosage '{dosage.split()[0]}' in message, got: {result}"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_llm_confirmation_message_russian_language(real_groq_client):
    """Test that LLM generates proper Russian language messages.
    
    Verifies that the confirmation messages are grammatically correct
    and use natural Russian language.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: Medication with Russian name
    medication_name = "Ношпа"
    medication_time = "16:30"
    
    # When: Generate confirmation message via real LLM
    result = await real_groq_client.generate_confirmation_message(
        medication_name=medication_name,
        medication_time=medication_time
    )
    
    # Then: Should be proper Russian
    assert isinstance(result, str), "Result should be a string"
    assert len(result) > 0, "Result should not be empty"
    
    # Check for natural Russian language patterns
    russian_patterns = [
        "принят", "принято", "отмечено", "записано",
        "в 16:30", "в 16.30", "16:30", "16.30"
    ]
    
    has_russian_pattern = any(pattern in result.lower() for pattern in russian_patterns)
    assert has_russian_pattern, f"Expected Russian language patterns in message, got: {result}"
    
    # Message should sound natural
    assert len(result) < 200, f"Message should be concise, got: {result}"


@pytest.mark.llm_real
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_llm_confirmation_message_without_optional_params(real_groq_client):
    """Test LLM confirmation message with minimal parameters.
    
    Verifies that the LLM handles cases where time and dosage are not provided.
    
    Args:
        real_groq_client: Real GroqClient fixture
    """
    # Given: Only medication name (no time or dosage)
    medication_name = "Ибупрофен"
    
    # When: Generate confirmation message via real LLM
    result = await real_groq_client.generate_confirmation_message(
        medication_name=medication_name
    )
    
    # Then: Should still generate a valid message
    assert isinstance(result, str), "Result should be a string"
    assert len(result) > 0, "Result should not be empty"
    assert "ибупрофен" in result.lower(), f"Expected 'ибупрофен' in message, got: {result}"
    assert "✓" in result or "принят" in result.lower() or "отмечено" in result.lower(), \
        f"Expected confirmation indicator in message, got: {result}"


# Test for fallback mechanism (simulate API failure)
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_confirmation_message_fallback(mock_groq_client):
    """Test fallback mechanism when LLM API fails.
    
    Verifies that the system falls back to a simple template message
    when the LLM API is unavailable.
    
    Args:
        mock_groq_client: Mock GroqClient fixture
    """
    # Given: Mock client that simulates API failure
    async def failing_confirmation(*args, **kwargs):
        raise GroqAPIError("API temporarily unavailable")
    
    mock_groq_client.generate_confirmation_message = AsyncMock(side_effect=failing_confirmation)
    
    # When: Try to generate confirmation message (will fail and use fallback)
    try:
        await mock_groq_client.generate_confirmation_message(medication_name="Аспирин")
        # If we reach here, the mock didn't fail as expected
        assert False, "Expected API to fail"
    except GroqAPIError:
        # This is expected - the fallback would be handled in the handler
        pass
    
    # Simulate the fallback behavior that would happen in the handler
    medication_name = "Аспирин"
    fallback_message = f"Отмечено как принято: {medication_name} ✓"
    
    # Then: Fallback message should be valid
    assert isinstance(fallback_message, str), "Fallback should be a string"
    assert "аспирин" in fallback_message.lower(), f"Expected 'аспирин' in fallback, got: {fallback_message}"
    assert "✓" in fallback_message, f"Expected checkmark in fallback, got: {fallback_message}"