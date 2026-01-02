#!/usr/bin/env python3
"""Test configuration and fixtures for medication bot tests.

This file contains shared fixtures and configuration for all test files.
It provides mock objects, test data, and utility functions used across tests.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, List, Optional

from src.llm_processor import LLMProcessor
from src.llm_client import LLMClient
from src.database import Database


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    mock = MagicMock(spec=LLMClient)
    return mock


@pytest.fixture
def mock_llm_processor(mock_llm_client):
    """Create an LLM processor with mocked client."""
    return LLMProcessor(mock_llm_client)


@pytest.fixture
def mock_database():
    """Create a mock database for testing."""
    mock = MagicMock(spec=Database)
    return mock


@pytest.fixture
def mock_schedule_manager():
    """Create a mock schedule manager for testing."""
    mock = MagicMock()
    return mock


@pytest.fixture
def sample_medication_schedule():
    """Provide a sample medication schedule for testing."""
    return [
        {"id": 1, "name": "Аспирин", "time": "08:00", "dosage": "200 мг"},
        {"id": 2, "name": "Парацетамол", "time": "12:00", "dosage": "400 мг"},
        {"id": 3, "name": "Витамин D", "time": "18:00", "dosage": "1000 МЕ"},
        {"id": 4, "name": "Героин", "time": "15:00", "dosage": "50 мг"}
    ]


@pytest.fixture
def sample_user_messages():
    """Provide sample user messages for testing."""
    return {
        "add": [
            "я принимаю аспирин в 10:00",
            "добавь парацетамол 400 мг в 18:00",
            "нужно добавить витамин д в 12:00"
        ],
        "delete": [
            "удали аспирин",
            "убери парацетамол из расписания",
            "удалить витамин с"
        ],
        "done": [
            "я принял аспирин",
            "принял героин в 15",
            "выпил таблетку"
        ],
        "list": [
            "что я принимаю?",
            "покажи мое расписание",
            "мои лекарства"
        ],
        "time_change": [
            "аспирин теперь в 11:00",
            "перенеси парацетамол на 18:00"
        ],
        "unknown": [
            "какая погода?",
            "привет как дела",
            "спасибо"
        ]
    }


@pytest.fixture
def expected_command_responses():
    """Provide expected LLM responses for different commands."""
    return {
        "add": {"command_type": "add"},
        "delete": {"command_type": "delete"},
        "done": {"command_type": "done"},
        "list": {"command_type": "list"},
        "time_change": {"command_type": "time_change"},
        "unknown": {"command_type": "unknown"}
    }


@pytest.fixture
def expected_add_response():
    """Provide expected response for add command."""
    return [
        {
            "medication_name": "аспирин",
            "times": ["10:00"],
            "dosage": "200 мг"
        }
    ]


@pytest.fixture
def expected_done_response():
    """Provide expected response for done command."""
    return {
        "medication_name": "аспирин",
        "time": "10:00",
        "medication_ids": [1]
    }


@pytest.fixture
def expected_confirmation_response():
    """Provide expected response for confirmation message."""
    return {
        "message": "Отмечено: аспирин (200 мг) принят в 10:00 ✓"
    }


@pytest.fixture
def real_llm_client():
    """Create a real LLM client if API key is available."""
    import os
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    
    return LLMClient(api_key=api_key, model="llama-3.1-70b-versatile")


@pytest.fixture
def real_llm_processor(real_llm_client):
    """Create an LLM processor with real client if available."""
    if not real_llm_client:
        return None
    
    return LLMProcessor(real_llm_client)


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "llm_real: mark test as requiring real LLM API"
    )
    config.addinivalue_line(
        "markers", "timeout: mark test with custom timeout"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip real API tests if no key is available."""
    import os
    
    if not os.getenv("GROQ_API_KEY"):
        # Skip tests marked with @pytest.mark.llm_real
        skip_real = pytest.mark.skip(reason="GROQ_API_KEY not set")
        
        for item in items:
            if "llm_real" in item.keywords:
                item.add_marker(skip_real)


# Utility functions for tests
def create_mock_async_function(return_value=None, side_effect=None):
    """Create a mock async function."""
    async def mock_func(*args, **kwargs):
        if side_effect:
            if callable(side_effect):
                return side_effect(*args, **kwargs)
            else:
                raise side_effect
        return return_value
    
    return AsyncMock(side_effect=mock_func)


def validate_json_structure(data: dict, required_keys: list) -> bool:
    """Validate that a dictionary contains all required keys."""
    if not isinstance(data, dict):
        return False
    
    for key in required_keys:
        if key not in data:
            return False
    
    return True


def normalize_medication_name(name: str) -> str:
    """Normalize medication name for comparison."""
    return name.lower().strip()


def is_time_format(time_str: str) -> bool:
    """Check if string is in HH:MM format."""
    try:
        parts = time_str.split(':')
        if len(parts) != 2:
            return False
        
        hour = int(parts[0])
        minute = int(parts[1])
        
        return 0 <= hour <= 23 and 0 <= minute <= 59
    except (ValueError, AttributeError):
        return False


# Russian language test helpers
def contains_russian_confirmation(text: str) -> bool:
    """Check if text contains Russian confirmation indicators."""
    indicators = ["принят", "принято", "отмечено", "записано", "✓", "✅"]
    text_lower = text.lower()
    return any(indicator in text_lower or indicator in text for indicator in indicators)


def extract_time_from_text(text: str) -> Optional[str]:
    """Extract time in HH:MM format from text."""
    import re
    
    # Pattern to match HH:MM format
    pattern = r'\b([01]?\d|2[0-3]):([0-5]\d)\b'
    match = re.search(pattern, text)
    
    if match:
        hour = match.group(1)
        minute = match.group(2)
        
        # Ensure proper formatting with leading zeros
        return f"{int(hour):02d}:{int(minute):02d}"
    
    return None


# Test data generators
def generate_test_medications() -> List[Dict]:
    """Generate test medication data."""
    return [
        {"id": 1, "name": "Аспирин", "time": "08:00", "dosage": "200 мг"},
        {"id": 2, "name": "Парацетамол", "time": "12:00", "dosage": "400 мг"},
        {"id": 3, "name": "Ибупрофен", "time": "18:00", "dosage": "600 мг"},
        {"id": 4, "name": "Витамин C", "time": "09:00", "dosage": "1000 мг"},
        {"id": 5, "name": "Габапентин", "time": "15:00", "dosage": "300 мг"},
        {"id": 6, "name": "Героин", "time": "15:00", "dosage": "50 мг"}
    ]


def generate_natural_language_variations(base_message: str) -> List[str]:
    """Generate natural language variations of a message."""
    variations = [base_message]
    
    # Add common variations based on the base message
    if "принимаю" in base_message:
        variations.extend([
            base_message.replace("принимаю", "пью"),
            base_message.replace("принимаю", "принимаю"),
            base_message.replace("принимаю", "буду принимать")
        ])
    
    if "аспирин" in base_message:
        variations.extend([
            base_message.replace("аспирин", "аспирин"),
            base_message.replace("аспирин", "аспирин таблетки")
        ])
    
    return list(set(variations))  # Remove duplicates


# Error simulation helpers
class LLMErrorSimulator:
    """Helper class to simulate various LLM errors."""
    
    @staticmethod
    def timeout_error():
        """Simulate timeout error."""
        import asyncio
        return asyncio.TimeoutError("Request timeout")
    
    @staticmethod
    def json_decode_error():
        """Simulate JSON decode error."""
        import json
        return json.JSONDecodeError("Invalid JSON", "", 0)
    
    @staticmethod
    def api_error():
        """Simulate API error."""
        return Exception("API error occurred")
    
    @staticmethod
    def rate_limit_error():
        """Simulate rate limit error."""
        return Exception("Rate limit exceeded")


# Performance testing helpers
async def measure_response_time(coro, *args, **kwargs):
    """Measure the response time of an async function."""
    import time
    
    start_time = time.time()
    result = await coro(*args, **kwargs)
    end_time = time.time()
    
    return result, end_time - start_time


# Russian text processing helpers
def normalize_russian_text(text: str) -> str:
    """Normalize Russian text for comparison."""
    import re
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove punctuation for comparison
    text = re.sub(r'[^\w\s]', '', text)
    
    return text


def extract_medication_name(text: str) -> Optional[str]:
    """Extract medication name from text."""
    # This is a simplified implementation
    # In a real scenario, you might use more sophisticated NLP
    common_medications = [
        "аспирин", "парацетамол", "ибупрофен", "витамин", "габапентин", "героин"
    ]
    
    text_normalized = normalize_russian_text(text)
    
    for med in common_medications:
        if med in text_normalized:
            return med
    
    return None


# Test assertions
def assert_valid_medication_data(medication: dict):
    """Assert that medication data is valid."""
    assert isinstance(medication, dict)
    assert "medication_name" in medication
    assert "times" in medication
    assert isinstance(medication["medication_name"], str)
    assert len(medication["medication_name"]) > 0
    assert isinstance(medication["times"], list)
    assert len(medication["times"]) > 0
    
    for time in medication["times"]:
        assert is_time_format(time)


def assert_valid_confirmation_message(message: str):
    """Assert that confirmation message is valid."""
    assert isinstance(message, str)
    assert len(message) > 0
    assert len(message) < 500  # Reasonable length limit
    assert contains_russian_confirmation(message)