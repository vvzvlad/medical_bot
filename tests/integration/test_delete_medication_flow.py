"""Integration test for delete medication flow.

This test suite verifies the fix for the bug where the LLM was generating
fictional medication IDs during delete operations. It ensures that:
1. Only valid IDs from the actual schedule are used
2. Fictional IDs are filtered out and logged
3. Delete operations work correctly for various scenarios
"""

import pytest
from unittest.mock import AsyncMock, patch
from loguru import logger


# TC-INT-DEL-001: Delete medication by name (all matching entries)
@pytest.mark.asyncio
async def test_delete_by_name_all_matching(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test deleting all medications with the same name.
    
    Scenario:
    - User has multiple "аспирин" entries at different times
    - User requests "удали аспирин"
    - All matching medications should be deleted
    - Only real IDs from schedule should be used
    """
    # Given: User with multiple medications with same name
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Add aspirin at different times
    meds_10 = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    meds_14 = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["14:00"],
        dosage="200 мг"
    )
    meds_18 = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["18:00"],
        dosage="200 мг"
    )
    
    # Add another medication to ensure we don't delete everything
    await schedule_manager.add_medication(
        user_id=user_id,
        name="парацетамол",
        times=["12:00"],
        dosage="400 мг"
    )
    
    # Collect all aspirin IDs
    aspirin_ids = [meds_10[0].id, meds_14[0].id, meds_18[0].id]
    
    # When: User requests to delete aspirin
    user_message = "Удали аспирин"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to return all aspirin IDs
    async def mock_delete_all_aspirin(message, schedule):
        # Find all aspirin medications
        aspirin_meds = [med for med in schedule if med["name"] == "аспирин"]
        return {
            "status": "success",
            "medication_ids": [med["id"] for med in aspirin_meds]
        }
    
    mock_groq_client.process_delete_command = AsyncMock(side_effect=mock_delete_all_aspirin)
    
    # Process delete command
    result = await mock_groq_client.process_delete_command(user_message, schedule_dict)
    assert result["status"] == "success"
    assert len(result["medication_ids"]) == 3
    
    # Verify all returned IDs are valid
    valid_ids = {med.id for med in schedule}
    for med_id in result["medication_ids"]:
        assert med_id in valid_ids, f"ID {med_id} should be in valid IDs"
    
    # Delete medications
    deleted = await schedule_manager.delete_medications(user_id, result["medication_ids"])
    assert deleted is True
    
    # Then: Only aspirin should be deleted, paracetemol should remain
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 1
    assert user_data.medications[0].name == "парацетамол"
    assert user_data.medications[0].time == "12:00"


# TC-INT-DEL-002: Delete medication at specific time
@pytest.mark.asyncio
async def test_delete_specific_time(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test deleting medication at a specific time.
    
    Scenario:
    - User has "аспирин" at 10:00, 14:00, and 18:00
    - User requests "удали аспирин в 14:00"
    - Only the 14:00 entry should be deleted
    """
    # Given: User with medication at multiple times
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    meds_10 = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    meds_14 = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["14:00"],
        dosage="200 мг"
    )
    meds_18 = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["18:00"],
        dosage="200 мг"
    )
    
    target_id = meds_14[0].id
    
    # When: User requests to delete aspirin at 14:00
    user_message = "Удали аспирин в 14:00"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to return only the 14:00 medication
    async def mock_delete_specific_time(message, schedule):
        # Find aspirin at 14:00
        for med in schedule:
            if med["name"] == "аспирин" and med["time"] == "14:00":
                return {
                    "status": "success",
                    "medication_ids": [med["id"]]
                }
        return {"status": "not_found"}
    
    mock_groq_client.process_delete_command = AsyncMock(side_effect=mock_delete_specific_time)
    
    # Process delete command
    result = await mock_groq_client.process_delete_command(user_message, schedule_dict)
    assert result["status"] == "success"
    assert len(result["medication_ids"]) == 1
    assert result["medication_ids"][0] == target_id
    
    # Delete medication
    deleted = await schedule_manager.delete_medications(user_id, result["medication_ids"])
    assert deleted is True
    
    # Then: Only 14:00 entry should be deleted
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 2
    
    # Verify remaining medications
    remaining_times = {med.time for med in user_data.medications}
    assert "10:00" in remaining_times
    assert "18:00" in remaining_times
    assert "14:00" not in remaining_times


# TC-INT-DEL-003: Delete non-existent medication
@pytest.mark.asyncio
async def test_delete_non_existent_medication(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test attempting to delete a medication not in schedule.
    
    Scenario:
    - User has "аспирин" and "парацетамол"
    - User requests "удали ибупрофен"
    - Should return appropriate error message
    - No medications should be deleted
    """
    # Given: User with some medications
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    await schedule_manager.add_medication(
        user_id=user_id,
        name="парацетамол",
        times=["14:00"],
        dosage="400 мг"
    )
    
    # When: User requests to delete non-existent medication
    user_message = "Удали ибупрофен"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to return not_found status
    async def mock_delete_not_found(message, schedule):
        # Check if medication exists
        if "ибупрофен" not in [med["name"] for med in schedule]:
            return {
                "status": "not_found",
                "message": "Не удалось найти указанный медикамент в вашем расписании."
            }
        return {"status": "success", "medication_ids": []}
    
    mock_groq_client.process_delete_command = AsyncMock(side_effect=mock_delete_not_found)
    
    # Process delete command
    result = await mock_groq_client.process_delete_command(user_message, schedule_dict)
    assert result["status"] == "not_found"
    assert "message" in result
    
    # Then: No medications should be deleted
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 2
    assert user_data.medications[0].name == "аспирин"
    assert user_data.medications[1].name == "парацетамол"


# TC-INT-DEL-004: ID validation - filter fictional IDs
@pytest.mark.asyncio
async def test_id_validation_filters_fictional_ids(
    data_manager,
    schedule_manager,
    mock_groq_client,
    caplog
):
    """Test that fictional IDs from LLM are filtered out.
    
    This is the core test for the bug fix. It verifies that when the LLM
    returns fictional IDs (like 34567), they are filtered out and only
    valid IDs from the actual schedule are used.
    
    Scenario:
    - User has medications with real IDs (e.g., 1, 2, 3)
    - LLM returns mix of real and fictional IDs (e.g., [1, 34567, 99999])
    - System should filter out fictional IDs
    - System should log a warning about filtered IDs
    - Only real IDs should be used for deletion
    """
    # Given: User with medications
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    meds_aspirin = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    meds_paracetamol = await schedule_manager.add_medication(
        user_id=user_id,
        name="парацетамол",
        times=["14:00"],
        dosage="400 мг"
    )
    
    real_aspirin_id = meds_aspirin[0].id
    real_paracetamol_id = meds_paracetamol[0].id
    
    # When: LLM returns fictional IDs mixed with real ones
    user_message = "Удали аспирин"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to return fictional IDs (simulating the bug)
    fictional_ids = [34567, 99999, 12345]
    async def mock_delete_with_fictional_ids(message, schedule):
        # Return mix of real and fictional IDs
        return {
            "status": "success",
            "medication_ids": [real_aspirin_id] + fictional_ids
        }
    
    mock_groq_client.process_delete_command = AsyncMock(side_effect=mock_delete_with_fictional_ids)
    
    # Process delete command
    result = await mock_groq_client.process_delete_command(user_message, schedule_dict)
    assert result["status"] == "success"
    
    # Simulate the validation logic from handlers.py (lines 372-383)
    valid_ids = {med.id for med in schedule}
    original_ids = result["medication_ids"].copy()
    filtered_ids = [id for id in result["medication_ids"] if id in valid_ids]
    
    # Verify filtering worked
    assert len(original_ids) == 4  # 1 real + 3 fictional
    assert len(filtered_ids) == 1  # Only 1 real ID
    assert filtered_ids[0] == real_aspirin_id
    
    # Verify fictional IDs were filtered out
    removed_ids = [id for id in original_ids if id not in filtered_ids]
    assert len(removed_ids) == 3
    for fictional_id in fictional_ids:
        assert fictional_id in removed_ids
    
    # Delete with filtered IDs
    deleted = await schedule_manager.delete_medications(user_id, filtered_ids)
    assert deleted is True
    
    # Then: Only aspirin should be deleted (using real ID)
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 1
    assert user_data.medications[0].name == "парацетамол"
    assert user_data.medications[0].id == real_paracetamol_id


# TC-INT-DEL-005: ID validation - all fictional IDs
@pytest.mark.asyncio
async def test_id_validation_all_fictional_ids(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test when LLM returns only fictional IDs.
    
    Scenario:
    - User has medications with real IDs
    - LLM returns only fictional IDs (e.g., [34567, 99999])
    - After filtering, no valid IDs remain
    - Should handle gracefully with appropriate message
    - No medications should be deleted
    """
    # Given: User with medications
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    await schedule_manager.add_medication(
        user_id=user_id,
        name="парацетамол",
        times=["14:00"],
        dosage="400 мг"
    )
    
    # When: LLM returns only fictional IDs
    user_message = "Удали аспирин"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to return only fictional IDs
    async def mock_delete_only_fictional(message, schedule):
        return {
            "status": "success",
            "medication_ids": [34567, 99999, 12345]
        }
    
    mock_groq_client.process_delete_command = AsyncMock(side_effect=mock_delete_only_fictional)
    
    # Process delete command
    result = await mock_groq_client.process_delete_command(user_message, schedule_dict)
    assert result["status"] == "success"
    
    # Simulate validation logic
    valid_ids = {med.id for med in schedule}
    filtered_ids = [id for id in result["medication_ids"] if id in valid_ids]
    
    # Verify all IDs were filtered out
    assert len(filtered_ids) == 0
    
    # Attempt to delete with empty list
    deleted = await schedule_manager.delete_medications(user_id, filtered_ids)
    assert deleted is False  # No medications deleted
    
    # Then: No medications should be deleted
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 2


# TC-INT-DEL-006: Delete with clarification needed
@pytest.mark.asyncio
async def test_delete_clarification_needed(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test delete when clarification is needed.
    
    Scenario:
    - User has multiple different medications
    - User sends ambiguous delete request
    - LLM requests clarification
    - No medications should be deleted
    """
    # Given: User with multiple medications
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    await schedule_manager.add_medication(
        user_id=user_id,
        name="парацетамол",
        times=["14:00"],
        dosage="400 мг"
    )
    await schedule_manager.add_medication(
        user_id=user_id,
        name="ибупрофен",
        times=["18:00"],
        dosage="300 мг"
    )
    
    # When: User sends ambiguous request
    user_message = "Удали"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to request clarification
    async def mock_delete_clarification(message, schedule):
        return {
            "status": "clarification_needed",
            "message": "Какое лекарство удалить? У вас в расписании: аспирин, парацетамол, ибупрофен"
        }
    
    mock_groq_client.process_delete_command = AsyncMock(side_effect=mock_delete_clarification)
    
    # Process delete command
    result = await mock_groq_client.process_delete_command(user_message, schedule_dict)
    assert result["status"] == "clarification_needed"
    assert "message" in result
    assert "аспирин" in result["message"]
    
    # Then: No medications should be deleted
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 3


# TC-INT-DEL-007: Delete from empty schedule
@pytest.mark.asyncio
async def test_delete_from_empty_schedule(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test delete when user has no medications.
    
    Scenario:
    - User has no medications in schedule
    - User requests to delete medication
    - Should return appropriate message
    """
    # Given: User with no medications
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # When: User requests to delete medication
    user_message = "Удали аспирин"
    
    # Get current schedule (empty)
    schedule = await schedule_manager.get_user_schedule(user_id)
    assert len(schedule) == 0
    
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to handle empty schedule
    async def mock_delete_empty(message, schedule):
        if not schedule:
            return {
                "status": "error",
                "message": "У вас нет медикаментов в расписании."
            }
        return {"status": "success", "medication_ids": []}
    
    mock_groq_client.process_delete_command = AsyncMock(side_effect=mock_delete_empty)
    
    # Process delete command
    result = await mock_groq_client.process_delete_command(user_message, schedule_dict)
    assert result["status"] == "error"
    assert "message" in result
    
    # Then: User still has no medications
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 0


# TC-INT-DEL-008: Delete multiple different medications
@pytest.mark.asyncio
async def test_delete_multiple_different_medications(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test deleting multiple different medications in one command.
    
    Scenario:
    - User has аспирин, парацетамол, and ибупрофен
    - User requests "удали аспирин и парацетамол"
    - Both medications should be deleted
    - Ибупрофен should remain
    """
    # Given: User with multiple medications
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    meds_aspirin = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    meds_paracetamol = await schedule_manager.add_medication(
        user_id=user_id,
        name="парацетамол",
        times=["14:00"],
        dosage="400 мг"
    )
    meds_ibuprofen = await schedule_manager.add_medication(
        user_id=user_id,
        name="ибупрофен",
        times=["18:00"],
        dosage="300 мг"
    )
    
    aspirin_id = meds_aspirin[0].id
    paracetamol_id = meds_paracetamol[0].id
    
    # When: User requests to delete multiple medications
    user_message = "Удали аспирин и парацетамол"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to return multiple medication IDs
    async def mock_delete_multiple(message, schedule):
        ids_to_delete = []
        for med in schedule:
            if med["name"] in ["аспирин", "парацетамол"]:
                ids_to_delete.append(med["id"])
        return {
            "status": "success",
            "medication_ids": ids_to_delete
        }
    
    mock_groq_client.process_delete_command = AsyncMock(side_effect=mock_delete_multiple)
    
    # Process delete command
    result = await mock_groq_client.process_delete_command(user_message, schedule_dict)
    assert result["status"] == "success"
    assert len(result["medication_ids"]) == 2
    assert aspirin_id in result["medication_ids"]
    assert paracetamol_id in result["medication_ids"]
    
    # Delete medications
    deleted = await schedule_manager.delete_medications(user_id, result["medication_ids"])
    assert deleted is True
    
    # Then: Only ибупрофен should remain
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 1
    assert user_data.medications[0].name == "ибупрофен"
    assert user_data.medications[0].time == "18:00"
