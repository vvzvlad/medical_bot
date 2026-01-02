"""Integration test for medication ID mismatch fix."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.data.models import Medication, UserData
from src.bot.handlers import handle_done_command


@pytest.mark.asyncio
async def test_medication_id_mismatch_fix():
    """Test that the medication ID mismatch issue is fixed.
    
    This test verifies that when the LLM returns hallucinated medication IDs
    that don't exist in the user's schedule, the system handles it gracefully
    instead of crashing.
    """
    
    # Create a mock user with medications that have IDs 1, 2, 3
    user_id = 85106994
    medications = [
        Medication(id=1, name="ламотриджин", dosage=None, time="09:00", last_taken=1767160800),
        Medication(id=2, name="героин", dosage=None, time="15:00", last_taken=None),
        Medication(id=3, name="героин", dosage=None, time="15:30", last_taken=None),
    ]
    
    user_data = UserData(user_id=user_id, timezone_offset="+03:00", medications=medications)
    
    # Mock the data manager
    mock_data_manager = AsyncMock()
    mock_data_manager.get_user_data.return_value = user_data
    mock_data_manager.save_user_data.return_value = None
    
    # Mock the schedule manager
    mock_schedule_manager = AsyncMock()
    mock_schedule_manager.get_user_schedule.return_value = medications
    
    # Mock the LLM client to return hallucinated ID 23 (the bug scenario)
    mock_groq_client = AsyncMock()
    mock_groq_client.process_done_command.return_value = {
        "medication_name": "героин",
        "time": None,
        "medication_ids": [23]  # This is the hallucinated ID that doesn't exist
    }
    
    # Mock the message
    mock_message = AsyncMock()
    mock_message.from_user.id = user_id
    mock_message.text = "принял героин"
    mock_message.bot.send_chat_action.return_value = None
    mock_message.answer.return_value = None
    
    # Mock thinking message
    mock_thinking_msg = AsyncMock()
    mock_thinking_msg.delete.return_value = None
    
    # Set up the global mocks
    import src.bot.handlers as handlers
    handlers.data_manager = mock_data_manager
    handlers.schedule_manager = mock_schedule_manager
    handlers.groq_client = mock_groq_client
    
    # Test the fix
    await handle_done_command(mock_message, user_id, "принял героин", mock_thinking_msg)
    
    # Verify that the LLM was called with the correct schedule
    call_args = mock_groq_client.process_done_command.call_args
    schedule_passed_to_llm = call_args[0][1]
    assert len(schedule_passed_to_llm) == 3
    assert schedule_passed_to_llm[0]['id'] == 1
    assert schedule_passed_to_llm[1]['id'] == 2
    assert schedule_passed_to_llm[2]['id'] == 3
    
    # Verify that the system successfully found medications by name and marked them as taken
    # (the name-based fallback should have worked)
    answer_calls = mock_message.answer.call_args_list
    success_messages = [call[0][0] for call in answer_calls if 'Отмечено как принято' in call[0][0]]
    assert len(success_messages) > 0, "Expected success message when medications are found by name"
    
    # Verify that mark_medication_taken was called with the correct IDs
    # (should have found medications by name when LLM IDs were invalid)
    mark_calls = mock_schedule_manager.mark_medication_taken.call_args_list
    marked_ids = [call[0][1] for call in mark_calls]
    assert len(marked_ids) > 0, "Expected medications to be marked as taken when found by name"


@pytest.mark.asyncio
async def test_valid_medication_id_still_works():
    """Test that valid medication IDs still work correctly after the fix."""
    
    # Create a mock user with medications that have IDs 1, 2, 3
    user_id = 85106994
    medications = [
        Medication(id=1, name="ламотриджин", dosage=None, time="09:00", last_taken=1767160800),
        Medication(id=2, name="героин", dosage=None, time="15:00", last_taken=None),
        Medication(id=3, name="героин", dosage=None, time="15:30", last_taken=None),
    ]
    
    user_data = UserData(user_id=user_id, timezone_offset="+03:00", medications=medications)
    
    # Mock the data manager
    mock_data_manager = AsyncMock()
    mock_data_manager.get_user_data.return_value = user_data
    mock_data_manager.save_user_data.return_value = None
    
    # Mock the schedule manager
    mock_schedule_manager = AsyncMock()
    mock_schedule_manager.get_user_schedule.return_value = medications
    mock_schedule_manager.mark_medication_taken.return_value = None
    
    # Mock the LLM client to return valid IDs
    mock_groq_client = AsyncMock()
    mock_groq_client.process_done_command.return_value = {
        "medication_name": "героин",
        "time": None,
        "medication_ids": [2, 3]  # Valid IDs
    }
    
    # Mock the message
    mock_message = AsyncMock()
    mock_message.from_user.id = user_id
    mock_message.text = "принял героин"
    mock_message.bot.send_chat_action.return_value = None
    mock_message.answer.return_value = None
    
    # Mock thinking message
    mock_thinking_msg = AsyncMock()
    mock_thinking_msg.delete.return_value = None
    
    # Set up the global mocks
    import src.bot.handlers as handlers
    handlers.data_manager = mock_data_manager
    handlers.schedule_manager = mock_schedule_manager
    handlers.groq_client = mock_groq_client
    
    # Test that valid IDs still work
    await handle_done_command(mock_message, user_id, "принял героин", mock_thinking_msg)
    
    # Verify that mark_medication_taken was called with the correct IDs
    mark_calls = mock_schedule_manager.mark_medication_taken.call_args_list
    marked_ids = [call[0][1] for call in mark_calls]
    assert 2 in marked_ids or 3 in marked_ids, "Expected medication 2 or 3 to be marked as taken"
    
    # Verify that the success message was sent
    answer_calls = mock_message.answer.call_args_list
    success_messages = [call[0][0] for call in answer_calls if 'Отмечено как принято' in call[0][0]]
    assert len(success_messages) > 0, "Expected success message for valid medication IDs"


@pytest.mark.asyncio
async def test_medication_name_fallback():
    """Test that the system falls back to medication name matching when LLM IDs are invalid."""
    
    # Create a mock user with medications
    user_id = 85106994
    medications = [
        Medication(id=1, name="аспирин", dosage="200 мг", time="09:00", last_taken=None),
        Medication(id=2, name="героин", dosage=None, time="15:00", last_taken=None),
    ]
    
    user_data = UserData(user_id=user_id, timezone_offset="+03:00", medications=medications)
    
    # Mock the data manager
    mock_data_manager = AsyncMock()
    mock_data_manager.get_user_data.return_value = user_data
    mock_data_manager.save_user_data.return_value = None
    
    # Mock the schedule manager
    mock_schedule_manager = AsyncMock()
    mock_schedule_manager.get_user_schedule.return_value = medications
    mock_schedule_manager.mark_medication_taken.return_value = None
    
    # Mock the LLM client to return invalid IDs but correct medication name
    mock_groq_client = AsyncMock()
    mock_groq_client.process_done_command.return_value = {
        "medication_name": "героин",  # Correct name
        "time": None,
        "medication_ids": [999]  # Invalid ID
    }
    
    # Mock the message
    mock_message = AsyncMock()
    mock_message.from_user.id = user_id
    mock_message.text = "принял героин"
    mock_message.bot.send_chat_action.return_value = None
    mock_message.answer.return_value = None
    
    # Mock thinking message
    mock_thinking_msg = AsyncMock()
    mock_thinking_msg.delete.return_value = None
    
    # Set up the global mocks
    import src.bot.handlers as handlers
    handlers.data_manager = mock_data_manager
    handlers.schedule_manager = mock_schedule_manager
    handlers.groq_client = mock_groq_client
    
    # Test the name-based fallback
    await handle_done_command(mock_message, user_id, "принял героин", mock_thinking_msg)
    
    # Verify that mark_medication_taken was called with the correct medication
    # (should find the medication by name when the ID is invalid)
    mark_calls = mock_schedule_manager.mark_medication_taken.call_args_list
    marked_ids = [call[0][1] for call in mark_calls]
    assert 2 in marked_ids, "Expected medication 2 (героин) to be found by name and marked as taken"