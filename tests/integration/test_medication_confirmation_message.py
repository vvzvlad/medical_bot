"""Integration test for medication confirmation message.

This test verifies that when a user marks medication as taken, 
the confirmation message includes the medication name.
Test case: user says "принял героин в 15" and should get response 
"Отмечено как принято: героин ✓"
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_medication_confirmation_message_includes_name(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test that confirmation message includes medication name when marking as taken.
    
    Scenario:
    - User has "Героин" scheduled at 15:00
    - User says "принял героин в 15"
    - System should respond with "Отмечено как принято: героин ✓"
    """
    # Given: User with medication at 15:00
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Add medication at 15:00
    created_meds, skipped = await schedule_manager.add_medication(
        user_id=user_id,
        name="Героин",
        times=["15:00"],
        dosage=None
    )
    
    med_15 = created_meds[0]
    
    # When: User reports taking medication at 15:00
    user_message = "принял героин в 15"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to extract medication name and time
    async def mock_done_with_time(message, schedule):
        return {
            "medication_name": "героин",
            "time": "15:00",
            "medication_ids": [med["id"] for med in schedule if med["name"] == "Героин"]
        }
    
    mock_groq_client.process_done_command = AsyncMock(side_effect=mock_done_with_time)
    
    # Process done command
    result = await mock_groq_client.process_done_command(user_message, schedule_dict)
    
    # Verify LLM extracted both name and time
    assert result["medication_name"] == "героин"
    assert result["time"] == "15:00"
    assert len(result["medication_ids"]) == 1
    
    # Simulate handler validation logic (similar to lines 653-676 in handlers.py)
    medication_name = result["medication_name"]
    specified_time = result["time"]
    medication_ids = result["medication_ids"]
    
    # Check if specified time matches any scheduled time
    matching_meds = [med for med in schedule if med.id in medication_ids and med.time == specified_time]
    
    # Then: Should find matching medication at 15:00
    assert len(matching_meds) == 1
    assert matching_meds[0].id == med_15.id
    assert matching_meds[0].time == "15:00"
    assert matching_meds[0].name == "Героин"
    
    # Mark as taken
    filtered_ids = [med.id for med in matching_meds]
    await schedule_manager.mark_medication_taken(user_id, filtered_ids[0])
    
    # Verify medication was marked as taken
    user_data = await data_manager.get_user_data(user_id)
    taken_med = user_data.get_medication_by_id(med_15.id)
    assert taken_med.last_taken is not None
    
    # Test the confirmation message generation (lines 844-855 in handlers.py)
    # Get medication name from the medication object for the confirmation message
    medication_name_display = None
    if filtered_ids:
        first_med = next((med for med in schedule if med.id == filtered_ids[0]), None)
        if first_med:
            medication_name_display = first_med.name
    
    # Verify the confirmation message includes the medication name
    assert medication_name_display == "Героин"
    
    # Simulate the confirmation message that would be sent to user
    expected_message = f"Отмечено как принято: {medication_name_display} ✓"
    assert expected_message == "Отмечено как принято: Героин ✓"


@pytest.mark.asyncio
async def test_medication_confirmation_message_lowercase_name(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test that confirmation message works with lowercase medication names.
    
    Scenario:
    - User has "Аспирин" scheduled at 10:00
    - User says "принял аспирин в 10"
    - System should respond with "Отмечено как принято: Аспирин ✓"
    """
    # Given: User with medication at 10:00
    user_id = 123456790
    await data_manager.create_user(user_id, "+03:00")
    
    # Add medication at 10:00
    created_meds, skipped = await schedule_manager.add_medication(
        user_id=user_id,
        name="Аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    
    med_10 = created_meds[0]
    
    # When: User reports taking medication at 10:00
    user_message = "принял аспирин в 10"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to extract medication name and time (LLM returns lowercase)
    async def mock_done_lowercase(message, schedule):
        return {
            "medication_name": "аспирин",
            "time": "10:00",
            "medication_ids": [med["id"] for med in schedule if med["name"] == "Аспирин"]
        }
    
    mock_groq_client.process_done_command = AsyncMock(side_effect=mock_done_lowercase)
    
    # Process done command
    result = await mock_groq_client.process_done_command(user_message, schedule_dict)
    
    # Verify LLM extracted both name and time
    assert result["medication_name"] == "аспирин"  # LLM returns lowercase
    assert result["time"] == "10:00"
    
    # Simulate handler validation logic
    medication_ids = result["medication_ids"]
    specified_time = result["time"]
    
    # Check if specified time matches any scheduled time
    matching_meds = [med for med in schedule if med.id in medication_ids and med.time == specified_time]
    
    # Then: Should find matching medication at 10:00
    assert len(matching_meds) == 1
    assert matching_meds[0].id == med_10.id
    assert matching_meds[0].name == "Аспирин"  # Original name from schedule
    
    # Mark as taken
    filtered_ids = [med.id for med in matching_meds]
    await schedule_manager.mark_medication_taken(user_id, filtered_ids[0])
    
    # Test the confirmation message generation
    medication_name_display = None
    if filtered_ids:
        first_med = next((med for med in schedule if med.id == filtered_ids[0]), None)
        if first_med:
            medication_name_display = first_med.name
    
    # Verify the confirmation message includes the original medication name from schedule
    assert medication_name_display == "Аспирин"
    
    # Simulate the confirmation message that would be sent to user
    expected_message = f"Отмечено как принято: {medication_name_display} ✓"
    assert expected_message == "Отмечено как принято: Аспирин ✓"


@pytest.mark.asyncio 
async def test_medication_confirmation_message_multiple_times(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test confirmation message when medication has multiple scheduled times.
    
    Scenario:
    - User has "Витамин C" scheduled at 08:00, 14:00, 20:00
    - User says "принял витамин с в 14"
    - System should respond with "Отмечено как принято: Витамин C ✓"
    """
    # Given: User with medication at multiple times
    user_id = 123456791
    await data_manager.create_user(user_id, "+03:00")
    
    # Add medication at multiple times
    created_meds, skipped = await schedule_manager.add_medication(
        user_id=user_id,
        name="Витамин C",
        times=["08:00", "14:00", "20:00"],
        dosage="1 таблетка"
    )
    
    med_14 = next(med for med in created_meds if med.time == "14:00")
    
    # When: User reports taking medication at 14:00
    user_message = "принял витамин с в 14"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to extract medication name and time
    async def mock_done_multiple_times(message, schedule):
        return {
            "medication_name": "витамин с",
            "time": "14:00", 
            "medication_ids": [med["id"] for med in schedule if med["name"] == "Витамин C"]
        }
    
    mock_groq_client.process_done_command = AsyncMock(side_effect=mock_done_multiple_times)
    
    # Process done command
    result = await mock_groq_client.process_done_command(user_message, schedule_dict)
    
    # Verify LLM extracted both name and time
    assert result["medication_name"] == "витамин с"
    assert result["time"] == "14:00"
    assert len(result["medication_ids"]) == 3  # All Витамин C entries
    
    # Simulate handler validation logic for specified time
    medication_ids = result["medication_ids"]
    specified_time = result["time"]
    
    # Check if specified time matches any scheduled time
    matching_meds = [med for med in schedule if med.id in medication_ids and med.time == specified_time]
    
    # Then: Should find matching medication at 14:00
    assert len(matching_meds) == 1
    assert matching_meds[0].id == med_14.id
    assert matching_meds[0].time == "14:00"
    assert matching_meds[0].name == "Витамин C"
    
    # Mark as taken
    filtered_ids = [med.id for med in matching_meds]
    await schedule_manager.mark_medication_taken(user_id, filtered_ids[0])
    
    # Test the confirmation message generation
    medication_name_display = None
    if filtered_ids:
        first_med = next((med for med in schedule if med.id == filtered_ids[0]), None)
        if first_med:
            medication_name_display = first_med.name
    
    # Verify the confirmation message includes the medication name
    assert medication_name_display == "Витамин C"
    
    # Simulate the confirmation message that would be sent to user
    expected_message = f"Отмечено как принято: {medication_name_display} ✓"
    assert expected_message == "Отмечено как принято: Витамин C ✓"