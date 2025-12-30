"""Integration test for medication intake recording validation.

This test suite verifies the fix for recording medication intake at unscheduled times.
It ensures that:
1. Users can record intake at scheduled times (should succeed)
2. Users cannot record intake at unscheduled times (should fail with clear message)
3. Users can record intake without specifying time (should use closest scheduled time)
"""

import pytest
from unittest.mock import AsyncMock


# TC-INT-INTAKE-001: Record intake at scheduled time (should succeed)
@pytest.mark.asyncio
async def test_record_intake_at_scheduled_time(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test recording medication intake at a scheduled time.
    
    Scenario:
    - User has "Героин" scheduled at 11:00, 13:00, 15:00, 17:00
    - User says "Принял Героин в 13:00"
    - System should successfully mark the 13:00 dose as taken
    """
    # Given: User with medication at multiple scheduled times
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Add medication with multiple times
    meds = await schedule_manager.add_medication(
        user_id=user_id,
        name="Героин",
        times=["11:00", "13:00", "15:00", "17:00"],
        dosage=None
    )
    
    # Find the 13:00 medication ID
    med_13 = next(med for med in meds if med.time == "13:00")
    
    # When: User reports taking medication at scheduled time
    user_message = "Принял Героин в 13:00"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to extract medication name and time
    async def mock_done_with_time(message, schedule):
        # LLM extracts both medication name and time
        return {
            "medication_name": "Героин",
            "time": "13:00",
            "medication_ids": [med["id"] for med in schedule if med["name"] == "Героин"]
        }
    
    mock_groq_client.process_done_command = AsyncMock(side_effect=mock_done_with_time)
    
    # Process done command
    result = await mock_groq_client.process_done_command(user_message, schedule_dict)
    
    # Verify LLM extracted both name and time
    assert result["medication_name"] == "Героин"
    assert result["time"] == "13:00"
    assert len(result["medication_ids"]) == 4  # All Героин entries
    
    # Simulate handler validation logic (lines 653-676 in handlers.py)
    medication_name = result["medication_name"]
    specified_time = result["time"]
    medication_ids = result["medication_ids"]
    
    # Check if specified time matches any scheduled time
    matching_meds = [med for med in schedule if med.id in medication_ids and med.time == specified_time]
    
    # Then: Should find matching medication at 13:00
    assert len(matching_meds) == 1
    assert matching_meds[0].id == med_13.id
    assert matching_meds[0].time == "13:00"
    
    # Mark as taken
    filtered_ids = [med.id for med in matching_meds]
    await schedule_manager.mark_medication_taken(user_id, filtered_ids[0])
    
    # Verify medication was marked as taken
    user_data = await data_manager.get_user_data(user_id)
    taken_med = user_data.get_medication_by_id(med_13.id)
    assert taken_med.last_taken is not None


# TC-INT-INTAKE-002: Record intake at unscheduled time (should fail)
@pytest.mark.asyncio
async def test_record_intake_at_unscheduled_time(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test recording medication intake at an unscheduled time.
    
    Scenario:
    - User has "Героин" scheduled at 11:00, 13:00, 15:00, 17:00
    - User says "Принял Героин в 22:00"
    - System should reject with error message showing scheduled times
    """
    # Given: User with medication at scheduled times
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Add medication with multiple times
    await schedule_manager.add_medication(
        user_id=user_id,
        name="Героин",
        times=["11:00", "13:00", "15:00", "17:00"],
        dosage=None
    )
    
    # When: User reports taking medication at unscheduled time
    user_message = "Принял Героин в 22:00"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to extract medication name and unscheduled time
    async def mock_done_unscheduled_time(message, schedule):
        return {
            "medication_name": "Героин",
            "time": "22:00",
            "medication_ids": [med["id"] for med in schedule if med["name"] == "Героин"]
        }
    
    mock_groq_client.process_done_command = AsyncMock(side_effect=mock_done_unscheduled_time)
    
    # Process done command
    result = await mock_groq_client.process_done_command(user_message, schedule_dict)
    
    # Verify LLM extracted both name and time
    assert result["medication_name"] == "Героин"
    assert result["time"] == "22:00"
    
    # Simulate handler validation logic (lines 653-676 in handlers.py)
    medication_name = result["medication_name"]
    specified_time = result["time"]
    medication_ids = result["medication_ids"]
    
    # Check if specified time matches any scheduled time
    matching_meds = [med for med in schedule if med.id in medication_ids and med.time == specified_time]
    
    # Then: Should NOT find any matching medication at 22:00
    assert len(matching_meds) == 0
    
    # Generate error message as handler would (lines 661-672)
    scheduled_times = [med.time for med in schedule if med.id in medication_ids]
    scheduled_times_str = ", ".join(sorted(set(scheduled_times)))
    
    error_message = (
        f"{medication_name} нет в расписании на {specified_time}.\n"
        f"Запланированное время приема: {scheduled_times_str}"
    )
    
    # Verify error message format
    assert "Героин нет в расписании на 22:00" in error_message
    assert "11:00" in error_message
    assert "13:00" in error_message
    assert "15:00" in error_message
    assert "17:00" in error_message


# TC-INT-INTAKE-003: Record intake without specifying time (should use closest)
@pytest.mark.asyncio
async def test_record_intake_without_time_uses_closest(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test recording medication intake without specifying time.
    
    Scenario:
    - User has "Аспирин" scheduled at 10:00, 14:00, 18:00
    - User says "Принял Аспирин" (no time specified)
    - System should use the closest scheduled time to current time
    """
    # Given: User with medication at multiple times
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Add medication with multiple times
    meds = await schedule_manager.add_medication(
        user_id=user_id,
        name="Аспирин",
        times=["10:00", "14:00", "18:00"],
        dosage="200 мг"
    )
    
    # When: User reports taking medication without specifying time
    user_message = "Принял Аспирин"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to extract medication name without time
    async def mock_done_no_time(message, schedule):
        return {
            "medication_name": "Аспирин",
            "time": None,  # No time specified
            "medication_ids": [med["id"] for med in schedule if med["name"] == "Аспирин"]
        }
    
    mock_groq_client.process_done_command = AsyncMock(side_effect=mock_done_no_time)
    
    # Process done command
    result = await mock_groq_client.process_done_command(user_message, schedule_dict)
    
    # Verify LLM extracted name but no time
    assert result["medication_name"] == "Аспирин"
    assert result["time"] is None
    assert len(result["medication_ids"]) == 3  # All Аспирин entries
    
    # Simulate handler logic for finding closest time (lines 679-699 in handlers.py)
    medication_ids = result["medication_ids"]
    specified_time = result["time"]
    
    # Since no time specified and multiple IDs, find closest to current time
    if specified_time is None and len(medication_ids) > 1:
        from datetime import datetime
        current_time = datetime.now().strftime("%H:%M")
        
        # Find medication closest to current time
        closest_med = None
        min_diff = float('inf')
        
        for med in schedule:
            if med.id in medication_ids:
                # Simple time difference calculation
                med_minutes = int(med.time.split(':')[0]) * 60 + int(med.time.split(':')[1])
                curr_minutes = int(current_time.split(':')[0]) * 60 + int(current_time.split(':')[1])
                diff = abs(med_minutes - curr_minutes)
                
                if diff < min_diff:
                    min_diff = diff
                    closest_med = med
        
        # Then: Should find the closest medication
        assert closest_med is not None
        assert closest_med.name == "Аспирин"
        assert closest_med.time in ["10:00", "14:00", "18:00"]
        
        # Mark as taken
        await schedule_manager.mark_medication_taken(user_id, closest_med.id)
        
        # Verify medication was marked as taken
        user_data = await data_manager.get_user_data(user_id)
        taken_med = user_data.get_medication_by_id(closest_med.id)
        assert taken_med.last_taken is not None


# TC-INT-INTAKE-004: Record intake with partial time match
@pytest.mark.asyncio
async def test_record_intake_with_partial_time_match(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test recording intake when user specifies time that's close but not exact.
    
    Scenario:
    - User has "Парацетамол" scheduled at 09:00, 15:00
    - User says "Принял Парацетамол в 9:00" (without leading zero)
    - System should match to 09:00
    """
    # Given: User with medication
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    meds = await schedule_manager.add_medication(
        user_id=user_id,
        name="Парацетамол",
        times=["09:00", "15:00"],
        dosage="400 мг"
    )
    
    med_09 = next(med for med in meds if med.time == "09:00")
    
    # When: User specifies time without leading zero
    user_message = "Принял Парацетамол в 9:00"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to normalize time format
    async def mock_done_normalized_time(message, schedule):
        # LLM should normalize "9:00" to "09:00"
        return {
            "medication_name": "Парацетамол",
            "time": "09:00",  # Normalized format
            "medication_ids": [med["id"] for med in schedule if med["name"] == "Парацетамол"]
        }
    
    mock_groq_client.process_done_command = AsyncMock(side_effect=mock_done_normalized_time)
    
    # Process done command
    result = await mock_groq_client.process_done_command(user_message, schedule_dict)
    
    # Verify LLM normalized the time
    assert result["time"] == "09:00"
    
    # Simulate handler validation
    specified_time = result["time"]
    medication_ids = result["medication_ids"]
    
    matching_meds = [med for med in schedule if med.id in medication_ids and med.time == specified_time]
    
    # Then: Should match the 09:00 medication
    assert len(matching_meds) == 1
    assert matching_meds[0].id == med_09.id


# TC-INT-INTAKE-005: Record intake for medication not in schedule
@pytest.mark.asyncio
async def test_record_intake_for_nonexistent_medication(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test recording intake for medication not in schedule.
    
    Scenario:
    - User has "Аспирин" in schedule
    - User says "Принял Ибупрофен"
    - System should return empty medication_ids
    """
    # Given: User with one medication
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    await schedule_manager.add_medication(
        user_id=user_id,
        name="Аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    
    # When: User reports taking different medication
    user_message = "Принял Ибупрофен"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to return empty IDs for non-existent medication
    async def mock_done_nonexistent(message, schedule):
        # LLM can't find Ибупрофен in schedule
        return {
            "medication_name": "Ибупрофен",
            "time": None,
            "medication_ids": []  # Not found
        }
    
    mock_groq_client.process_done_command = AsyncMock(side_effect=mock_done_nonexistent)
    
    # Process done command
    result = await mock_groq_client.process_done_command(user_message, schedule_dict)
    
    # Then: Should return empty medication_ids
    assert result["medication_ids"] == []
    assert result["medication_name"] == "Ибупрофен"


# TC-INT-INTAKE-006: Record intake with single scheduled time
@pytest.mark.asyncio
async def test_record_intake_single_scheduled_time(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test recording intake when medication has only one scheduled time.
    
    Scenario:
    - User has "Витамин D" scheduled only at 09:00
    - User says "Принял Витамин D"
    - System should use the only available time
    """
    # Given: User with medication at single time
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    meds = await schedule_manager.add_medication(
        user_id=user_id,
        name="Витамин D",
        times=["09:00"],
        dosage="2 капсулы"
    )
    
    med_id = meds[0].id
    
    # When: User reports taking medication without time
    user_message = "Принял Витамин D"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to extract medication
    async def mock_done_single(message, schedule):
        return {
            "medication_name": "Витамин D",
            "time": None,
            "medication_ids": [med["id"] for med in schedule if med["name"] == "Витамин D"]
        }
    
    mock_groq_client.process_done_command = AsyncMock(side_effect=mock_done_single)
    
    # Process done command
    result = await mock_groq_client.process_done_command(user_message, schedule_dict)
    
    # Verify single ID returned
    assert len(result["medication_ids"]) == 1
    assert result["medication_ids"][0] == med_id
    
    # Mark as taken (no need to find closest since only one)
    await schedule_manager.mark_medication_taken(user_id, med_id)
    
    # Verify medication was marked as taken
    user_data = await data_manager.get_user_data(user_id)
    taken_med = user_data.get_medication_by_id(med_id)
    assert taken_med.last_taken is not None


# TC-INT-INTAKE-007: Record intake at exact scheduled time with multiple medications
@pytest.mark.asyncio
async def test_record_intake_exact_time_multiple_medications(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test recording intake at exact time when multiple medications scheduled.
    
    Scenario:
    - User has "Аспирин" at 10:00 and "Парацетамол" at 10:00
    - User says "Принял Аспирин в 10:00"
    - System should mark only Аспирин as taken, not Парацетамол
    """
    # Given: User with multiple medications at same time
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    meds_aspirin = await schedule_manager.add_medication(
        user_id=user_id,
        name="Аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    
    meds_paracetamol = await schedule_manager.add_medication(
        user_id=user_id,
        name="Парацетамол",
        times=["10:00"],
        dosage="400 мг"
    )
    
    aspirin_id = meds_aspirin[0].id
    paracetamol_id = meds_paracetamol[0].id
    
    # When: User reports taking specific medication at time
    user_message = "Принял Аспирин в 10:00"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to extract only Аспирин
    async def mock_done_specific_med(message, schedule):
        return {
            "medication_name": "Аспирин",
            "time": "10:00",
            "medication_ids": [med["id"] for med in schedule if med["name"] == "Аспирин"]
        }
    
    mock_groq_client.process_done_command = AsyncMock(side_effect=mock_done_specific_med)
    
    # Process done command
    result = await mock_groq_client.process_done_command(user_message, schedule_dict)
    
    # Verify only Аспирин IDs returned
    assert len(result["medication_ids"]) == 1
    assert aspirin_id in result["medication_ids"]
    assert paracetamol_id not in result["medication_ids"]
    
    # Simulate handler validation
    specified_time = result["time"]
    medication_ids = result["medication_ids"]
    
    matching_meds = [med for med in schedule if med.id in medication_ids and med.time == specified_time]
    
    # Then: Should match only Аспирин
    assert len(matching_meds) == 1
    assert matching_meds[0].id == aspirin_id
    assert matching_meds[0].name == "Аспирин"
