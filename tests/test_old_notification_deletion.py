"""Simple test to verify old notification deletion functionality."""

import pytest
from unittest.mock import MagicMock, AsyncMock
import asyncio


def test_old_notification_deletion_logic():
    """Test that the old notification deletion logic is implemented correctly."""
    # Mock the database and bot
    mock_db = MagicMock()
    mock_bot = MagicMock()
    mock_bot.bot = MagicMock()
    
    # Create scheduler instance
    from src.scheduler import NotificationScheduler
    scheduler = NotificationScheduler(mock_db, mock_bot)
    
    # Test case: existing status with old message ID
    mock_status = {
        "reminder_message_id": 12345,
        "medication_id": 1,
        "name": "aspirin",
        "dosage": "100mg"
    }
    
    # Mock the methods
    mock_db.get_intake_status = AsyncMock(return_value=mock_status)
    mock_bot.send_notification = AsyncMock(return_value=67890)
    mock_db.set_reminder_message_id = AsyncMock(return_value=True)
    
    # Test the _send_notification method
    medication = {"id": 1, "name": "aspirin", "dosage": "100mg", "time": "11:00"}
    
    async def run_test():
        await scheduler._send_notification(123, medication, "2024-01-01")
        
        # Verify old message was deleted
        mock_bot.bot.delete_message.assert_called_once_with(123, 12345)
        # Verify new message was sent
        mock_bot.send_notification.assert_called_once_with(123, medication, "2024-01-01")
        # Verify database was updated with new message ID
        mock_db.set_reminder_message_id.assert_called_once_with(123, 1, "2024-01-01", 67890)
    
    # Run the async test
    asyncio.run(run_test())


def test_no_old_notification_no_deletion():
    """Test that no deletion occurs when there's no old notification."""
    # Mock the database and bot
    mock_db = MagicMock()
    mock_bot = MagicMock()
    mock_bot.bot = MagicMock()
    
    # Create scheduler instance
    from src.scheduler import NotificationScheduler
    scheduler = NotificationScheduler(mock_db, mock_bot)
    
    # Test case: no existing status
    mock_db.get_intake_status = AsyncMock(return_value=None)
    mock_bot.send_notification = AsyncMock(return_value=67890)
    mock_db.create_intake_status = AsyncMock(return_value=1)
    
    # Test the _send_notification method
    medication = {"id": 1, "name": "aspirin", "dosage": "100mg", "time": "11:00"}
    
    async def run_test():
        await scheduler._send_notification(123, medication, "2024-01-01")
        
        # Verify no deletion was attempted
        mock_bot.bot.delete_message.assert_not_called()
        # Verify new message was sent
        mock_bot.send_notification.assert_called_once_with(123, medication, "2024-01-01")
        # Verify new intake status was created
        mock_db.create_intake_status.assert_called_once_with(123, 1, "2024-01-01", 67890)
    
    # Run the async test
    asyncio.run(run_test())


if __name__ == "__main__":
    test_old_notification_deletion_logic()
    test_no_old_notification_no_deletion()
    print("✓ All tests passed: Old notification deletion functionality is working correctly!")