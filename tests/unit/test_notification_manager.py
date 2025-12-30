"""Unit tests for notification manager."""

from datetime import datetime

import pytest
from freezegun import freeze_time

from src.data.models import Medication


# TC-NOTIF-001: Get Medications to Remind
@pytest.mark.asyncio
@freeze_time("2024-01-01 10:00:00")
async def test_get_medications_to_remind(notification_manager, data_manager):
    """Test getting medications that need reminders."""
    # Given: User with medications at different times
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    user_data = await data_manager.get_user_data(user_id)
    
    # Add medications
    med1 = user_data.add_medication("аспирин", "10:00", "200 мг")
    med2 = user_data.add_medication("парацетамол", "18:00", "400 мг")
    await data_manager.save_user_data(user_data)
    
    # When: Getting medications to remind at 10:00
    medications = await notification_manager.get_medications_to_remind(user_id)
    
    # Then: Should return only med1
    assert len(medications) == 1
    assert medications[0].name == "аспирин"


# TC-NOTIF-002: Should Send Reminder - Time Match
def test_should_send_reminder_time_match(notification_manager):
    """Test reminder should be sent when time matches."""
    # Given: Medication at 10:00, current time is 10:00
    medication = Medication(
        id=1,
        name="аспирин",
        dosage="200 мг",
        time="10:00",
        last_taken=None,
        reminder_message_id=None
    )
    current_time = datetime(2024, 1, 1, 10, 0, 0)
    timezone_offset = "+03:00"
    
    # When: Checking if reminder should be sent
    should_send = notification_manager.should_send_reminder(medication, current_time, timezone_offset)
    
    # Then: Should return True
    assert should_send is True


# TC-NOTIF-003: Should Not Send - Already Taken
def test_should_not_send_reminder_already_taken(notification_manager):
    """Test reminder should not be sent if already taken today."""
    # Given: Medication already taken today
    medication = Medication(
        id=1,
        name="аспирин",
        dosage="200 мг",
        time="10:00",
        last_taken=int(datetime(2024, 1, 1, 9, 0, 0).timestamp()),
        reminder_message_id=None
    )
    current_time = datetime(2024, 1, 1, 10, 0, 0)
    timezone_offset = "+03:00"
    
    # When: Checking if reminder should be sent
    should_send = notification_manager.should_send_reminder(medication, current_time, timezone_offset)
    
    # Then: Should return False
    assert should_send is False


# TC-NOTIF-004: Should Not Send - Reminder Already Sent
def test_should_not_send_reminder_already_sent(notification_manager):
    """Test reminder should not be sent if already sent recently."""
    # Given: Medication with recent reminder
    medication = Medication(
        id=1,
        name="аспирин",
        dosage="200 мг",
        time="10:00",
        last_taken=None,
        reminder_message_id=12345  # Reminder already sent
    )
    current_time = datetime(2024, 1, 1, 10, 0, 0)
    timezone_offset = "+03:00"
    
    # When: Checking if reminder should be sent
    should_send = notification_manager.should_send_reminder(medication, current_time, timezone_offset)
    
    # Then: Should return False
    assert should_send is False


# TC-NOTIF-005: Format Reminder Message Single
def test_format_reminder_message_single(notification_manager):
    """Test formatting reminder message for single medication."""
    # Given: Single medication
    medications = [
        Medication(id=1, name="аспирин", dosage="200 мг", time="10:00")
    ]
    
    # When: Formatting message
    message = notification_manager.format_reminder_message(medications)
    
    # Then: Message should be formatted correctly
    assert "Надо принять:" in message
    assert "аспирин 200 мг" in message


# TC-NOTIF-006: Format Reminder Message Multiple
def test_format_reminder_message_multiple(notification_manager):
    """Test formatting reminder message for multiple medications."""
    # Given: Multiple medications
    medications = [
        Medication(id=1, name="аспирин", dosage="200 мг", time="10:00"),
        Medication(id=2, name="парацетамол", dosage=None, time="10:00")
    ]
    
    # When: Formatting message
    message = notification_manager.format_reminder_message(medications)
    
    # Then: Message should include both medications
    assert "Надо принять:" in message
    assert "аспирин 200 мг" in message
    assert "парацетамол" in message


# TC-NOTIF-007: Create Reminder Keyboard
def test_create_reminder_keyboard(notification_manager):
    """Test creating inline keyboard for reminder."""
    # Given: Medications
    medications = [
        Medication(id=1, name="аспирин", dosage="200 мг", time="10:00"),
        Medication(id=2, name="парацетамол", dosage=None, time="10:00")
    ]
    
    # When: Creating keyboard
    keyboard = notification_manager.create_reminder_keyboard(medications)
    
    # Then: Keyboard should have buttons for each medication
    assert len(keyboard["inline_keyboard"]) == 2
    assert keyboard["inline_keyboard"][0][0]["text"] == "аспирин"
    assert keyboard["inline_keyboard"][0][0]["callback_data"] == "taken:1"
    assert keyboard["inline_keyboard"][1][0]["text"] == "парацетамол"
    assert keyboard["inline_keyboard"][1][0]["callback_data"] == "taken:2"


# TC-NOTIF-008: Set Reminder Message ID
@pytest.mark.asyncio
async def test_set_reminder_message_id(notification_manager, data_manager):
    """Test setting reminder message ID."""
    # Given: User with medication
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    user_data = await data_manager.get_user_data(user_id)
    med = user_data.add_medication("аспирин", "10:00", "200 мг")
    await data_manager.save_user_data(user_data)
    
    # When: Setting reminder message ID
    message_id = 12345
    await notification_manager.set_reminder_message_id(user_id, med.id, message_id)
    
    # Then: Message ID should be set
    user_data = await data_manager.get_user_data(user_id)
    assert user_data.medications[0].reminder_message_id == message_id


# TC-NOTIF-009: Clear Reminder Message ID
@pytest.mark.asyncio
async def test_clear_reminder_message_id(notification_manager, data_manager):
    """Test clearing reminder message ID."""
    # Given: User with medication with reminder
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    user_data = await data_manager.get_user_data(user_id)
    med = user_data.add_medication("аспирин", "10:00", "200 мг")
    med.reminder_message_id = 12345
    await data_manager.save_user_data(user_data)
    
    # When: Clearing reminder message ID
    await notification_manager.clear_reminder_message_id(user_id, med.id)
    
    # Then: Message ID should be cleared
    user_data = await data_manager.get_user_data(user_id)
    assert user_data.medications[0].reminder_message_id is None


# TC-NOTIF-010: Should Delete Previous Reminder
@pytest.mark.asyncio
async def test_should_delete_previous_reminder(notification_manager, data_manager):
    """Test checking if previous reminder should be deleted."""
    # Given: User with two medications with same name
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    user_data = await data_manager.get_user_data(user_id)
    
    med1 = user_data.add_medication("аспирин", "10:00", "200 мг")
    med1.reminder_message_id = 12345
    
    med2 = user_data.add_medication("аспирин", "18:00", "200 мг")
    
    await data_manager.save_user_data(user_data)
    
    # When: Checking if previous reminder should be deleted
    message_id = await notification_manager.should_delete_previous_reminder(
        user_id, "аспирин", med2.id
    )
    
    # Then: Should return previous message ID
    assert message_id == 12345


# Additional test: Get medications by name
@pytest.mark.asyncio
async def test_get_medications_by_name(notification_manager, data_manager):
    """Test getting medications by name."""
    # Given: User with multiple medications
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    user_data = await data_manager.get_user_data(user_id)
    
    user_data.add_medication("аспирин", "10:00", "200 мг")
    user_data.add_medication("аспирин", "18:00", "200 мг")
    user_data.add_medication("парацетамол", "12:00", "400 мг")
    
    await data_manager.save_user_data(user_data)
    
    # When: Getting medications by name
    medications = await notification_manager.get_medications_by_name(user_id, "аспирин")
    
    # Then: Should return only aspirin medications
    assert len(medications) == 2
    assert all(med.name == "аспирин" for med in medications)


# Additional test: Find closest medication by time
@pytest.mark.asyncio
@freeze_time("2024-01-01 10:30:00")
async def test_find_closest_medication_by_time(notification_manager, data_manager):
    """Test finding medication closest to current time."""
    # Given: User with multiple medications at different times
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    user_data = await data_manager.get_user_data(user_id)
    
    med1 = user_data.add_medication("аспирин", "10:00", "200 мг")
    med2 = user_data.add_medication("аспирин", "11:00", "200 мг")
    med3 = user_data.add_medication("аспирин", "18:00", "200 мг")
    
    await data_manager.save_user_data(user_data)
    
    # When: Finding closest medication at 10:30
    closest = await notification_manager.find_closest_medication_by_time(
        user_id, [med1.id, med2.id, med3.id]
    )
    
    # Then: Should return med2 (11:00 is closest to 10:30)
    assert closest.id == med2.id
    assert closest.time == "11:00"


# Additional test: Empty medications list
def test_format_reminder_message_empty(notification_manager):
    """Test formatting reminder message with empty list."""
    # Given: Empty medications list
    medications = []
    
    # When: Formatting message
    message = notification_manager.format_reminder_message(medications)
    
    # Then: Should return empty string
    assert message == ""


# Additional test: Empty keyboard
def test_create_reminder_keyboard_empty(notification_manager):
    """Test creating keyboard with empty medications list."""
    # Given: Empty medications list
    medications = []
    
    # When: Creating keyboard
    keyboard = notification_manager.create_reminder_keyboard(medications)
    
    # Then: Should return empty keyboard
    assert keyboard == {"inline_keyboard": []}
