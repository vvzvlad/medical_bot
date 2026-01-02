#!/usr/bin/env python3
"""Test thinking message functionality in medication bot."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.telegram_bot import MedicationBot
from src.llm_processor import LLMProcessor
from src.database import Database


@pytest.mark.asyncio
async def test_send_thinking_message():
    """Test that thinking message is sent correctly."""
    # Create mock objects
    mock_llm = MagicMock(spec=LLMProcessor)
    mock_db = MagicMock(spec=Database)
    mock_bot = MagicMock()
    
    # Setup the bot with mocked dependencies
    medication_bot = MedicationBot(mock_llm, mock_db)
    medication_bot.bot = mock_bot
    
    # Mock the bot send_message method
    mock_message = MagicMock()
    mock_message.message_id = 123
    mock_bot.send_message = AsyncMock(return_value=mock_message)
    
    # Test sending thinking message
    chat_id = 456
    message_id = await medication_bot.send_thinking_message(chat_id)
    
    # Verify the thinking message was sent
    mock_bot.send_message.assert_called_once_with(chat_id, "думаю...")
    assert message_id == 123


@pytest.mark.asyncio
async def test_delete_thinking_message():
    """Test that thinking message is deleted correctly."""
    # Create mock objects
    mock_llm = MagicMock(spec=LLMProcessor)
    mock_db = MagicMock(spec=Database)
    mock_bot = MagicMock()
    
    # Setup the bot with mocked dependencies
    medication_bot = MedicationBot(mock_llm, mock_db)
    medication_bot.bot = mock_bot
    
    # Mock the bot delete_message method
    mock_bot.delete_message = AsyncMock()
    
    # Test deleting thinking message
    chat_id = 456
    message_id = 123
    await medication_bot.delete_thinking_message(chat_id, message_id)
    
    # Verify the thinking message was deleted
    mock_bot.delete_message.assert_called_once_with(chat_id, 123)


@pytest.mark.asyncio
async def test_handle_message_with_thinking_message():
    """Test that handle_message sends and deletes thinking message during processing."""
    # Create mock objects
    mock_llm = MagicMock(spec=LLMProcessor)
    mock_db = MagicMock(spec=Database)
    mock_bot = MagicMock()
    mock_message = MagicMock()
    
    # Setup message mock
    mock_message.from_user.id = 123
    mock_message.text = "test message"
    mock_message.chat.id = 456
    
    # Setup the bot with mocked dependencies
    medication_bot = MedicationBot(mock_llm, mock_db)
    medication_bot.bot = mock_bot
    
    # Mock database methods
    mock_db.get_user = AsyncMock(return_value=None)
    mock_db.create_user = AsyncMock()
    
    # Mock LLM methods
    mock_llm.classify_intent = AsyncMock(return_value="unknown")
    mock_llm.process_unknown = AsyncMock(return_value={"message": "test response"})
    
    # Mock bot methods
    mock_thinking_message = MagicMock()
    mock_thinking_message.message_id = 789
    mock_bot.send_message = AsyncMock(return_value=mock_thinking_message)
    mock_bot.delete_message = AsyncMock()
    
    # Mock message reply
    mock_message.reply = AsyncMock()
    
    # Test handle_message
    await medication_bot.handle_message(mock_message)
    
    # Verify thinking message was sent
    mock_bot.send_message.assert_any_call(456, "думаю...")
    
    # Verify thinking message was deleted
    mock_bot.delete_message.assert_called_once_with(456, 789)
    
    # Verify response was sent
    mock_message.reply.assert_called_once_with("test response")


@pytest.mark.asyncio
async def test_thinking_message_error_handling():
    """Test that errors in thinking message operations don't break the flow."""
    # Create mock objects
    mock_llm = MagicMock(spec=LLMProcessor)
    mock_db = MagicMock(spec=Database)
    mock_bot = MagicMock()
    mock_message = MagicMock()
    
    # Setup message mock
    mock_message.from_user.id = 123
    mock_message.text = "test message"
    mock_message.chat.id = 456
    
    # Setup the bot with mocked dependencies
    medication_bot = MedicationBot(mock_llm, mock_db)
    medication_bot.bot = mock_bot
    
    # Mock database methods
    mock_db.get_user = AsyncMock(return_value=None)
    mock_db.create_user = AsyncMock()
    
    # Mock LLM methods
    mock_llm.classify_intent = AsyncMock(return_value="unknown")
    mock_llm.process_unknown = AsyncMock(return_value={"message": "test response"})
    
    # Mock bot methods to simulate errors
    mock_bot.send_message = AsyncMock(side_effect=Exception("Network error"))
    mock_bot.delete_message = AsyncMock()
    
    # Mock message reply
    mock_message.reply = AsyncMock()
    
    # Test handle_message with thinking message error
    await medication_bot.handle_message(mock_message)
    
    # Verify thinking message was attempted but failed
    mock_bot.send_message.assert_called_once()
    
    # Verify response was still sent despite thinking message error
    mock_message.reply.assert_called_once_with("test response")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])