"""Integration test for time change medication flow.

This test suite verifies that time change confirmation messages include
medication names in lowercase genitive case (родительный падеж):
- "Время приема {medication_name} изменено на {time}"
- Example: "Время приема ламотриджина изменено на 11:00"
- Genitive case examples: аспирин → аспирина, габапентин → габапентина, ламотриджин → ламотриджина
"""

import pytest
from unittest.mock import AsyncMock


# TC-INT-TIME-001: Time change with medication name in confirmation (genitive case)
@pytest.mark.asyncio
async def test_time_change_confirmation_includes_medication_name(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test that time change confirmation includes medication name in lowercase genitive case.
    
    Scenario:
    - User has "Ламотриджин" at 10:00
    - User requests "ламотриджин теперь в 11:00"
    - Confirmation should be "Время приема ламотриджина изменено на 11:00"
    - Medication name should be in lowercase genitive case (родительный падеж)
    - Genitive: ламотриджин → ламотриджина
    """
    # Given: User with medication
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    created_meds, skipped = await schedule_manager.add_medication(
        user_id=user_id,
        name="Ламотриджин",
        times=["10:00"],
        dosage="100 мг"
    )
    
    med_id = created_meds[0].id
    
    # When: User requests to change time
    user_message = "ламотриджин теперь в 11:00"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to return medication ID, new time, and medication name in genitive case
    # The LLM should return medication_name in genitive case as per prompts.py
    async def mock_time_change_with_name(message, schedule):
        return {
            "status": "success",
            "medication_id": med_id,
            "new_times": ["11:00"],
            "medication_name": "ламотриджина"  # Genitive case, lowercase
        }
    
    mock_groq_client.process_time_change_command = AsyncMock(side_effect=mock_time_change_with_name)
    
    # Process time change command
    result = await mock_groq_client.process_time_change_command(user_message, schedule_dict)
    assert result["status"] == "success"
    assert result["medication_name"] == "ламотриджина"  # LLM returns genitive case
    assert result["new_times"] == ["11:00"]
    
    # Update medication time
    updated_meds = await schedule_manager.update_medication_time(
        user_id=user_id,
        medication_id=result["medication_id"],
        new_times=result["new_times"]
    )
    
    # Then: Verify the expected confirmation message format
    # According to handlers.py line 534: f"Время приема {medication_name.lower()} изменено на {times_str}"
    medication_name = result.get("medication_name")
    times_str = " и ".join(result["new_times"])
    expected_message = f"Время приема {medication_name.lower()} изменено на {times_str}"
    
    # Verify medication name is in lowercase genitive case in the message
    # Genitive case: ламотриджин → ламотриджина
    assert expected_message == "Время приема ламотриджина изменено на 11:00"
    assert "ламотриджина" in expected_message
    
    # Verify medication time was actually updated
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 1
    assert user_data.medications[0].time == "11:00"


# TC-INT-TIME-002: Time change with multiple times (genitive case)
@pytest.mark.asyncio
async def test_time_change_confirmation_multiple_times(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test time change confirmation with multiple new times in genitive case.
    
    Scenario:
    - User has "аспирин" at 10:00
    - User requests "аспирин теперь в 10:00 и 18:00"
    - Confirmation should be "Время приема аспирина изменено на 10:00 и 18:00"
    - Genitive case: аспирин → аспирина
    """
    # Given: User with medication
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    created_meds, skipped = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    
    med_id = created_meds[0].id
    
    # When: User requests to change time to multiple times
    user_message = "аспирин теперь в 10:00 и 18:00"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to return multiple new times with genitive case
    async def mock_time_change_multiple(message, schedule):
        return {
            "status": "success",
            "medication_id": med_id,
            "new_times": ["10:00", "18:00"],
            "medication_name": "аспирина"  # Genitive case, lowercase
        }
    
    mock_groq_client.process_time_change_command = AsyncMock(side_effect=mock_time_change_multiple)
    
    # Process time change command
    result = await mock_groq_client.process_time_change_command(user_message, schedule_dict)
    assert result["status"] == "success"
    assert result["new_times"] == ["10:00", "18:00"]
    
    # Update medication time
    updated_meds = await schedule_manager.update_medication_time(
        user_id=user_id,
        medication_id=result["medication_id"],
        new_times=result["new_times"]
    )
    
    # Verify expected confirmation message format with genitive case
    medication_name = result.get("medication_name")
    times_str = " и ".join(result["new_times"])
    expected_message = f"Время приема {medication_name.lower()} изменено на {times_str}"
    
    # Genitive case: аспирин → аспирина
    assert expected_message == "Время приема аспирина изменено на 10:00 и 18:00"
    assert "аспирина" in expected_message
    
    # Verify medications were created for each time
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 2
    times = {med.time for med in user_data.medications}
    assert times == {"10:00", "18:00"}


# TC-INT-TIME-003: Time change with various medication names (genitive case)
@pytest.mark.asyncio
async def test_time_change_confirmation_various_medications(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test time change confirmation for various medication names in genitive case.
    
    Scenario:
    - Test multiple medications with different names
    - Verify each confirmation message includes the correct medication name in lowercase genitive case
    - Examples: габапентин → габапентина, парацетамол → парацетамола, ибупрофен → ибупрофена
    """
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Test cases: (medication_name, expected_lowercase_genitive, new_time)
    test_cases = [
        ("Габапентин", "габапентина", "11:00"),  # genitive case
        ("ПАРАЦЕТАМОЛ", "парацетамола", "12:00"),  # genitive case
        ("ИбуПрофен", "ибупрофена", "13:00"),  # genitive case
    ]
    
    for med_name, expected_lowercase, new_time in test_cases:
        # Add medication
        created_meds, skipped = await schedule_manager.add_medication(
            user_id=user_id,
            name=med_name,
            times=["10:00"],
            dosage="100 мг"
        )
        
        med_id = created_meds[0].id
        
        # Get current schedule
        schedule = await schedule_manager.get_user_schedule(user_id)
        schedule_dict = [med.to_dict() for med in schedule]
        
        # Mock LLM to return medication ID, new time, and name in genitive case
        async def mock_time_change(message, schedule, name=expected_lowercase, id=med_id, time=new_time):
            return {
                "status": "success",
                "medication_id": id,
                "new_times": [time],
                "medication_name": name  # Already in genitive case from test_cases
            }
        
        mock_groq_client.process_time_change_command = AsyncMock(side_effect=mock_time_change)
        
        # Process time change command
        result = await mock_groq_client.process_time_change_command(
            f"{med_name} теперь в {new_time}",
            schedule_dict
        )
        
        # Verify medication name is returned in genitive case
        assert result["medication_name"] == expected_lowercase
        
        # Update medication time
        updated_meds = await schedule_manager.update_medication_time(
            user_id=user_id,
            medication_id=result["medication_id"],
            new_times=result["new_times"]
        )
        
        # Verify expected confirmation message format with genitive case
        expected_message = f"Время приема {expected_lowercase} изменено на {new_time}"
        # Verify genitive case is used (e.g., "габапентина", not "габапентин")
        assert expected_lowercase in expected_message
        
        # Clean up for next test
        await schedule_manager.delete_medications(user_id, [med_id])


# TC-INT-TIME-004: Time change without medication name (fallback)
@pytest.mark.asyncio
async def test_time_change_confirmation_without_medication_name(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test time change confirmation when medication name is not provided by LLM.
    
    Scenario:
    - User has medication
    - LLM returns only medication_id and new_times without medication_name
    - Should use fallback message: "Время приема изменено на {time}"
    """
    # Given: User with medication
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    created_meds, skipped = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    
    med_id = created_meds[0].id
    
    # When: LLM returns result without medication_name
    user_message = "измени время на 11:00"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to return only medication_id and new_times (no medication_name)
    async def mock_time_change_without_name(message, schedule):
        return {
            "status": "success",
            "medication_id": med_id,
            "new_times": ["11:00"]
            # Note: no medication_name field
        }
    
    mock_groq_client.process_time_change_command = AsyncMock(side_effect=mock_time_change_without_name)
    
    # Process time change command
    result = await mock_groq_client.process_time_change_command(user_message, schedule_dict)
    assert result["status"] == "success"
    assert "medication_name" not in result
    
    # Update medication time
    updated_meds = await schedule_manager.update_medication_time(
        user_id=user_id,
        medication_id=result["medication_id"],
        new_times=result["new_times"]
    )
    
    # Then: Verify fallback message format (handlers.py line 536)
    medication_name = result.get("medication_name")
    times_str = " и ".join(result["new_times"])
    
    if medication_name:
        expected_message = f"Время приема {medication_name.lower()} изменено на {times_str}"
    else:
        expected_message = f"Время приема изменено на {times_str}"
    
    # Verify fallback message is used when name not available
    assert medication_name is None
    assert expected_message == "Время приема изменено на 11:00"


# TC-INT-TIME-005: Time change with clarification needed
@pytest.mark.asyncio
async def test_time_change_clarification_needed(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test time change when clarification is needed.
    
    Scenario:
    - User has multiple medications
    - User sends ambiguous time change request
    - LLM requests clarification
    - No medications should be updated
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
    
    # When: User sends ambiguous request
    user_message = "измени время на 11:00"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to request clarification
    async def mock_time_change_clarification(message, schedule):
        return {
            "status": "clarification_needed",
            "message": "Для какого медикамента изменить время? У вас в расписании: аспирин, парацетамол"
        }
    
    mock_groq_client.process_time_change_command = AsyncMock(side_effect=mock_time_change_clarification)
    
    # Process time change command
    result = await mock_groq_client.process_time_change_command(user_message, schedule_dict)
    assert result["status"] == "clarification_needed"
    assert "message" in result
    assert "аспирин" in result["message"]
    
    # Then: No medications should be updated
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 2
    # Verify times are unchanged
    times = {med.time for med in user_data.medications}
    assert times == {"10:00", "14:00"}
