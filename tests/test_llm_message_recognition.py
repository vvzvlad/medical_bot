#!/usr/bin/env python3
"""Comprehensive test suite for LLM message recognition in medication bot.

This test suite verifies that the LLM correctly recognizes and processes user messages,
comparing actual LLM responses against expected JSON outputs. It includes both unit tests
with mocked responses and integration tests with real LLM API calls.

Test categories:
1. Command Type Detection - Verify LLM correctly identifies command types
2. Parameter Extraction - Verify LLM extracts medication parameters correctly
3. Confirmation Messages - Verify LLM generates appropriate confirmation messages
4. Real API Tests - Test with actual LLM API calls (when available)
5. Error Handling - Verify proper error handling and fallbacks
"""

import os
import pytest
import json
import asyncio
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from src.llm_processor import LLMProcessor
from src.llm_client import LLMClient


class TestCommandTypeDetection:
    """Test LLM command type detection with various user messages."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        mock = MagicMock(spec=LLMClient)
        return mock
    
    @pytest.fixture
    def llm_processor(self, mock_llm_client):
        """Create LLM processor with mocked client."""
        return LLMProcessor(mock_llm_client)
    
    @pytest.mark.asyncio
    async def test_detect_add_command(self, llm_processor, mock_llm_client):
        """Test detection of add medication command."""
        # Mock LLM response - expected JSON format
        expected_response = {"command_type": "add"}
        mock_llm_client.complete_json.return_value = expected_response
        
        # Test with various add command variations
        test_cases = [
            "я принимаю аспирин в 10:00",
            "добавь парацетамол 400 мг в 18:00",
            "нужно добавить витамин д в 12:00",
            "буду пить габапентин 300 мг утром"
        ]
        
        for user_message in test_cases:
            result = await llm_processor.classify_intent(user_message)
            assert result == "add", f"Failed to detect add command for: {user_message}"
            
            # Verify the LLM was called with correct parameters
            mock_llm_client.complete_json.assert_called()
            call_args = mock_llm_client.complete_json.call_args
            assert "определи тип команды" in call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_detect_delete_command(self, llm_processor, mock_llm_client):
        """Test detection of delete medication command."""
        expected_response = {"command_type": "delete"}
        mock_llm_client.complete_json.return_value = expected_response
        
        test_cases = [
            "удали аспирин",
            "убери парацетамол из расписания",
            "удалить витамин с",
            "убери лекарство"
        ]
        
        for user_message in test_cases:
            result = await llm_processor.classify_intent(user_message)
            assert result == "delete", f"Failed to detect delete command for: {user_message}"
    
    @pytest.mark.asyncio
    async def test_detect_done_command(self, llm_processor, mock_llm_client):
        """Test detection of done (mark as taken) command."""
        expected_response = {"command_type": "done"}
        mock_llm_client.complete_json.return_value = expected_response
        
        test_cases = [
            "я принял аспирин",
            "принял героин в 15",
            "выпил таблетку",
            "отметь как принято парацетамол",
            "я принял лекарство"
        ]
        
        for user_message in test_cases:
            result = await llm_processor.classify_intent(user_message)
            assert result == "done", f"Failed to detect done command for: {user_message}"
    
    @pytest.mark.asyncio
    async def test_detect_list_command(self, llm_processor, mock_llm_client):
        """Test detection of list medications command."""
        expected_response = {"command_type": "list"}
        mock_llm_client.complete_json.return_value = expected_response
        
        test_cases = [
            "что я принимаю?",
            "покажи мое расписание",
            "мои лекарства",
            "список медикаментов"
        ]
        
        for user_message in test_cases:
            result = await llm_processor.classify_intent(user_message)
            assert result == "list", f"Failed to detect list command for: {user_message}"
    
    @pytest.mark.asyncio
    async def test_detect_time_change_command(self, llm_processor, mock_llm_client):
        """Test detection of time change command."""
        expected_response = {"command_type": "time_change"}
        mock_llm_client.complete_json.return_value = expected_response
        
        test_cases = [
            "аспирин теперь в 11:00",
            "перенеси парацетамол на 18:00",
            "измени время приема",
            "витамин д теперь вечером"
        ]
        
        for user_message in test_cases:
            result = await llm_processor.classify_intent(user_message)
            assert result == "time_change", f"Failed to detect time_change command for: {user_message}"
    
    @pytest.mark.asyncio
    async def test_detect_unknown_command(self, llm_processor, mock_llm_client):
        """Test detection of unknown/unsupported commands."""
        expected_response = {"command_type": "unknown"}
        mock_llm_client.complete_json.return_value = expected_response
        
        test_cases = [
            "какая погода?",
            "привет как дела",
            "что ты умеешь?",
            "спасибо",
            "до свидания"
        ]
        
        for user_message in test_cases:
            result = await llm_processor.classify_intent(user_message)
            assert result == "unknown", f"Failed to detect unknown command for: {user_message}"


class TestParameterExtraction:
    """Test LLM parameter extraction from user messages."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        mock = MagicMock(spec=LLMClient)
        return mock
    
    @pytest.fixture
    def llm_processor(self, mock_llm_client):
        """Create LLM processor with mocked client."""
        return LLMProcessor(mock_llm_client)
    
    @pytest.mark.asyncio
    async def test_extract_single_medication(self, llm_processor, mock_llm_client):
        """Test extraction of single medication parameters."""
        expected_response = [{
            "medication_name": "аспирин",
            "times": ["10:00"],
            "dosage": "200 мг"
        }]
        mock_llm_client.complete_json.return_value = expected_response
        
        user_message = "добавь аспирин 200 мг в 10:00"
        result = await llm_processor.process_add(user_message)
        
        assert len(result) == 1
        assert result[0]["medication_name"] == "аспирин"
        assert result[0]["times"] == ["10:00"]
        assert result[0]["dosage"] == "200 мг"
        
        # Verify LLM was called with correct prompt
        mock_llm_client.complete_json.assert_called_once()
        call_args = mock_llm_client.complete_json.call_args
        assert "пользователь хочет добавить новый медикамент" in call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_extract_multiple_medications(self, llm_processor, mock_llm_client):
        """Test extraction of multiple medications from one message."""
        expected_response = [
            {"medication_name": "аспирин", "times": ["10:00"], "dosage": "200 мг"},
            {"medication_name": "парацетамол", "times": ["18:00"], "dosage": "400 мг"}
        ]
        mock_llm_client.complete_json.return_value = expected_response
        
        user_message = "добавь аспирин в 10:00 и парацетамол в 18:00"
        result = await llm_processor.process_add(user_message)
        
        assert len(result) == 2
        assert result[0]["medication_name"] == "аспирин"
        assert result[1]["medication_name"] == "парацетамол"
    
    @pytest.mark.asyncio
    async def test_extract_multiple_times(self, llm_processor, mock_llm_client):
        """Test extraction of medication with multiple intake times."""
        expected_response = [{
            "medication_name": "парацетамол",
            "times": ["10:00", "18:00"],
            "dosage": "400 мг"
        }]
        mock_llm_client.complete_json.return_value = expected_response
        
        user_message = "добавь парацетамол 400 мг в 10:00 и 18:00"
        result = await llm_processor.process_add(user_message)
        
        assert len(result) == 1
        assert result[0]["times"] == ["10:00", "18:00"]
    
    @pytest.mark.asyncio
    async def test_extract_without_dosage(self, llm_processor, mock_llm_client):
        """Test extraction when dosage is not specified."""
        expected_response = [{
            "medication_name": "витамин д",
            "times": ["12:00"],
            "dosage": None
        }]
        mock_llm_client.complete_json.return_value = expected_response
        
        user_message = "добавь витамин д в 12:00"
        result = await llm_processor.process_add(user_message)
        
        assert len(result) == 1
        assert result[0]["medication_name"] == "витамин д"
        assert result[0]["dosage"] is None
    
    @pytest.mark.asyncio
    async def test_process_done_with_schedule(self, llm_processor, mock_llm_client):
        """Test processing done command with schedule context."""
        schedule = [
            {"id": 1, "name": "аспирин", "time": "10:00", "dosage": "200 мг"},
            {"id": 2, "name": "парацетамол", "time": "18:00", "dosage": "400 мг"}
        ]
        
        expected_response = {
            "medication_name": "аспирин",
            "time": "10:00",
            "medication_ids": [1]
        }
        mock_llm_client.complete_json.return_value = expected_response
        
        user_message = "я принял аспирин в 10:00"
        result = await llm_processor.process_done(user_message, schedule)
        
        assert result["medication_name"] == "аспирин"
        assert result["time"] == "10:00"
        assert result["medication_ids"] == [1]
    
    @pytest.mark.asyncio
    async def test_process_done_without_time(self, llm_processor, mock_llm_client):
        """Test processing done command without specific time."""
        schedule = [
            {"id": 1, "name": "аспирин", "time": "10:00", "dosage": "200 мг"}
        ]
        
        expected_response = {
            "medication_name": "аспирин",
            "time": None,
            "medication_ids": [1]
        }
        mock_llm_client.complete_json.return_value = expected_response
        
        user_message = "я принял аспирин"
        result = await llm_processor.process_done(user_message, schedule)
        
        assert result["medication_name"] == "аспирин"
        assert result["time"] is None
        assert result["medication_ids"] == [1]
    
    @pytest.mark.asyncio
    async def test_process_delete_with_clarification(self, llm_processor, mock_llm_client):
        """Test processing delete command when clarification is needed."""
        schedule = [
            {"id": 1, "name": "аспирин", "time": "10:00", "dosage": "200 мг"},
            {"id": 2, "name": "аспирин", "time": "18:00", "dosage": "300 мг"}
        ]
        
        expected_response = {
            "status": "clarification_needed",
            "medication_name": "аспирин",
            "message": "Вы принимаете аспирин в 10:00 и аспирин в 18:00, уточните, какой именно вы хотите удалить"
        }
        mock_llm_client.complete_json.return_value = expected_response
        
        user_message = "удали аспирин"
        result = await llm_processor.process_delete(user_message, schedule)
        
        assert result["status"] == "clarification_needed"
        assert "аспирин" in result["message"]


class TestConfirmationMessages:
    """Test LLM confirmation message generation."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        mock = MagicMock(spec=LLMClient)
        return mock
    
    @pytest.fixture
    def llm_processor(self, mock_llm_client):
        """Create LLM processor with mocked client."""
        return LLMProcessor(mock_llm_client)
    
    @pytest.mark.asyncio
    async def test_generate_confirmation_message_basic(self, llm_processor, mock_llm_client):
        """Test basic confirmation message generation."""
        expected_response = {
            "message": "Отмечено: аспирин (200 мг) принят в 10:00 ✓ Хорошо заботитесь о себе!"
        }
        mock_llm_client.complete_json.return_value = expected_response
        
        result = await llm_processor.generate_confirmation_message("аспирин", "10:00", "200 мг")
        
        assert "аспирин" in result["message"]
        assert "10:00" in result["message"]
        assert "200 мг" in result["message"]
        assert "✓" in result["message"]
    
    @pytest.mark.asyncio
    async def test_generate_confirmation_message_without_time(self, llm_processor, mock_llm_client):
        """Test confirmation message without time specification."""
        expected_response = {
            "message": "Отмечено: витамин D принят ✓"
        }
        mock_llm_client.complete_json.return_value = expected_response
        
        result = await llm_processor.generate_confirmation_message("витамин D", None, None)
        
        assert "витамин D" in result["message"]
        assert "✓" in result["message"]
    
    @pytest.mark.asyncio
    async def test_generate_confirmation_message_without_dosage(self, llm_processor, mock_llm_client):
        """Test confirmation message without dosage specification."""
        expected_response = {
            "message": "Отмечено: парацетамол принят в 18:00 ✓"
        }
        mock_llm_client.complete_json.return_value = expected_response
        
        result = await llm_processor.generate_confirmation_message("парацетамол", "18:00", None)
        
        assert "парацетамол" in result["message"]
        assert "18:00" in result["message"]
        assert "✓" in result["message"]


# Integration tests with real LLM API
@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set - skipping real API tests"
)
class TestRealLLMAPI:
    """Test with real LLM API calls to verify actual behavior."""
    
    @pytest.fixture
    def real_llm_client(self):
        """Create real LLM client with API key."""
        api_key = os.getenv("GROQ_API_KEY")
        return LLMClient(api_key=api_key, model="llama-3.1-70b-versatile")
    
    @pytest.fixture
    def real_llm_processor(self, real_llm_client):
        """Create LLM processor with real client."""
        return LLMProcessor(real_llm_client)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_command_detection(self, real_llm_processor):
        """Test real LLM command detection."""
        user_message = "я принимаю аспирин в 10:00"
        result = await real_llm_processor.classify_intent(user_message)
        assert result == "add"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_parameter_extraction(self, real_llm_processor):
        """Test real LLM parameter extraction."""
        user_message = "добавь аспирин 200 мг в 10:00"
        result = await real_llm_processor.process_add(user_message)
        
        assert len(result) >= 1
        assert "аспирин" in result[0]["medication_name"].lower()
        assert "200" in result[0]["dosage"]
        assert "10:00" in result[0]["times"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_confirmation_message(self, real_llm_processor):
        """Test real LLM confirmation message generation."""
        result = await real_llm_processor.generate_confirmation_message("аспирин", "10:00", "200 мг")
        
        assert "message" in result
        assert len(result["message"]) > 0
        assert "аспирин" in result["message"].lower()
        assert "✓" in result["message"]


class TestErrorHandling:
    """Test error handling and fallback mechanisms."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        mock = MagicMock(spec=LLMClient)
        return mock
    
    @pytest.fixture
    def llm_processor(self, mock_llm_client):
        """Create LLM processor with mocked client."""
        return LLMProcessor(mock_llm_client)
    
    @pytest.mark.asyncio
    async def test_json_decode_error_handling(self, llm_processor, mock_llm_client):
        """Test handling of invalid JSON responses."""
        mock_llm_client.complete_json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        with pytest.raises(json.JSONDecodeError):
            await llm_processor.classify_intent("test message")
    
    @pytest.mark.asyncio
    async def test_empty_response_handling(self, llm_processor, mock_llm_client):
        """Test handling of empty LLM responses."""
        mock_llm_client.complete_json.return_value = {}
        
        result = await llm_processor.classify_intent("test message")
        assert result == "unknown"
    
    @pytest.mark.asyncio
    async def test_missing_fields_handling(self, llm_processor, mock_llm_client):
        """Test handling of missing fields in LLM responses."""
        # Response missing expected fields
        mock_llm_client.complete_json.return_value = {"medication_name": "аспирин"}
        
        result = await llm_processor.process_done("я принял аспирин", [])
        
        # Should handle gracefully with defaults
        assert result["medication_name"] == "аспирин"
        assert result.get("medication_ids", []) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
