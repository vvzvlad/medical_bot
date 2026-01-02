#!/usr/bin/env python3
"""Test suite for the specific user scenario: "принял героин в 15".

This test file focuses on the exact scenario mentioned by the user where someone says
"принял героин в 15" and the LLM should generate an appropriate confirmation message.

Tests include:
1. Command detection for the specific phrase
2. Parameter extraction (medication name and time)
3. Confirmation message generation
4. Real LLM API testing with the exact phrase
5. Variations of the phrase to ensure robustness
"""

import os
import pytest
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock

from src.llm_processor import LLMProcessor
from src.llm_client import LLMClient


class TestHeroineScenarioDetection:
    """Test LLM recognition of the specific "принял героин в 15" scenario."""
    
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
    async def test_detect_done_command_heroine_fifteen(self, llm_processor, mock_llm_client):
        """Test that 'принял героин в 15' is detected as done command."""
        expected_response = {"command_type": "done"}
        mock_llm_client.complete_json.return_value = expected_response
        
        user_message = "принял героин в 15"
        result = await llm_processor.classify_intent(user_message)
        
        assert result == "done", f"Failed to detect done command for: {user_message}"
        mock_llm_client.complete_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_detect_variations_of_heroine_phrase(self, llm_processor, mock_llm_client):
        """Test detection of various ways to say the same thing."""
        expected_response = {"command_type": "done"}
        mock_llm_client.complete_json.return_value = expected_response
        
        variations = [
            "принял героин в 15",
            "я принял героин в 15:00",
            "героин в 15 принял",
            "выпил героин в 15",
            "принял героин в 3 часа дня",
            "отметь как принято героин в 15"
        ]
        
        for user_message in variations:
            result = await llm_processor.classify_intent(user_message)
            assert result == "done", f"Failed to detect done command for variation: {user_message}"
            mock_llm_client.reset_mock()


class TestHeroineScenarioExtraction:
    """Test LLM parameter extraction for the heroine scenario."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        mock = MagicMock(spec=LLMClient)
        return mock
    
    @pytest.fixture
    def llm_processor(self, mock_llm_client):
        """Create LLM processor with mocked client."""
        return LLMProcessor(mock_llm_client)
    
    @pytest.fixture
    def sample_schedule(self):
        """Create a sample schedule with heroine at 15:00."""
        return [
            {"id": 1, "name": "Героин", "time": "15:00", "dosage": "50 мг"},
            {"id": 2, "name": "Аспирин", "time": "08:00", "dosage": "200 мг"},
            {"id": 3, "name": "Витамин D", "time": "12:00", "dosage": "1000 МЕ"}
        ]
    
    @pytest.mark.asyncio
    async def test_extract_heroine_parameters_exact_phrase(self, llm_processor, mock_llm_client, sample_schedule):
        """Test extraction of medication name and time from exact phrase."""
        expected_response = {
            "medication_name": "героин",
            "time": "15:00",
            "medication_ids": [1]
        }
        mock_llm_client.complete_json.return_value = expected_response
        
        user_message = "принял героин в 15"
        result = await llm_processor.process_done(user_message, sample_schedule)
        
        assert result["medication_name"] == "героин"
        assert result["time"] == "15:00"
        assert result["medication_ids"] == [1]
        
        # Verify LLM was called with correct prompt
        mock_llm_client.complete_json.assert_called_once()
        call_args = mock_llm_client.complete_json.call_args
        assert "пользователь хочет отметить, что принял медикамент" in call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_extract_heroine_parameters_variations(self, llm_processor, mock_llm_client, sample_schedule):
        """Test extraction with different variations of the phrase."""
        test_cases = [
            {
                "message": "принял героин в 15",
                "expected_name": "героин",
                "expected_time": "15:00",
                "expected_ids": [1]
            },
            {
                "message": "я принял героин в 15:00",
                "expected_name": "героин", 
                "expected_time": "15:00",
                "expected_ids": [1]
            },
            {
                "message": "героин в 15 принял",
                "expected_name": "героин",
                "expected_time": "15:00", 
                "expected_ids": [1]
            }
        ]
        
        for test_case in test_cases:
            mock_llm_client.reset_mock()
            mock_llm_client.complete_json.return_value = {
                "medication_name": test_case["expected_name"],
                "time": test_case["expected_time"],
                "medication_ids": test_case["expected_ids"]
            }
            
            result = await llm_processor.process_done(test_case["message"], sample_schedule)
            
            assert result["medication_name"] == test_case["expected_name"]
            assert result["time"] == test_case["expected_time"]
            assert result["medication_ids"] == test_case["expected_ids"]


class TestHeroineConfirmationMessages:
    """Test confirmation message generation for the heroine scenario."""
    
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
    async def test_confirmation_message_heroine_basic(self, llm_processor, mock_llm_client):
        """Test confirmation message for basic heroine scenario."""
        expected_response = {
            "message": "Отмечено как принято: героин в 15:00 ✓"
        }
        mock_llm_client.complete_json.return_value = expected_response
        
        result = await llm_processor.generate_confirmation_message("Героин", "15:00", "50 мг")
        
        assert "героин" in result["message"].lower()
        assert "15:00" in result["message"]
        assert "✓" in result["message"]
    
    @pytest.mark.asyncio
    async def test_confirmation_message_heroine_with_dosage(self, llm_processor, mock_llm_client):
        """Test confirmation message including dosage information."""
        expected_response = {
            "message": "Отмечено: героин (50 мг) принят в 15:00 ✓ Хорошо заботитесь о себе!"
        }
        mock_llm_client.complete_json.return_value = expected_response
        
        result = await llm_processor.generate_confirmation_message("Героин", "15:00", "50 мг")
        
        assert "героин" in result["message"].lower()
        assert "50 мг" in result["message"]
        assert "15:00" in result["message"]
        assert "✓" in result["message"]
    
    @pytest.mark.asyncio
    async def test_confirmation_message_variations(self, llm_processor, mock_llm_client):
        """Test that confirmation messages can vary while maintaining key information."""
        # Mock different variations of confirmation messages
        variations = [
            {"message": "Отмечено как принято: героин ✓"},
            {"message": "Героин в 15:00 отмечен как принято ✓"},
            {"message": "Принято: героин (50 мг) в 15:00 ✓"},
            {"message": "Записано: героин принят в 15:00 ✓"}
        ]
        
        for i, expected_response in enumerate(variations):
            mock_llm_client.reset_mock()
            mock_llm_client.complete_json.return_value = expected_response
            
            result = await llm_processor.generate_confirmation_message("Героин", "15:00", "50 мг")
            
            # All variations should contain key information
            assert "героин" in result["message"].lower()
            assert "✓" in result["message"]
            # Not all variations include time, but that's okay for natural language


# Real API tests with the exact user scenario
@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set - skipping real API tests"
)
class TestRealAPIHeroineScenario:
    """Test with real LLM API using the exact user scenario."""
    
    @pytest.fixture
    def real_llm_client(self):
        """Create real LLM client with API key."""
        api_key = os.getenv("GROQ_API_KEY")
        return LLMClient(api_key=api_key, model="llama-3.1-70b-versatile")
    
    @pytest.fixture
    def real_llm_processor(self, real_llm_client):
        """Create LLM processor with real client."""
        return LLMProcessor(real_llm_client)
    
    @pytest.fixture
    def sample_schedule(self):
        """Create a sample schedule with heroine at 15:00."""
        return [
            {"id": 1, "name": "Героин", "time": "15:00", "dosage": "50 мг"},
            {"id": 2, "name": "Аспирин", "time": "08:00", "dosage": "200 мг"}
        ]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_api_detect_heroine_command(self, real_llm_processor):
        """Test real LLM detects the exact user phrase as done command."""
        user_message = "принял героин в 15"
        result = await real_llm_processor.classify_intent(user_message)
        assert result == "done"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_api_extract_heroine_parameters(self, real_llm_processor, sample_schedule):
        """Test real LLM extracts parameters from the exact user phrase."""
        user_message = "принял героин в 15"
        result = await real_llm_processor.process_done(user_message, sample_schedule)
        
        assert "medication_name" in result
        assert "time" in result
        assert "medication_ids" in result
        
        # Verify the medication name contains "геро" (allowing for case variations)
        assert "геро" in result["medication_name"].lower()
        
        # Verify the time is correctly extracted
        assert result["time"] == "15:00"
        
        # Verify the correct medication ID is found
        assert 1 in result["medication_ids"]
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_api_heroine_confirmation_message(self, real_llm_processor):
        """Test real LLM generates confirmation message for heroine scenario."""
        result = await real_llm_processor.generate_confirmation_message("Героин", "15:00", "50 мг")
        
        assert "message" in result
        assert len(result["message"]) > 0
        
        # Verify the confirmation message contains key elements
        message_lower = result["message"].lower()
        assert "геро" in message_lower
        assert "15:00" in result["message"]
        assert any(indicator in result["message"] for indicator in ["✓", "✅", "принят", "отмечено"])
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_real_api_heroine_variations(self, real_llm_processor, sample_schedule):
        """Test real LLM with variations of the heroine phrase."""
        variations = [
            "принял героин в 15",
            "я принял героин в 15:00",
            "героин в 15 принял",
            "выпил героин в 15"
        ]
        
        for user_message in variations:
            # Test command detection
            command_result = await real_llm_processor.classify_intent(user_message)
            assert command_result == "done", f"Failed for variation: {user_message}"
            
            # Test parameter extraction
            extract_result = await real_llm_processor.process_done(user_message, sample_schedule)
            assert "геро" in extract_result["medication_name"].lower()
            assert extract_result["time"] == "15:00"


class TestHeroineScenarioEdgeCases:
    """Test edge cases and error scenarios for the heroine scenario."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        mock = MagicMock(spec=LLMClient)
        return mock
    
    @pytest.fixture
    def llm_processor(self, mock_llm_client):
        """Create LLM processor with mocked client."""
        return LLMProcessor(mock_llm_client)
    
    @pytest.fixture
    def sample_schedule(self):
        """Create a sample schedule with heroine at 15:00."""
        return [
            {"id": 1, "name": "Героин", "time": "15:00", "dosage": "50 мг"},
            {"id": 2, "name": "Аспирин", "time": "08:00", "dosage": "200 мг"}
        ]
    
    @pytest.mark.asyncio
    async def test_heroine_not_in_schedule(self, llm_processor, mock_llm_client):
        """Test when heroine is not in the user's schedule."""
        schedule_without_heroine = [
            {"id": 1, "name": "Аспирин", "time": "08:00", "dosage": "200 мг"},
            {"id": 2, "name": "Витамин D", "time": "12:00", "dosage": "1000 МЕ"}
        ]
        
        # Mock LLM to return heroine but no matching IDs
        expected_response = {
            "medication_name": "героин",
            "time": "15:00",
            "medication_ids": []  # Not found in schedule
        }
        mock_llm_client.complete_json.return_value = expected_response
        
        user_message = "принял героин в 15"
        result = await llm_processor.process_done(user_message, schedule_without_heroine)
        
        assert result["medication_name"] == "героин"
        assert result["time"] == "15:00"
        assert result["medication_ids"] == []  # Should be empty when not found
    
    @pytest.mark.asyncio
    async def test_heroine_wrong_time(self, llm_processor, mock_llm_client, sample_schedule):
        """Test when user mentions wrong time for heroine."""
        # Mock LLM to return wrong time
        expected_response = {
            "medication_name": "героин",
            "time": "16:00",  # Wrong time - heroine is at 15:00
            "medication_ids": [1]
        }
        mock_llm_client.complete_json.return_value = expected_response
        
        user_message = "принял героин в 16"
        result = await llm_processor.process_done(user_message, sample_schedule)
        
        assert result["medication_name"] == "героин"
        assert result["time"] == "16:00"
        # The medication_ids would be empty in real scenario due to time mismatch
        # but here we mock it to test the extraction logic


if __name__ == "__main__":
    pytest.main([__file__, "-v"])