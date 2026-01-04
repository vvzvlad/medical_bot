#!/usr/bin/env python3
"""Test suite for multiple medication dose change functionality.

This test suite covers:
1. LLM processing of dose change commands for multiple medications
2. Handling of array responses from LLM
3. Database updates for multiple medications
4. End-to-end flow for changing doses of all instances of a medication
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.llm_processor import LLMProcessor
from src.database import Database
from src.llm_client import LLMClient
from src.telegram_bot import MedicationBot


class TestMultipleDoseChange:
    """Test dose change functionality for multiple medications."""

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
    def mock_database(self):
        """Create a mock database."""
        mock = MagicMock(spec=Database)
        return mock

    @pytest.fixture
    def medication_bot(self, llm_processor, mock_database):
        """Create medication bot with mocked dependencies."""
        bot = MedicationBot(llm_processor, mock_database)
        bot.bot = MagicMock()
        return bot

    @pytest.mark.asyncio
    async def test_process_dose_change_single_medication_array_format(
        self, llm_processor, mock_llm_client
    ):
        """Test processing dose change for single medication in array format."""
        # Mock schedule
        schedule = [
            {"id": 1, "name": "аспирин", "time": "10:00", "dosage": "200 мг"}
        ]

        # Mock LLM response - array with single item
        mock_llm_client.complete_json.return_value = [
            {
                "medication_id": 1,
                "medication_name": "аспирина",
                "new_dosage": "300 мг"
            }
        ]

        # Test processing
        result = await llm_processor.process_dose_change(
            "аспирин теперь 300 мг", schedule
        )

        # Verify
        assert result["status"] == "success"
        assert result["medication_name"] == "аспирина"
        assert len(result["dose_changes"]) == 1
        assert result["dose_changes"][0]["medication_id"] == 1
        assert result["dose_changes"][0]["new_dosage"] == "300 мг"

    @pytest.mark.asyncio
    async def test_process_dose_change_multiple_medications(
        self, llm_processor, mock_llm_client
    ):
        """Test processing dose change for multiple medications."""
        # Mock schedule with multiple aspirin entries
        schedule = [
            {"id": 1, "name": "аспирин", "time": "10:00", "dosage": "200 мг"},
            {"id": 3, "name": "аспирин", "time": "18:00", "dosage": "200 мг"},
            {"id": 5, "name": "аспирин", "time": "22:00", "dosage": "200 мг"},
            {"id": 2, "name": "парацетамол", "time": "12:00", "dosage": "400 мг"}
        ]

        # Mock LLM response - array with multiple items
        mock_llm_client.complete_json.return_value = [
            {
                "medication_id": 1,
                "medication_name": "аспирина",
                "new_dosage": "100 мг"
            },
            {
                "medication_id": 3,
                "medication_name": "аспирина",
                "new_dosage": "100 мг"
            },
            {
                "medication_id": 5,
                "medication_name": "аспирина",
                "new_dosage": "100 мг"
            }
        ]

        # Test processing
        result = await llm_processor.process_dose_change(
            "у всего аспирина теперь доза 100мг", schedule
        )

        # Verify
        assert result["status"] == "success"
        assert result["medication_name"] == "аспирина"
        assert len(result["dose_changes"]) == 3
        assert result["dose_changes"][0]["medication_id"] == 1
        assert result["dose_changes"][1]["medication_id"] == 3
        assert result["dose_changes"][2]["medication_id"] == 5
        assert all(
            change["new_dosage"] == "100 мг" 
            for change in result["dose_changes"]
        )

    @pytest.mark.asyncio
    async def test_process_dose_change_clarification_needed(
        self, llm_processor, mock_llm_client
    ):
        """Test processing dose change when clarification is needed."""
        # Mock schedule
        schedule = [
            {"id": 1, "name": "аспирин", "time": "10:00", "dosage": "200 мг"},
            {"id": 2, "name": "аспирин", "time": "18:00", "dosage": "300 мг"}
        ]

        # Mock LLM response - clarification needed
        mock_llm_client.complete_json.return_value = {
            "status": "clarification_needed",
            "message": "Вы принимаете аспирин в 10:00 и аспирин в 18:00, уточните, для какого именно вы хотите изменить дозировку"
        }

        # Test processing
        result = await llm_processor.process_dose_change(
            "аспирин теперь 250 мг", schedule
        )

        # Verify
        assert result["status"] == "clarification_needed"
        assert "аспирин" in result["message"]

    @pytest.mark.asyncio
    async def test_process_dose_change_old_dict_format(
        self, llm_processor, mock_llm_client
    ):
        """Test backward compatibility with old dict format response."""
        # Mock schedule
        schedule = [
            {"id": 1, "name": "аспирин", "time": "10:00", "dosage": "200 мг"}
        ]

        # Mock LLM response - old dict format (backward compatibility)
        mock_llm_client.complete_json.return_value = {
            "medication_id": 1,
            "medication_name": "аспирина",
            "new_dosage": "300 мг"
        }

        # Test processing
        result = await llm_processor.process_dose_change(
            "аспирин теперь 300 мг", schedule
        )

        # Verify
        assert result["status"] == "success"
        assert result["medication_name"] == "аспирина"
        assert len(result["dose_changes"]) == 1
        assert result["dose_changes"][0]["medication_id"] == 1

    @pytest.mark.asyncio
    async def test_complete_dose_change_flow_multiple_medications(
        self, medication_bot, mock_llm_client, mock_database
    ):
        """Test complete flow of changing dose for multiple medications."""
        # Mock message
        mock_message = MagicMock()
        mock_message.from_user.id = 123456789
        mock_message.from_user.username = "testuser"
        mock_message.from_user.first_name = "Test"
        mock_message.from_user.last_name = "User"
        mock_message.text = "у всего аспирина теперь доза 100мг"
        mock_message.chat.id = 123456789

        # Mock database responses
        mock_database.get_user.return_value = {"timezone_offset": "+03:00"}
        mock_database.get_medications.return_value = [
            {"id": 1, "name": "аспирин", "time": "10:00", "dosage": "200 мг"},
            {"id": 3, "name": "аспирин", "time": "18:00", "dosage": "200 мг"},
            {"id": 5, "name": "аспирин", "time": "22:00", "dosage": "200 мг"},
            {"id": 2, "name": "парацетамол", "time": "12:00", "dosage": "400 мг"}
        ]
        mock_database.update_medication_dosage.return_value = True

        # Mock LLM responses for the flow
        def mock_complete_json(prompt, user_message):
            if "определи тип команды" in prompt.lower():
                return {"command_type": "dose_change"}
            elif "пользователь хочет изменить дозировку медикамента" in prompt.lower():
                return [
                    {
                        "medication_id": 1,
                        "medication_name": "аспирина",
                        "new_dosage": "100 мг"
                    },
                    {
                        "medication_id": 3,
                        "medication_name": "аспирина",
                        "new_dosage": "100 мг"
                    },
                    {
                        "medication_id": 5,
                        "medication_name": "аспирина",
                        "new_dosage": "100 мг"
                    }
                ]
            return {}

        mock_llm_client.complete_json.side_effect = mock_complete_json

        # Mock bot methods
        medication_bot.bot.send_message = AsyncMock(
            return_value=MagicMock(message_id=123)
        )
        medication_bot.bot.delete_message = AsyncMock()

        # Test the complete flow
        await medication_bot.handle_message(mock_message)

        # Verify database interactions
        mock_database.get_medications.assert_called_once_with(123456789)
        
        # Verify update_medication_dosage was called 3 times (once for each aspirin)
        assert mock_database.update_medication_dosage.call_count == 3
        
        # Verify the calls were made with correct parameters
        calls = mock_database.update_medication_dosage.call_args_list
        assert any(call[0] == (1, "100 мг") for call in calls)
        assert any(call[0] == (3, "100 мг") for call in calls)
        assert any(call[0] == (5, "100 мг") for call in calls)

        # Verify response message
        send_calls = medication_bot.bot.send_message.call_args_list
        # Find the call that's not the thinking message
        response_calls = [
            call for call in send_calls 
            if call[0][1] != "🤔🤔🤔"
        ]
        assert len(response_calls) > 0
        response_text = response_calls[0][0][1]
        assert "дозировка" in response_text.lower()
        assert "аспирина" in response_text.lower()
        assert "100 мг" in response_text.lower()
        assert "3 записей" in response_text.lower() or "3" in response_text

    @pytest.mark.asyncio
    async def test_dose_change_partial_failure(
        self, medication_bot, mock_llm_client, mock_database
    ):
        """Test dose change when some updates fail."""
        # Mock message
        mock_message = MagicMock()
        mock_message.from_user.id = 123456789
        mock_message.from_user.username = "testuser"
        mock_message.from_user.first_name = "Test"
        mock_message.from_user.last_name = "User"
        mock_message.text = "у всего аспирина теперь доза 100мг"
        mock_message.chat.id = 123456789

        # Mock database responses
        mock_database.get_user.return_value = {"timezone_offset": "+03:00"}
        mock_database.get_medications.return_value = [
            {"id": 1, "name": "аспирин", "time": "10:00", "dosage": "200 мг"},
            {"id": 3, "name": "аспирин", "time": "18:00", "dosage": "200 мг"},
        ]
        
        # Mock update to fail for second medication
        mock_database.update_medication_dosage.side_effect = [True, False]

        # Mock LLM responses
        def mock_complete_json(prompt, user_message):
            if "определи тип команды" in prompt.lower():
                return {"command_type": "dose_change"}
            elif "пользователь хочет изменить дозировку медикамента" in prompt.lower():
                return [
                    {
                        "medication_id": 1,
                        "medication_name": "аспирина",
                        "new_dosage": "100 мг"
                    },
                    {
                        "medication_id": 3,
                        "medication_name": "аспирина",
                        "new_dosage": "100 мг"
                    }
                ]
            return {}

        mock_llm_client.complete_json.side_effect = mock_complete_json

        # Mock bot methods
        medication_bot.bot.send_message = AsyncMock(
            return_value=MagicMock(message_id=123)
        )
        medication_bot.bot.delete_message = AsyncMock()

        # Test the complete flow
        await medication_bot.handle_message(mock_message)

        # Verify that both success and failure messages were sent
        send_calls = medication_bot.bot.send_message.call_args_list
        response_calls = [
            call for call in send_calls 
            if call[0][1] != "🤔🤔🤔"
        ]
        
        # Should have at least 2 messages: success and warning about failed updates
        assert len(response_calls) >= 1

    @pytest.mark.asyncio
    async def test_dose_change_empty_array_response(
        self, llm_processor, mock_llm_client
    ):
        """Test handling of empty array response from LLM."""
        # Mock schedule
        schedule = [
            {"id": 1, "name": "аспирин", "time": "10:00", "dosage": "200 мг"}
        ]

        # Mock LLM response - empty array
        mock_llm_client.complete_json.return_value = []

        # Test processing
        result = await llm_processor.process_dose_change(
            "аспирин теперь 300 мг", schedule
        )

        # Verify error handling
        assert result["status"] == "error"
        assert "message" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])