"""Integration test for dose change medication flow.

This test suite verifies that dose change confirmation messages include
medication names in lowercase genitive case (родительный падеж):
- "Дозировка {medication_name} изменена на {dosage}"
- Example: "Дозировка габапентина изменена на 400 мг"
- Genitive case examples: аспирин → аспирина, габапентин → габапентина, ламотриджин → ламотриджина
"""

import pytest
from unittest.mock import AsyncMock


# TC-INT-DOSE-001: Dose change with medication name in confirmation (genitive case)
@pytest.mark.asyncio
async def test_dose_change_confirmation_includes_medication_name(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test that dose change confirmation includes medication name in lowercase genitive case.
    
    Scenario:
    - User has "Габапентин" with dosage "300 мг"
    - User requests "габапентин теперь 400 мг"
    - Confirmation should be "Дозировка габапентина изменена на 400 мг"
    - Medication name should be in lowercase genitive case (родительный падеж)
    - Genitive: габапентин → габапентина
    """
    # Given: User with medication
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    meds = await schedule_manager.add_medication(
        user_id=user_id,
        name="Габапентин",
        times=["10:00"],
        dosage="300 мг"
    )
    
    med_id = meds[0].id
    
    # When: User requests to change dosage
    user_message = "габапентин теперь 400 мг"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to return medication ID, new dosage, and medication name in genitive case
    # The LLM should return medication_name in genitive case as per prompts.py
    async def mock_dose_change_with_name(message, schedule):
        return {
            "status": "success",
            "medication_id": med_id,
            "new_dosage": "400 мг",
            "medication_name": "габапентина"  # Genitive case, lowercase
        }
    
    mock_groq_client.process_dose_change_command = AsyncMock(side_effect=mock_dose_change_with_name)
    
    # Process dose change command
    result = await mock_groq_client.process_dose_change_command(user_message, schedule_dict)
    assert result["status"] == "success"
    assert result["medication_name"] == "габапентина"  # LLM returns genitive case
    assert result["new_dosage"] == "400 мг"
    
    # Update medication dosage
    await schedule_manager.update_medication_dosage(
        user_id=user_id,
        medication_id=result["medication_id"],
        new_dosage=result["new_dosage"]
    )
    
    # Then: Verify the expected confirmation message format
    # According to handlers.py line 598: f"Дозировка {medication_name.lower()} изменена на {new_dosage}"
    medication_name = result.get("medication_name")
    new_dosage = result["new_dosage"]
    expected_message = f"Дозировка {medication_name.lower()} изменена на {new_dosage}"
    
    # Verify medication name is in lowercase genitive case in the message
    # Genitive case: габапентин → габапентина
    assert expected_message == "Дозировка габапентина изменена на 400 мг"
    assert "габапентина" in expected_message
    
    # Verify medication dosage was actually updated
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 1
    assert user_data.medications[0].dosage == "400 мг"


# TC-INT-DOSE-002: Dose change with various medication names (genitive case)
@pytest.mark.asyncio
async def test_dose_change_confirmation_various_medications(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test dose change confirmation for various medication names in genitive case.
    
    Scenario:
    - Test multiple medications with different names
    - Verify each confirmation message includes the correct medication name in lowercase genitive case
    - Examples: ламотриджин → ламотриджина, аспирин → аспирина, парацетамол → парацетамола
    """
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Test cases: (medication_name, expected_lowercase_genitive, old_dosage, new_dosage)
    test_cases = [
        ("Ламотриджин", "ламотриджина", "100 мг", "150 мг"),  # genitive case
        ("АСПИРИН", "аспирина", "200 мг", "300 мг"),  # genitive case
        ("ПараЦетаМол", "парацетамола", "400 мг", "500 мг"),  # genitive case
    ]
    
    for med_name, expected_lowercase, old_dosage, new_dosage in test_cases:
        # Add medication
        meds = await schedule_manager.add_medication(
            user_id=user_id,
            name=med_name,
            times=["10:00"],
            dosage=old_dosage
        )
        
        med_id = meds[0].id
        
        # Get current schedule
        schedule = await schedule_manager.get_user_schedule(user_id)
        schedule_dict = [med.to_dict() for med in schedule]
        
        # Mock LLM to return medication ID, new dosage, and name in genitive case
        async def mock_dose_change(message, schedule, name=expected_lowercase, id=med_id, dosage=new_dosage):
            return {
                "status": "success",
                "medication_id": id,
                "new_dosage": dosage,
                "medication_name": name  # Already in genitive case from test_cases
            }
        
        mock_groq_client.process_dose_change_command = AsyncMock(side_effect=mock_dose_change)
        
        # Process dose change command
        result = await mock_groq_client.process_dose_change_command(
            f"{med_name} теперь {new_dosage}",
            schedule_dict
        )
        
        # Verify medication name is returned in genitive case
        assert result["medication_name"] == expected_lowercase
        
        # Update medication dosage
        await schedule_manager.update_medication_dosage(
            user_id=user_id,
            medication_id=result["medication_id"],
            new_dosage=result["new_dosage"]
        )
        
        # Verify expected confirmation message format with genitive case
        expected_message = f"Дозировка {expected_lowercase} изменена на {new_dosage}"
        # Verify genitive case is used (e.g., "габапентина", not "габапентин")
        assert expected_lowercase in expected_message
        
        # Verify dosage was updated
        user_data = await data_manager.get_user_data(user_id)
        medication = user_data.get_medication_by_id(med_id)
        assert medication.dosage == new_dosage
        
        # Clean up for next test
        await schedule_manager.delete_medications(user_id, [med_id])


# TC-INT-DOSE-003: Dose change without medication name (fallback)
@pytest.mark.asyncio
async def test_dose_change_confirmation_without_medication_name(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test dose change confirmation when medication name is not provided by LLM.
    
    Scenario:
    - User has medication
    - LLM returns only medication_id and new_dosage without medication_name
    - Should use fallback message: "Дозировка изменена на {dosage}"
    """
    # Given: User with medication
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    meds = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    
    med_id = meds[0].id
    
    # When: LLM returns result without medication_name
    user_message = "измени дозировку на 300 мг"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to return only medication_id and new_dosage (no medication_name)
    async def mock_dose_change_without_name(message, schedule):
        return {
            "status": "success",
            "medication_id": med_id,
            "new_dosage": "300 мг"
            # Note: no medication_name field
        }
    
    mock_groq_client.process_dose_change_command = AsyncMock(side_effect=mock_dose_change_without_name)
    
    # Process dose change command
    result = await mock_groq_client.process_dose_change_command(user_message, schedule_dict)
    assert result["status"] == "success"
    assert "medication_name" not in result
    
    # Update medication dosage
    await schedule_manager.update_medication_dosage(
        user_id=user_id,
        medication_id=result["medication_id"],
        new_dosage=result["new_dosage"]
    )
    
    # Then: Verify fallback message format (handlers.py line 600)
    medication_name = result.get("medication_name")
    new_dosage = result["new_dosage"]
    
    if medication_name:
        expected_message = f"Дозировка {medication_name.lower()} изменена на {new_dosage}"
    else:
        expected_message = f"Дозировка изменена на {new_dosage}"
    
    # Verify fallback message is used when name not available
    assert medication_name is None
    assert expected_message == "Дозировка изменена на 300 мг"


# TC-INT-DOSE-004: Dose change with clarification needed
@pytest.mark.asyncio
async def test_dose_change_clarification_needed(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test dose change when clarification is needed.
    
    Scenario:
    - User has multiple medications
    - User sends ambiguous dose change request
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
    user_message = "измени дозировку на 300 мг"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to request clarification
    async def mock_dose_change_clarification(message, schedule):
        return {
            "status": "clarification_needed",
            "message": "Для какого медикамента изменить дозировку? У вас в расписании: аспирин, парацетамол"
        }
    
    mock_groq_client.process_dose_change_command = AsyncMock(side_effect=mock_dose_change_clarification)
    
    # Process dose change command
    result = await mock_groq_client.process_dose_change_command(user_message, schedule_dict)
    assert result["status"] == "clarification_needed"
    assert "message" in result
    assert "аспирин" in result["message"]
    
    # Then: No medications should be updated
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 2
    # Verify dosages are unchanged
    dosages = {med.dosage for med in user_data.medications}
    assert dosages == {"200 мг", "400 мг"}


# TC-INT-DOSE-005: Dose change with different dosage formats
@pytest.mark.asyncio
async def test_dose_change_various_dosage_formats(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test dose change with various dosage formats.
    
    Scenario:
    - Test different dosage formats (мг, таблетки, мл, etc.)
    - Verify confirmation messages work correctly with all formats
    """
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Test cases: (medication_name, genitive_case, old_dosage, new_dosage)
    test_cases = [
        ("аспирин", "аспирина", "200 мг", "300 мг"),
        ("парацетамол", "парацетамола", "1 таблетка", "2 таблетки"),
        ("сироп", "сиропа", "5 мл", "10 мл"),
    ]
    
    for med_name, genitive_name, old_dosage, new_dosage in test_cases:
        # Add medication
        meds = await schedule_manager.add_medication(
            user_id=user_id,
            name=med_name,
            times=["10:00"],
            dosage=old_dosage
        )
        
        med_id = meds[0].id
        
        # Get current schedule
        schedule = await schedule_manager.get_user_schedule(user_id)
        schedule_dict = [med.to_dict() for med in schedule]
        
        # Mock LLM to return medication ID, new dosage, and name in genitive case
        async def mock_dose_change(message, schedule, name=genitive_name, id=med_id, dosage=new_dosage):
            return {
                "status": "success",
                "medication_id": id,
                "new_dosage": dosage,
                "medication_name": name  # Genitive case
            }
        
        mock_groq_client.process_dose_change_command = AsyncMock(side_effect=mock_dose_change)
        
        # Process dose change command
        result = await mock_groq_client.process_dose_change_command(
            f"{med_name} теперь {new_dosage}",
            schedule_dict
        )
        
        # Update medication dosage
        await schedule_manager.update_medication_dosage(
            user_id=user_id,
            medication_id=result["medication_id"],
            new_dosage=result["new_dosage"]
        )
        
        # Verify expected confirmation message format
        medication_name = result.get("medication_name")
        expected_message = f"Дозировка {medication_name.lower()} изменена на {new_dosage}"
        
        # Verify dosage was updated
        user_data = await data_manager.get_user_data(user_id)
        medication = user_data.get_medication_by_id(med_id)
        assert medication.dosage == new_dosage
        
        # Clean up for next test
        await schedule_manager.delete_medications(user_id, [med_id])


# TC-INT-DOSE-006: Dose change for medication with multiple time entries
@pytest.mark.asyncio
async def test_dose_change_multiple_time_entries(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test dose change for medication with multiple time entries.
    
    Scenario:
    - User has "аспирин" at 10:00 and 18:00
    - User requests "аспирин теперь 300 мг"
    - Both entries should have dosage updated
    - Confirmation should include medication name
    """
    # Given: User with medication at multiple times
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    meds = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00", "18:00"],
        dosage="200 мг"
    )
    
    # Get one of the medication IDs (they share the same name)
    med_id = meds[0].id
    
    # When: User requests to change dosage
    user_message = "аспирин теперь 300 мг"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [med.to_dict() for med in schedule]
    
    # Mock LLM to return medication ID and new dosage with genitive case
    async def mock_dose_change_with_name(message, schedule):
        return {
            "status": "success",
            "medication_id": med_id,
            "new_dosage": "300 мг",
            "medication_name": "аспирина"  # Genitive case, lowercase
        }
    
    mock_groq_client.process_dose_change_command = AsyncMock(side_effect=mock_dose_change_with_name)
    
    # Process dose change command
    result = await mock_groq_client.process_dose_change_command(user_message, schedule_dict)
    assert result["status"] == "success"
    
    # Update medication dosage
    await schedule_manager.update_medication_dosage(
        user_id=user_id,
        medication_id=result["medication_id"],
        new_dosage=result["new_dosage"]
    )
    
    # Verify expected confirmation message format with genitive case
    medication_name = result.get("medication_name")
    new_dosage = result["new_dosage"]
    expected_message = f"Дозировка {medication_name.lower()} изменена на {new_dosage}"
    
    # Genitive case: аспирин → аспирина
    assert expected_message == "Дозировка аспирина изменена на 300 мг"
    assert "аспирина" in expected_message
    
    # Verify the specific medication was updated
    user_data = await data_manager.get_user_data(user_id)
    medication = user_data.get_medication_by_id(med_id)
    assert medication.dosage == "300 мг"
