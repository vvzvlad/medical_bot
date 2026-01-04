"""Test to verify the notification deletion behavior in the hourly reminder method.

This test verifies that the _send_hourly_reminder method correctly handles
the deletion of old notification messages before sending fresh ones, preventing
multiple reminder messages from accumulating.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
import asyncio
from datetime import datetime


@pytest.fixture
def mock_database():
    """Create a mock database for testing."""
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_bot():
    """Create a mock bot for testing."""
    mock = MagicMock()
    mock.bot = MagicMock()
    return mock


@pytest.fixture
def scheduler(mock_database, mock_bot):
    """Create a scheduler instance for testing."""
    from src.scheduler import NotificationScheduler
    return NotificationScheduler(mock_database, mock_bot)


@pytest.fixture
def sample_status():
    """Provide a sample intake status for testing."""
    return {
        "id": 1,
        "medication_id": 100,
        "name": "aspirin",
        "dosage": "100mg",
        "time": "10:00",
        "reminder_message_id": 12345,
        "reminder_sent_at": int(datetime.utcnow().timestamp()) - 3600
    }


def test_hourly_reminder_deletes_old_and_sends_new(scheduler, mock_database, mock_bot, sample_status):
    """Test that old message is deleted and new one is sent."""
    # Setup: delete succeeds, send succeeds
    mock_bot.bot.delete_message = AsyncMock(return_value=True)
    
    # Mock the send_message to return a message object with message_id
    mock_message = MagicMock()
    mock_message.message_id = 67890
    mock_bot.bot.send_message = AsyncMock(return_value=mock_message)
    
    mock_database.set_reminder_message_id = AsyncMock(return_value=True)
    mock_database.update_reminder_sent_at = AsyncMock(return_value=True)
    
    async def run_test():
        await scheduler._send_hourly_reminder(123, sample_status, "2024-01-01")
        
        # Verify old message was deleted
        mock_bot.bot.delete_message.assert_called_once_with(123, 12345)
        
        # Verify new message was sent
        mock_bot.bot.send_message.assert_called_once()
        call_args = mock_bot.bot.send_message.call_args
        assert call_args[0][0] == 123  # user_id
        assert "Напоминание" in call_args[0][1]  # message text
        assert "aspirin" in call_args[0][1].lower()
        
        # Verify database was updated with new message ID
        mock_database.set_reminder_message_id.assert_called_once_with(
            123, 100, "2024-01-01", 67890
        )
        
        # Verify timestamp was updated
        mock_database.update_reminder_sent_at.assert_called_once()
    
    asyncio.run(run_test())


def test_hourly_reminder_deletion_fails_but_still_sends(scheduler, mock_database, mock_bot, sample_status):
    """Test that when deletion fails, new message is still sent."""
    # Setup: delete fails, send succeeds
    mock_bot.bot.delete_message = AsyncMock(side_effect=Exception("Message already deleted"))
    
    # Mock the send_message to return a message object with message_id
    mock_message = MagicMock()
    mock_message.message_id = 67890
    mock_bot.bot.send_message = AsyncMock(return_value=mock_message)
    
    mock_database.set_reminder_message_id = AsyncMock(return_value=True)
    mock_database.update_reminder_sent_at = AsyncMock(return_value=True)
    
    async def run_test():
        await scheduler._send_hourly_reminder(123, sample_status, "2024-01-01")
        
        # Verify deletion was attempted (even though it failed)
        mock_bot.bot.delete_message.assert_called_once_with(123, 12345)
        
        # Verify new message was still sent despite deletion failure
        mock_bot.bot.send_message.assert_called_once()
        call_args = mock_bot.bot.send_message.call_args
        assert call_args[0][0] == 123  # user_id
        assert "Напоминание" in call_args[0][1]  # message text
        
        # Verify database was updated with new message ID
        mock_database.set_reminder_message_id.assert_called_once_with(
            123, 100, "2024-01-01", 67890
        )
        
        # Verify timestamp was updated
        mock_database.update_reminder_sent_at.assert_called_once()
    
    asyncio.run(run_test())


def test_hourly_reminder_no_existing_message(scheduler, mock_database, mock_bot):
    """Test that when there's no previous message, new message is sent normally."""
    # Setup: status without reminder_message_id
    status_no_message = {
        "id": 1,
        "medication_id": 100,
        "name": "aspirin",
        "dosage": "100mg",
        "time": "10:00",
        "reminder_message_id": None,  # No existing message
        "reminder_sent_at": int(datetime.utcnow().timestamp()) - 3600
    }
    
    # Mock the send_message to return a message object with message_id
    mock_message = MagicMock()
    mock_message.message_id = 67890
    mock_bot.bot.send_message = AsyncMock(return_value=mock_message)
    
    mock_database.set_reminder_message_id = AsyncMock(return_value=True)
    mock_database.update_reminder_sent_at = AsyncMock(return_value=True)
    
    async def run_test():
        await scheduler._send_hourly_reminder(123, status_no_message, "2024-01-01")
        
        # Verify deletion was NOT attempted (no existing message)
        mock_bot.bot.delete_message.assert_not_called()
        
        # Verify new message was sent
        mock_bot.bot.send_message.assert_called_once()
        call_args = mock_bot.bot.send_message.call_args
        assert call_args[0][0] == 123  # user_id
        assert "Напоминание" in call_args[0][1]  # message text
        
        # Verify database was updated with new message ID
        mock_database.set_reminder_message_id.assert_called_once_with(
            123, 100, "2024-01-01", 67890
        )
        
        # Verify timestamp was updated
        mock_database.update_reminder_sent_at.assert_called_once()
    
    asyncio.run(run_test())


def test_hourly_reminder_message_format(scheduler, mock_database, mock_bot, sample_status):
    """Test that reminder message has correct format with dosage information."""
    # Setup
    mock_bot.bot.delete_message = AsyncMock(return_value=True)
    
    mock_message = MagicMock()
    mock_message.message_id = 67890
    mock_bot.bot.send_message = AsyncMock(return_value=mock_message)
    
    mock_database.set_reminder_message_id = AsyncMock(return_value=True)
    mock_database.update_reminder_sent_at = AsyncMock(return_value=True)
    
    async def run_test():
        await scheduler._send_hourly_reminder(123, sample_status, "2024-01-01")
        
        # Verify message format
        call_args = mock_bot.bot.send_message.call_args
        message_text = call_args[0][1]
        
        assert "Напоминание" in message_text
        assert "Aspirin" in message_text  # Capitalized
        assert "100mg" in message_text  # Dosage included
    
    asyncio.run(run_test())


def test_hourly_reminder_without_dosage(scheduler, mock_database, mock_bot):
    """Test that reminder message works without dosage information."""
    # Setup: status without dosage
    status_no_dosage = {
        "id": 1,
        "medication_id": 100,
        "name": "aspirin",
        "dosage": None,  # No dosage
        "time": "10:00",
        "reminder_message_id": 12345,
        "reminder_sent_at": int(datetime.utcnow().timestamp()) - 3600
    }
    
    mock_bot.bot.delete_message = AsyncMock(return_value=True)
    
    mock_message = MagicMock()
    mock_message.message_id = 67890
    mock_bot.bot.send_message = AsyncMock(return_value=mock_message)
    
    mock_database.set_reminder_message_id = AsyncMock(return_value=True)
    mock_database.update_reminder_sent_at = AsyncMock(return_value=True)
    
    async def run_test():
        await scheduler._send_hourly_reminder(123, status_no_dosage, "2024-01-01")
        
        # Verify message format (without dosage)
        call_args = mock_bot.bot.send_message.call_args
        message_text = call_args[0][1]
        
        assert "Напоминание" in message_text
        assert "Aspirin" in message_text
        # Should not contain parentheses when no dosage
        assert message_text.count("(") == 0
    
    asyncio.run(run_test())


def test_hourly_reminder_inline_button_format(scheduler, mock_database, mock_bot, sample_status):
    """Test that reminder message includes correct inline button."""
    # Setup
    mock_bot.bot.delete_message = AsyncMock(return_value=True)
    
    mock_message = MagicMock()
    mock_message.message_id = 67890
    mock_bot.bot.send_message = AsyncMock(return_value=mock_message)
    
    mock_database.set_reminder_message_id = AsyncMock(return_value=True)
    mock_database.update_reminder_sent_at = AsyncMock(return_value=True)
    
    async def run_test():
        await scheduler._send_hourly_reminder(123, sample_status, "2024-01-01")
        
        # Verify inline keyboard
        call_args = mock_bot.bot.send_message.call_args
        keyboard = call_args[1]["reply_markup"]
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 1  # One row
        assert len(keyboard.inline_keyboard[0]) == 1  # One button
        
        button = keyboard.inline_keyboard[0][0]
        assert button.text == "Принял"
        assert button.callback_data == "taken:100:2024-01-01"
    
    asyncio.run(run_test())


def test_hourly_reminder_timestamp_not_updated_on_send_failure(scheduler, mock_database, mock_bot, sample_status):
    """Test that timestamp is not updated if message sending fails."""
    # Setup: delete succeeds, send fails
    mock_bot.bot.delete_message = AsyncMock(return_value=True)
    mock_bot.bot.send_message = AsyncMock(side_effect=Exception("Send failed"))
    
    mock_database.set_reminder_message_id = AsyncMock(return_value=True)
    mock_database.update_reminder_sent_at = AsyncMock(return_value=True)
    
    async def run_test():
        await scheduler._send_hourly_reminder(123, sample_status, "2024-01-01")
        
        # Verify deletion was attempted
        mock_bot.bot.delete_message.assert_called_once_with(123, 12345)
        
        # Verify send was attempted
        mock_bot.bot.send_message.assert_called_once()
        
        # Verify timestamp was NOT updated (since send failed)
        mock_database.update_reminder_sent_at.assert_not_called()
    
    asyncio.run(run_test())


def test_hourly_reminder_multiple_scenarios_integration(scheduler, mock_database, mock_bot):
    """Integration test covering multiple scenarios in sequence."""
    statuses = [
        # Scenario 1: Normal flow - delete succeeds, send succeeds
        {
            "id": 1,
            "medication_id": 100,
            "name": "medication1",
            "dosage": "100mg",
            "time": "10:00",
            "reminder_message_id": 1000,
            "reminder_sent_at": int(datetime.utcnow().timestamp()) - 3600
        },
        # Scenario 2: Delete fails, send succeeds
        {
            "id": 2,
            "medication_id": 200,
            "name": "medication2",
            "dosage": "200mg",
            "time": "11:00",
            "reminder_message_id": 2000,
            "reminder_sent_at": int(datetime.utcnow().timestamp()) - 3600
        },
        # Scenario 3: No existing message
        {
            "id": 3,
            "medication_id": 300,
            "name": "medication3",
            "dosage": "300mg",
            "time": "12:00",
            "reminder_message_id": None,
            "reminder_sent_at": int(datetime.utcnow().timestamp()) - 3600
        }
    ]
    
    async def run_test():
        # Scenario 1: Normal flow
        mock_bot.bot.delete_message = AsyncMock(return_value=True)
        
        mock_message = MagicMock()
        mock_message.message_id = 1001
        mock_bot.bot.send_message = AsyncMock(return_value=mock_message)
        
        mock_database.set_reminder_message_id = AsyncMock(return_value=True)
        mock_database.update_reminder_sent_at = AsyncMock(return_value=True)
        
        await scheduler._send_hourly_reminder(123, statuses[0], "2024-01-01")
        
        assert mock_bot.bot.delete_message.call_count == 1
        assert mock_bot.bot.send_message.call_count == 1
        
        # Reset mocks
        mock_bot.bot.reset_mock()
        mock_database.reset_mock()
        
        # Scenario 2: Delete fails, send succeeds
        mock_bot.bot.delete_message = AsyncMock(side_effect=Exception("Delete failed"))
        
        mock_message = MagicMock()
        mock_message.message_id = 2001
        mock_bot.bot.send_message = AsyncMock(return_value=mock_message)
        
        mock_database.set_reminder_message_id = AsyncMock(return_value=True)
        mock_database.update_reminder_sent_at = AsyncMock(return_value=True)
        
        await scheduler._send_hourly_reminder(123, statuses[1], "2024-01-01")
        
        assert mock_bot.bot.delete_message.call_count == 1
        assert mock_bot.bot.send_message.call_count == 1
        
        # Reset mocks
        mock_bot.bot.reset_mock()
        mock_database.reset_mock()
        
        # Scenario 3: No existing message
        mock_message = MagicMock()
        mock_message.message_id = 3001
        mock_bot.bot.send_message = AsyncMock(return_value=mock_message)
        
        mock_database.set_reminder_message_id = AsyncMock(return_value=True)
        mock_database.update_reminder_sent_at = AsyncMock(return_value=True)
        
        await scheduler._send_hourly_reminder(123, statuses[2], "2024-01-01")
        
        assert mock_bot.bot.delete_message.call_count == 0
        assert mock_bot.bot.send_message.call_count == 1
    
    asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])