"""Integration test for duplicate medication prevention.

This test verifies the fix for the reported issue where users could add
the same medication at the same time multiple times, resulting in duplicates.

Test Scenario (as reported):
1. User adds "героин в 13:00" - should be added successfully
2. User adds "героин в 13:00" again - should be detected as duplicate and skipped
3. User lists medications - should show only ONE entry for "героин в 13:00"
"""

import pytest
from unittest.mock import AsyncMock


# TC-INT-DUP-001: Exact Duplicate Detection
@pytest.mark.asyncio
async def test_exact_duplicate_prevention(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test that exact duplicate medications are prevented.
    
    This is the exact scenario reported by the user:
    - Add "героин в 13:00" first time -> should succeed
    - Add "героин в 13:00" second time -> should be skipped as duplicate
    - List medications -> should show only ONE entry
    """
    # Given: User with account
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Mock LLM to return героин at 13:00
    async def mock_process_add_heroin(message):
        return [{
            "medication_name": "героин",
            "times": ["13:00"],
            "dosage": None
        }]
    
    mock_groq_client.process_add_command = AsyncMock(side_effect=mock_process_add_heroin)
    
    # When: User adds "героин в 13:00" first time
    user_message_1 = "героин в 13:00"
    result_1 = await mock_groq_client.process_add_command(user_message_1)
    med_data_1 = result_1[0]
    
    created_1, skipped_1 = await schedule_manager.add_medication(
        user_id=user_id,
        name=med_data_1["medication_name"],
        times=med_data_1["times"],
        dosage=med_data_1.get("dosage")
    )
    
    # Then: First add should succeed
    assert len(created_1) == 1
    assert len(skipped_1) == 0
    assert created_1[0].name == "героин"
    assert created_1[0].time == "13:00"
    
    # When: User adds "героин в 13:00" second time (duplicate)
    user_message_2 = "героин в 13:00"
    result_2 = await mock_groq_client.process_add_command(user_message_2)
    med_data_2 = result_2[0]
    
    created_2, skipped_2 = await schedule_manager.add_medication(
        user_id=user_id,
        name=med_data_2["medication_name"],
        times=med_data_2["times"],
        dosage=med_data_2.get("dosage")
    )
    
    # Then: Second add should be skipped as duplicate
    assert len(created_2) == 0, "No new medications should be created for duplicate"
    assert len(skipped_2) == 1, "Duplicate time should be skipped"
    assert skipped_2[0] == "13:00", "13:00 should be in skipped times"
    
    # When: User lists medications
    schedule = await schedule_manager.get_user_schedule(user_id)
    
    # Then: Should show only ONE entry for "героин в 13:00"
    assert len(schedule) == 1, "Should have exactly one medication entry"
    assert schedule[0].name == "героин"
    assert schedule[0].time == "13:00"


# TC-INT-DUP-002: Case-Insensitive Duplicate Detection
@pytest.mark.asyncio
async def test_case_insensitive_duplicate_prevention(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test that duplicates are detected regardless of case.
    
    Scenario:
    - Add "героин в 13:00" (lowercase)
    - Add "Героин в 13:00" (capitalized) -> should be detected as duplicate
    """
    # Given: User with account
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # When: Add "героин" (lowercase) first
    created_1, skipped_1 = await schedule_manager.add_medication(
        user_id=user_id,
        name="героин",
        times=["13:00"],
        dosage=None
    )
    
    # Then: First add should succeed
    assert len(created_1) == 1
    assert len(skipped_1) == 0
    
    # When: Add "Героин" (capitalized) at same time
    created_2, skipped_2 = await schedule_manager.add_medication(
        user_id=user_id,
        name="Героин",
        times=["13:00"],
        dosage=None
    )
    
    # Then: Should be detected as duplicate (case-insensitive)
    assert len(created_2) == 0, "Capitalized version should be detected as duplicate"
    assert len(skipped_2) == 1
    assert skipped_2[0] == "13:00"
    
    # Verify only one entry exists
    schedule = await schedule_manager.get_user_schedule(user_id)
    assert len(schedule) == 1


# TC-INT-DUP-003: Partial Duplicate Detection (Multiple Times)
@pytest.mark.asyncio
async def test_partial_duplicate_with_multiple_times(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test duplicate detection when adding multiple times with some duplicates.
    
    Scenario:
    - Add "героин в 13:00" first
    - Add "героин в 10:00 и 13:00" -> 10:00 should be added, 13:00 skipped
    """
    # Given: User with account and existing medication at 13:00
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Add first medication at 13:00
    created_1, skipped_1 = await schedule_manager.add_medication(
        user_id=user_id,
        name="героин",
        times=["13:00"],
        dosage=None
    )
    assert len(created_1) == 1
    
    # When: Add same medication at 10:00 and 13:00 (13:00 is duplicate)
    created_2, skipped_2 = await schedule_manager.add_medication(
        user_id=user_id,
        name="героин",
        times=["10:00", "13:00"],
        dosage=None
    )
    
    # Then: Only 10:00 should be added, 13:00 should be skipped
    assert len(created_2) == 1, "Only non-duplicate time should be added"
    assert created_2[0].time == "10:00"
    assert len(skipped_2) == 1, "Duplicate time should be skipped"
    assert skipped_2[0] == "13:00"
    
    # Verify schedule has both times
    schedule = await schedule_manager.get_user_schedule(user_id)
    assert len(schedule) == 2
    times = [med.time for med in schedule]
    assert "10:00" in times
    assert "13:00" in times


# TC-INT-DUP-004: Multiple Medications with Some Duplicates
@pytest.mark.asyncio
async def test_multiple_medications_with_duplicates(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test duplicate detection with multiple different medications.
    
    Scenario:
    - Add "аспирин в 10:00" and "героин в 13:00"
    - Try to add "аспирин в 10:00" again -> should be skipped
    - Try to add "героин в 14:00" -> should be added (different time)
    """
    # Given: User with account
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Add first medications
    await schedule_manager.add_medication(user_id, "аспирин", ["10:00"], "200 мг")
    await schedule_manager.add_medication(user_id, "героин", ["13:00"], None)
    
    # When: Try to add duplicate аспирин
    created_1, skipped_1 = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    
    # Then: Should be skipped
    assert len(created_1) == 0
    assert len(skipped_1) == 1
    assert skipped_1[0] == "10:00"
    
    # When: Add героин at different time (14:00)
    created_2, skipped_2 = await schedule_manager.add_medication(
        user_id=user_id,
        name="героин",
        times=["14:00"],
        dosage=None
    )
    
    # Then: Should be added (different time)
    assert len(created_2) == 1
    assert len(skipped_2) == 0
    assert created_2[0].time == "14:00"
    
    # Verify final schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    assert len(schedule) == 3  # аспирин 10:00, героин 13:00, героин 14:00


# TC-INT-DUP-005: Duplicate Detection with Different Dosages
@pytest.mark.asyncio
async def test_duplicate_detection_ignores_dosage(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test that duplicate detection is based on name and time, not dosage.
    
    Scenario:
    - Add "аспирин 200 мг в 10:00"
    - Try to add "аспирин 300 мг в 10:00" -> should be skipped (same name and time)
    """
    # Given: User with account
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Add medication with 200 мг dosage
    created_1, skipped_1 = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    assert len(created_1) == 1
    
    # When: Try to add same medication at same time with different dosage
    created_2, skipped_2 = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="300 мг"
    )
    
    # Then: Should be skipped (duplicate based on name and time)
    assert len(created_2) == 0
    assert len(skipped_2) == 1
    assert skipped_2[0] == "10:00"
    
    # Verify original dosage is preserved
    schedule = await schedule_manager.get_user_schedule(user_id)
    assert len(schedule) == 1
    assert schedule[0].dosage == "200 мг"


# TC-INT-DUP-006: Empty Schedule After All Duplicates Skipped
@pytest.mark.asyncio
async def test_all_times_skipped_as_duplicates(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test behavior when all times in a request are duplicates.
    
    Scenario:
    - Add "героин в 10:00 и 13:00"
    - Try to add "героин в 10:00 и 13:00" again -> all should be skipped
    """
    # Given: User with medications at 10:00 and 13:00
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    created_1, skipped_1 = await schedule_manager.add_medication(
        user_id=user_id,
        name="героин",
        times=["10:00", "13:00"],
        dosage=None
    )
    assert len(created_1) == 2
    assert len(skipped_1) == 0
    
    # When: Try to add same medications again
    created_2, skipped_2 = await schedule_manager.add_medication(
        user_id=user_id,
        name="героин",
        times=["10:00", "13:00"],
        dosage=None
    )
    
    # Then: All times should be skipped
    assert len(created_2) == 0, "No medications should be created"
    assert len(skipped_2) == 2, "All times should be skipped"
    assert set(skipped_2) == {"10:00", "13:00"}
    
    # Verify schedule still has only 2 entries
    schedule = await schedule_manager.get_user_schedule(user_id)
    assert len(schedule) == 2


# TC-INT-DUP-007: Formatted Display Shows Correct Count
@pytest.mark.asyncio
async def test_formatted_display_after_duplicate_prevention(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test that formatted schedule display shows correct count after duplicates.
    
    This verifies the complete user experience:
    - Add medication twice
    - List medications
    - Display should show only one entry
    """
    # Given: User with account
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Add medication first time
    await schedule_manager.add_medication(user_id, "героин", ["13:00"], None)
    
    # Try to add duplicate
    created, skipped = await schedule_manager.add_medication(
        user_id=user_id,
        name="героин",
        times=["13:00"],
        dosage=None
    )
    assert len(created) == 0
    assert len(skipped) == 1
    
    # When: Get formatted schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    formatted = schedule_manager.format_schedule_for_display(schedule)
    
    # Then: Should show only one entry
    assert "Вы принимаете:" in formatted
    assert "героин" in formatted
    assert "13:00" in formatted
    # Count occurrences of "героин" in the formatted output
    # Should appear only once in the medication list
    lines = formatted.split("\n")
    medication_lines = [line for line in lines if "героин" in line]
    assert len(medication_lines) == 1, "героин should appear only once in the list"


# TC-INT-DUP-008: Integration with Real User Flow
@pytest.mark.asyncio
async def test_complete_duplicate_prevention_flow(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test complete user flow with duplicate prevention.
    
    This simulates the exact reported scenario end-to-end:
    1. User sends "героин в 13:00"
    2. Bot adds medication
    3. User sends "героин в 13:00" again
    4. Bot detects duplicate and skips
    5. User asks "что я принимаю?"
    6. Bot shows only one entry
    """
    # Given: User with account
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Mock LLM responses
    async def mock_process_add_heroin(message):
        return [{
            "medication_name": "героин",
            "times": ["13:00"],
            "dosage": None
        }]
    
    mock_groq_client.process_add_command = AsyncMock(side_effect=mock_process_add_heroin)
    
    # Step 1: User sends "добавь героин в 13:00" first time
    message_1 = "добавь героин в 13:00"
    command_type_1 = await mock_groq_client.detect_command_type(message_1)
    assert command_type_1 == "add"
    
    result_1 = await mock_groq_client.process_add_command(message_1)
    med_data_1 = result_1[0]
    
    created_1, skipped_1 = await schedule_manager.add_medication(
        user_id=user_id,
        name=med_data_1["medication_name"],
        times=med_data_1["times"],
        dosage=med_data_1.get("dosage")
    )
    
    # Verify first add succeeded
    assert len(created_1) == 1
    assert len(skipped_1) == 0
    
    # Step 2: User sends "добавь героин в 13:00" second time (duplicate)
    message_2 = "добавь героин в 13:00"
    command_type_2 = await mock_groq_client.detect_command_type(message_2)
    assert command_type_2 == "add"
    
    result_2 = await mock_groq_client.process_add_command(message_2)
    med_data_2 = result_2[0]
    
    created_2, skipped_2 = await schedule_manager.add_medication(
        user_id=user_id,
        name=med_data_2["medication_name"],
        times=med_data_2["times"],
        dosage=med_data_2.get("dosage")
    )
    
    # Verify duplicate was detected and skipped
    assert len(created_2) == 0, "Duplicate should not create new medication"
    assert len(skipped_2) == 1, "Duplicate time should be skipped"
    assert skipped_2[0] == "13:00"
    
    # Step 3: User asks "что я принимаю?"
    message_3 = "что я принимаю?"
    command_type_3 = await mock_groq_client.detect_command_type(message_3)
    assert command_type_3 == "list"
    
    schedule = await schedule_manager.get_user_schedule(user_id)
    formatted = schedule_manager.format_schedule_for_display(schedule)
    
    # Verify only one entry is shown
    assert len(schedule) == 1, "Should have exactly one medication"
    assert schedule[0].name == "героин"
    assert schedule[0].time == "13:00"
    assert "героин" in formatted
    assert "13:00" in formatted
    
    # Verify the formatted output shows only one entry
    lines = formatted.split("\n")
    medication_lines = [line for line in lines if ")" in line and "—" in line]
    assert len(medication_lines) == 1, "Should show exactly one medication entry"
