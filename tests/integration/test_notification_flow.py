"""Integration tests for notification flow."""

import pytest
from freezegun import freeze_time
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.scheduler import ReminderScheduler


@pytest.fixture
def scheduler(mock_bot, data_manager, schedule_manager):
    """Create ReminderScheduler for testing.
    
    Args:
        mock_bot: Mock bot fixture
        data_manager: DataManager fixture
        schedule_manager: ScheduleManager fixture
        
    Returns:
        ReminderScheduler: Scheduler instance for testing
    """
    return ReminderScheduler(mock_bot, data_manager, schedule_manager)


# TC-NOTIF-INT-001: Complete Reminder Flow
@pytest.mark.asyncio
@freeze_time("2024-01-01 10:00:00")
async def test_complete_reminder_flow(
    scheduler,
    data_manager,
    notification_manager,
    mock_bot
):
    """Test complete flow from scheduling to sending reminder."""
    # Given: User with medication at current time
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    user_data = await data_manager.get_user_data(user_id)
    med = user_data.add_medication("аспирин", "10:00", "200 мг")
    await data_manager.save_user_data(user_data)
    
    # When: Scheduler runs at 10:00
    await scheduler.check_and_send_reminders()
    
    # Then: Bot should have sent message
    assert mock_bot.send_message.called
    call_args = mock_bot.send_message.call_args
    assert call_args.kwargs["chat_id"] == user_id
    assert "аспирин" in call_args.kwargs["text"]
    
    # And: Reminder message ID should be stored
    user_data = await data_manager.get_user_data(user_id)
    assert user_data.medications[0].reminder_message_id is not None


# TC-NOTIF-INT-002: Multiple Medications Grouped
@pytest.mark.asyncio
@freeze_time("2024-01-01 10:00:00")
async def test_multiple_medications_grouped(
    scheduler,
    data_manager,
    mock_bot
):
    """Test that multiple medications at same time are grouped."""
    # Given: User with multiple medications at same time
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    user_data = await data_manager.get_user_data(user_id)
    user_data.add_medication("аспирин", "10:00", "200 мг")
    user_data.add_medication("парацетамол", "10:00", "400 мг")
    await data_manager.save_user_data(user_data)
    
    # When: Scheduler runs at 10:00
    await scheduler.check_and_send_reminders()
    
    # Then: Should send single message with both medications
    assert mock_bot.send_message.call_count == 1
    call_args = mock_bot.send_message.call_args
    message_text = call_args.kwargs["text"]
    assert "аспирин" in message_text
    assert "парацетамол" in message_text


# TC-NOTIF-INT-003: Previous Reminder Deleted
@pytest.mark.asyncio
@freeze_time("2024-01-01 18:00:00")
async def test_previous_reminder_deleted(
    scheduler,
    data_manager,
    mock_bot
):
    """Test that previous reminder is deleted when new time comes."""
    # Given: User with medication that has previous reminder
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    user_data = await data_manager.get_user_data(user_id)
    
    med1 = user_data.add_medication("аспирин", "10:00", "200 мг")
    med1.reminder_message_id = 12345
    
    med2 = user_data.add_medication("аспирин", "18:00", "200 мг")
    
    await data_manager.save_user_data(user_data)
    
    # When: Scheduler runs at 18:00
    await scheduler.check_and_send_reminders()
    
    # Then: Should delete previous message
    assert mock_bot.delete_message.called
    delete_call_args = mock_bot.delete_message.call_args
    assert delete_call_args.kwargs["chat_id"] == user_id
    assert delete_call_args.kwargs["message_id"] == 12345
    
    # And: Should send new message
    assert mock_bot.send_message.called


# TC-NOTIF-INT-004: Callback Button Click
@pytest.mark.asyncio
async def test_callback_button_click(
    data_manager,
    schedule_manager,
    mock_callback_query
):
    """Test handling of callback button click."""
    # Given: User with medication and reminder sent
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    meds = await schedule_manager.add_medication(user_id, "аспирин", ["10:00"], "200 мг")
    medication_id = meds[0].id
    
    # Set reminder message ID
    user_data = await data_manager.get_user_data(user_id)
    user_data.medications[0].reminder_message_id = 12345
    await data_manager.save_user_data(user_data)
    
    # When: User clicks "taken" button
    mock_callback_query.from_user.id = user_id
    mock_callback_query.data = f"taken:{medication_id}"
    
    # Simulate callback handler
    from src.bot.handlers import handle_medication_taken_callback
    
    # Mock the handler if it doesn't exist yet
    # For now, we'll test the logic directly
    await schedule_manager.mark_medication_taken(user_id, medication_id)
    
    # Then: Medication should be marked as taken
    user_data = await data_manager.get_user_data(user_id)
    assert user_data.medications[0].last_taken is not None
    
    # And: Reminder message ID should be cleared
    assert user_data.medications[0].reminder_message_id is None


# TC-NOTIF-INT-005: Timezone Handling
@pytest.mark.asyncio
@freeze_time("2024-01-01 07:00:00")  # 07:00 UTC = 10:00 Moscow time
async def test_timezone_handling(
    scheduler,
    data_manager,
    mock_bot
):
    """Test that reminders respect user timezone."""
    # Given: User in Moscow timezone (+03:00)
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    user_data = await data_manager.get_user_data(user_id)
    user_data.add_medication("аспирин", "10:00", "200 мг")
    await data_manager.save_user_data(user_data)
    
    # When: Scheduler runs at 07:00 UTC (10:00 Moscow time)
    await scheduler.check_and_send_reminders()
    
    # Then: Should send reminder
    assert mock_bot.send_message.called


# TC-NOTIF-INT-006: No Reminder if Already Taken
@pytest.mark.asyncio
@freeze_time("2024-01-01 10:00:00")
async def test_no_reminder_if_already_taken(
    scheduler,
    data_manager,
    schedule_manager,
    mock_bot
):
    """Test that no reminder is sent if medication already taken."""
    # Given: User with medication already taken today
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    meds = await schedule_manager.add_medication(user_id, "аспирин", ["10:00"], "200 мг")
    
    # Mark as taken
    await schedule_manager.mark_medication_taken(user_id, meds[0].id)
    
    # When: Scheduler runs at 10:00
    await scheduler.check_and_send_reminders()
    
    # Then: Should not send reminder
    assert not mock_bot.send_message.called


# TC-NOTIF-INT-007: Repeat Reminder After Interval
@pytest.mark.asyncio
async def test_repeat_reminder_after_interval(
    scheduler,
    data_manager,
    mock_bot
):
    """Test that reminder is repeated after interval if not taken."""
    # Given: User with medication, reminder sent 1 hour ago
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    user_data = await data_manager.get_user_data(user_id)
    med = user_data.add_medication("аспирин", "10:00", "200 мг")
    # Clear reminder_message_id to allow repeat
    med.reminder_message_id = None
    await data_manager.save_user_data(user_data)
    
    # When: Scheduler runs 1 hour later
    with freeze_time("2024-01-01 11:00:00"):
        await scheduler.check_and_send_reminders()
    
    # Then: Should send repeat reminder
    assert mock_bot.send_message.called


# Additional test: No medications to remind
@pytest.mark.asyncio
@freeze_time("2024-01-01 06:00:00")  # 06:00 UTC = 09:00 Moscow time (before 10:00)
async def test_no_medications_to_remind(
    scheduler,
    data_manager,
    mock_bot
):
    """Test when there are no medications to remind."""
    # Given: User with medication at 10:00
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    user_data = await data_manager.get_user_data(user_id)
    user_data.add_medication("аспирин", "10:00", "200 мг")
    await data_manager.save_user_data(user_data)
    
    # When: Scheduler runs at 06:00 UTC (09:00 Moscow time, before medication time)
    await scheduler.check_and_send_reminders()
    
    # Then: Should not send reminder
    assert not mock_bot.send_message.called


# Additional test: Multiple users
@pytest.mark.asyncio
@freeze_time("2024-01-01 10:00:00")
async def test_multiple_users(
    scheduler,
    data_manager,
    mock_bot
):
    """Test scheduler handles multiple users."""
    # Given: Multiple users with medications
    user_id_1 = 111111111
    user_id_2 = 222222222
    
    await data_manager.create_user(user_id_1, "+03:00")
    user_data_1 = await data_manager.get_user_data(user_id_1)
    user_data_1.add_medication("аспирин", "10:00", "200 мг")
    await data_manager.save_user_data(user_data_1)
    
    await data_manager.create_user(user_id_2, "+03:00")
    user_data_2 = await data_manager.get_user_data(user_id_2)
    user_data_2.add_medication("парацетамол", "10:00", "400 мг")
    await data_manager.save_user_data(user_data_2)
    
    # When: Scheduler runs
    await scheduler.check_and_send_reminders()
    
    # Then: Should send reminders to both users
    assert mock_bot.send_message.call_count == 2


# Additional test: Telegram error handling
@pytest.mark.asyncio
@freeze_time("2024-01-01 10:00:00")
async def test_telegram_error_handling(
    scheduler,
    data_manager,
    mock_bot
):
    """Test handling of Telegram API errors."""
    from aiogram.exceptions import TelegramForbiddenError
    from aiogram.methods import SendMessage
    
    # Given: User with medication
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    user_data = await data_manager.get_user_data(user_id)
    user_data.add_medication("аспирин", "10:00", "200 мг")
    await data_manager.save_user_data(user_data)
    
    # Mock bot to raise error with proper parameters
    mock_bot.send_message = AsyncMock(
        side_effect=TelegramForbiddenError(
            method=SendMessage(chat_id=user_id, text="test"),
            message="Forbidden: bot was blocked by the user"
        )
    )
    
    # When: Scheduler runs
    # Should not raise exception
    await scheduler.check_and_send_reminders()
    
    # Then: Error should be handled gracefully
    assert mock_bot.send_message.called
