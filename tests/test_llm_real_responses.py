#!/usr/bin/env python3
"""Test suite for verifying real LLM responses against expected JSON outputs.

This test file makes actual API calls to the LLM and verifies that the responses
match the expected JSON structure and content. It's designed to test the real
behavior of the LLM with the exact prompts used in the application.

Tests include:
1. Real command detection with exact user messages
2. Real parameter extraction with expected JSON format
3. Real confirmation message generation
4. Validation of JSON response structure
5. Comparison of actual vs expected responses
"""

import os
import pytest
import json
from typing import Dict, List, Any
from datetime import datetime

from src.llm_processor import LLMProcessor
from src.llm_client import LLMClient


# Skip all tests if GROQ_API_KEY is not available
pytestmark = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set - skipping real API tests"
)


class TestRealLLMCommandDetection:
    """Test real LLM command detection with actual API calls."""
    
    @pytest.fixture
    def real_llm_processor(self):
        """Create LLM processor with real API client."""
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
        llm_client = LLMClient(api_key=api_key, model=model)
        return LLMProcessor(llm_client)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_detect_add_command(self, real_llm_processor):
        """Test real LLM detection of add command."""
        user_message = "я принимаю аспирин в 10:00"
        result = await real_llm_processor.classify_intent(user_message)
        
        # Verify the result is exactly what we expect
        assert result == "add", f"Expected 'add', got '{result}' for message: {user_message}"
        
        # Verify the response is a valid string (not empty, not None)
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_detect_delete_command(self, real_llm_processor):
        """Test real LLM detection of delete command."""
        user_message = "удали аспирин"
        result = await real_llm_processor.classify_intent(user_message)
        
        assert result == "delete", f"Expected 'delete', got '{result}' for message: {user_message}"
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_detect_done_command_heroine(self, real_llm_processor):
        """Test real LLM detection of done command with the exact heroine scenario."""
        user_message = "принял героин в 15"
        result = await real_llm_processor.classify_intent(user_message)
        
        assert result == "done", f"Expected 'done', got '{result}' for message: {user_message}"
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_detect_list_command(self, real_llm_processor):
        """Test real LLM detection of list command."""
        user_message = "что я принимаю?"
        result = await real_llm_processor.classify_intent(user_message)
        
        assert result == "list", f"Expected 'list', got '{result}' for message: {user_message}"
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_detect_unknown_command(self, real_llm_processor):
        """Test real LLM detection of unknown command."""
        user_message = "какая погода?"
        result = await real_llm_processor.classify_intent(user_message)
        
        assert result == "unknown", f"Expected 'unknown', got '{result}' for message: {user_message}"
        assert isinstance(result, str)
        assert len(result) > 0


class TestRealLLMParameterExtraction:
    """Test real LLM parameter extraction with actual API calls."""
    
    @pytest.fixture
    def real_llm_processor(self):
        """Create LLM processor with real API client."""
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
        llm_client = LLMClient(api_key=api_key, model=model)
        return LLMProcessor(llm_client)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_extract_single_medication(self, real_llm_processor):
        """Test real LLM extraction of single medication parameters."""
        user_message = "добавь аспирин 200 мг в 10:00"
        result = await real_llm_processor.process_add(user_message)
        
        # Verify the result structure
        assert isinstance(result, list)
        assert len(result) >= 1
        
        medication = result[0]
        assert isinstance(medication, dict)
        assert "medication_name" in medication
        assert "times" in medication
        assert "dosage" in medication
        
        # Verify the content
        assert "аспирин" in medication["medication_name"].lower()
        assert medication["times"] == ["10:00"]
        assert "200" in medication["dosage"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_extract_multiple_medications(self, real_llm_processor):
        """Test real LLM extraction of multiple medications."""
        user_message = "добавь аспирин в 10:00 и парацетамол в 18:00"
        result = await real_llm_processor.process_add(user_message)
        
        # Verify the result structure
        assert isinstance(result, list)
        assert len(result) >= 2
        
        # Verify first medication
        med1 = result[0]
        assert "аспирин" in med1["medication_name"].lower()
        assert med1["times"] == ["10:00"]
        
        # Verify second medication
        med2 = result[1]
        assert "парацетамол" in med2["medication_name"].lower()
        assert med2["times"] == ["18:00"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_extract_multiple_times(self, real_llm_processor):
        """Test real LLM extraction of medication with multiple times."""
        user_message = "добавь парацетамол в 10:00 и 18:00"
        result = await real_llm_processor.process_add(user_message)
        
        # Verify the result structure
        assert isinstance(result, list)
        assert len(result) >= 1
        
        medication = result[0]
        assert "парацетамол" in medication["medication_name"].lower()
        assert isinstance(medication["times"], list)
        assert len(medication["times"]) == 2
        assert "10:00" in medication["times"]
        assert "18:00" in medication["times"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_extract_without_dosage(self, real_llm_processor):
        """Test real LLM extraction when dosage is not specified."""
        user_message = "добавь витамин д в 12:00"
        result = await real_llm_processor.process_add(user_message)
        
        # Verify the result structure
        assert isinstance(result, list)
        assert len(result) >= 1
        
        medication = result[0]
        assert "витамин" in medication["medication_name"].lower()
        assert medication["times"] == ["12:00"]
        # Dosage can be None, empty string, or contain some default value, or missing
        assert "dosage" not in medication or medication["dosage"] is None or medication["dosage"] == "" or isinstance(medication["dosage"], str)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_process_done_with_schedule(self, real_llm_processor):
        """Test real LLM processing of done command with schedule context."""
        schedule = [
            {"id": 1, "name": "аспирин", "time": "10:00", "dosage": "200 мг"},
            {"id": 2, "name": "парацетамол", "time": "18:00", "dosage": "400 мг"}
        ]
        
        user_message = "я принял аспирин в 10:00"
        result = await real_llm_processor.process_done(user_message, schedule)
        
        # Verify the result structure
        assert isinstance(result, dict)
        assert "medication_name" in result
        assert "time" in result
        assert "medication_ids" in result
        
        # Verify the content
        assert "аспирин" in result["medication_name"].lower()
        assert result["time"] == "10:00"
        assert 1 in result["medication_ids"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_process_done_heroine_exact(self, real_llm_processor):
        """Test real LLM processing of the exact heroine scenario."""
        schedule = [
            {"id": 1, "name": "Героин", "time": "15:00", "dosage": "50 мг"},
            {"id": 2, "name": "Аспирин", "time": "08:00", "dosage": "200 мг"}
        ]
        
        user_message = "принял героин в 15"
        result = await real_llm_processor.process_done(user_message, schedule)
        
        # Verify the result structure
        assert isinstance(result, dict)
        assert "medication_name" in result
        assert "time" in result
        assert "medication_ids" in result
        
        # Verify the content - should recognize "героин" even with case variations
        assert "геро" in result["medication_name"].lower()
        assert result["time"] == "15:00"
        assert 1 in result["medication_ids"]


class TestRealLLMConfirmationMessages:
    """Test real LLM confirmation message generation."""
    
    @pytest.fixture
    def real_llm_processor(self):
        """Create LLM processor with real API client."""
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
        llm_client = LLMClient(api_key=api_key, model=model)
        return LLMProcessor(llm_client)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_confirmation_message_basic(self, real_llm_processor):
        """Test real LLM generation of basic confirmation message."""
        result = await real_llm_processor.generate_confirmation_message("аспирин", "10:00", "200 мг")
        
        # Verify the result structure
        assert isinstance(result, dict)
        assert "message" in result
        
        # Verify the message content
        message = result["message"]
        assert isinstance(message, str)
        assert len(message) > 0
        assert "аспирин" in message.lower()
        assert "10:00" in message
        # Check for dosage in different formats (handling Unicode spaces)
        assert ("200 мг" in message or "200\u202fмг" in message or "200mg" in message.lower())
        assert any(indicator in message for indicator in ["✓", "✅", "принят", "отмечено"])
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_confirmation_message_heroine(self, real_llm_processor):
        """Test real LLM generation of confirmation message for heroine scenario."""
        result = await real_llm_processor.generate_confirmation_message("Героин", "15:00", "50 мг")
        
        # Verify the result structure
        assert isinstance(result, dict)
        assert "message" in result
        
        # Verify the message content
        message = result["message"]
        assert isinstance(message, str)
        assert len(message) > 0
        assert "геро" in message.lower()
        assert "15:00" in message
        assert any(indicator in message for indicator in ["✓", "✅", "принят", "отмечено"])
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_confirmation_message_without_dosage(self, real_llm_processor):
        """Test real LLM confirmation message without dosage."""
        result = await real_llm_processor.generate_confirmation_message("витамин д", "12:00", None)
        
        # Verify the result structure
        assert isinstance(result, dict)
        assert "message" in result
        
        # Verify the message content
        message = result["message"]
        assert isinstance(message, str)
        assert len(message) > 0
        assert "витамин" in message.lower()
        assert "12:00" in message
        assert any(indicator in message for indicator in ["✓", "✅", "принят", "отмечено"])


class TestRealLLMResponseValidation:
    """Test validation of real LLM responses against expected formats."""
    
    @pytest.fixture
    def real_llm_processor(self):
        """Create LLM processor with real API client."""
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
        llm_client = LLMClient(api_key=api_key, model=model)
        return LLMProcessor(llm_client)
    
    def validate_json_response(self, response: Any, expected_keys: List[str]) -> bool:
        """Validate that a JSON response contains all expected keys."""
        if not isinstance(response, dict):
            return False
        
        for key in expected_keys:
            if key not in response:
                return False
        
        return True
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_validate_command_detection_response(self, real_llm_processor):
        """Test that command detection returns valid JSON with expected keys."""
        user_message = "добавь аспирин в 10:00"
        
        # Use the existing processor to test real response
        result = await real_llm_processor.classify_intent(user_message)
        
        # Validate the response
        assert result == "add"
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_validate_add_command_response(self, real_llm_processor):
        """Test that add command returns valid JSON with expected structure."""
        user_message = "добавь аспирин 200 мг в 10:00"
        
        # Get the raw LLM response
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
        llm_client = LLMClient(api_key=api_key, model=model)
        
        prompt = f"""Пользователь хочет добавить новый медикамент. Извлеки информацию и верни JSON массив с объектами.

Сообщение пользователя: добавь аспирин 200 мг в 10:00

Формат ответа:
[
  {{
    "medication_name": "название медикамента",
    "times": ["время1", "время2"],
    "dosage": "дозировка"
  }}
]"""
        
        raw_response = await llm_client.complete_json(prompt, user_message)
        
        # Validate the response structure
        assert isinstance(raw_response, list)
        assert len(raw_response) >= 1
        
        medication = raw_response[0]
        assert self.validate_json_response(medication, ["medication_name", "times", "dosage"])
        assert isinstance(medication["medication_name"], str)
        assert isinstance(medication["times"], list)
        assert isinstance(medication["dosage"], (str, type(None)))
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_validate_done_command_response(self, real_llm_processor):
        """Test that done command returns valid JSON with expected structure."""
        schedule = [{"id": 1, "name": "аспирин", "time": "10:00", "dosage": "200 мг"}]
        user_message = "я принял аспирин в 10:00"
        
        # Get the raw LLM response
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
        llm_client = LLMClient(api_key=api_key, model=model)
        
        prompt = f"""Пользователь хочет отметить, что принял медикамент. Найди соответствующий медикамент в расписании.

Расписание: {schedule}

Сообщение пользователя: я принял аспирин в 10:00

Формат ответа:
{{
  "medication_name": "название медикамента",
  "time": "время приема",
  "medication_ids": [id_медикаментов]
}}"""
        
        raw_response = await llm_client.complete_json(prompt, user_message)
        
        # Validate the response structure
        assert self.validate_json_response(raw_response, ["medication_name", "time", "medication_ids"])
        assert isinstance(raw_response["medication_name"], str)
        assert isinstance(raw_response["time"], (str, type(None)))
        assert isinstance(raw_response["medication_ids"], list)


class TestRealLLMConsistency:
    """Test consistency of real LLM responses across multiple calls."""
    
    @pytest.fixture
    def real_llm_processor(self):
        """Create LLM processor with real API client."""
        api_key = os.getenv("GROQ_API_KEY")
        llm_client = LLMClient(api_key=api_key, model="llama-3.1-70b-versatile")
        return LLMProcessor(llm_client)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_consistent_command_detection(self, real_llm_processor):
        """Test that LLM consistently detects the same command type."""
        user_message = "я принимаю аспирин в 10:00"
        
        # Test consistency with the configured model
        result = await real_llm_processor.classify_intent(user_message)
        assert result == "add"
        
        # Test another message for consistency
        result2 = await real_llm_processor.classify_intent("удали аспирин")
        assert result2 == "delete"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_consistent_parameter_extraction(self, real_llm_processor):
        """Test that LLM consistently extracts parameters."""
        user_message = "добавь аспирин 200 мг в 10:00"
        
        # Test parameter extraction consistency
        result = await real_llm_processor.process_add(user_message)
        
        assert len(result) >= 1
        medication = result[0]
        assert "аспирин" in medication["medication_name"].lower()
        assert "200" in medication["dosage"]
        assert medication["times"] == ["10:00"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])