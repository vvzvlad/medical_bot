"""Integration test for add medication flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# TC-INT-001: Complete Add Medication Flow
@pytest.mark.asyncio
async def test_complete_add_medication_flow(
    mock_message,
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test complete flow of adding medication."""
    # Given: User sends add medication message
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    mock_message.from_user.id = user_id
    mock_message.text = "Добавь аспирин 200 мг в 10:00"
    
    # When: Processing the message (simulating handler logic)
    # Step 1: Detect command type
    command_type = await mock_groq_client.detect_command_type(mock_message.text)
    assert command_type == "add"
    
    # Step 2: Process add command
    result = await mock_groq_client.process_add_command(mock_message.text)
    assert isinstance(result, list)
    assert len(result) > 0
    
    # Step 3: Add medication to schedule
    medication_data = result[0]
    medications = await schedule_manager.add_medication(
        user_id=user_id,
        name=medication_data["medication_name"],
        times=medication_data["times"],
        dosage=medication_data.get("dosage")
    )
    
    # Then: Medication should be added to user file
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 1
    assert user_data.medications[0].name == "аспирин"
    assert user_data.medications[0].dosage == "200 мг"
    assert user_data.medications[0].time == "10:00"


# Additional test: Add multiple medications
@pytest.mark.asyncio
async def test_add_multiple_medications_flow(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test adding multiple medications in one command."""
    # Given: User with account
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Mock LLM to return multiple medications
    async def mock_process_add_multiple(message):
        return [
            {"medication_name": "аспирин", "times": ["10:00"], "dosage": "200 мг"},
            {"medication_name": "парацетамол", "times": ["18:00"], "dosage": "400 мг"}
        ]
    
    mock_groq_client.process_add_command = AsyncMock(side_effect=mock_process_add_multiple)
    
    # When: Processing add command with multiple medications
    user_message = "Добавь аспирин в 10:00 и парацетамол в 18:00"
    result = await mock_groq_client.process_add_command(user_message)
    
    # Add all medications
    for med_data in result:
        await schedule_manager.add_medication(
            user_id=user_id,
            name=med_data["medication_name"],
            times=med_data["times"],
            dosage=med_data.get("dosage")
        )
    
    # Then: Both medications should be added
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 2
    assert user_data.medications[0].name == "аспирин"
    assert user_data.medications[1].name == "парацетамол"


# Additional test: Add medication with multiple times
@pytest.mark.asyncio
async def test_add_medication_multiple_times_flow(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test adding medication with multiple times."""
    # Given: User with account
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # Mock LLM to return medication with multiple times
    async def mock_process_add_multi_time(message):
        return [{
            "medication_name": "парацетамол",
            "times": ["12:00", "18:00"],
            "dosage": None
        }]
    
    mock_groq_client.process_add_command = AsyncMock(side_effect=mock_process_add_multi_time)
    
    # When: Processing add command
    user_message = "Принимаю парацетамол в 12:00 и 18:00"
    result = await mock_groq_client.process_add_command(user_message)
    
    # Add medication
    med_data = result[0]
    await schedule_manager.add_medication(
        user_id=user_id,
        name=med_data["medication_name"],
        times=med_data["times"],
        dosage=med_data.get("dosage")
    )
    
    # Then: Two separate medication entries should be created
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 2
    assert user_data.medications[0].name == "парацетамол"
    assert user_data.medications[0].time == "12:00"
    assert user_data.medications[1].name == "парацетамол"
    assert user_data.medications[1].time == "18:00"


# Additional test: Delete medication flow
@pytest.mark.asyncio
async def test_delete_medication_flow(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test complete flow of deleting medication."""
    # Given: User with medication
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    created_meds, skipped = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    medication_id = created_meds[0].id
    
    # When: Processing delete command
    user_message = "Удали аспирин"
    
    # Get current schedule for LLM
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [
        {"id": med.id, "name": med.name, "time": med.time}
        for med in schedule
    ]
    
    # Detect command and process
    command_type = await mock_groq_client.detect_command_type(user_message)
    assert command_type == "delete"
    
    result = await mock_groq_client.process_delete_command(user_message, schedule_dict)
    assert result["status"] == "success"
    
    # Delete medication
    await schedule_manager.delete_medications(user_id, result["medication_ids"])
    
    # Then: Medication should be deleted
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 0


# Additional test: Time change flow
@pytest.mark.asyncio
async def test_time_change_flow(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test complete flow of changing medication time."""
    # Given: User with medication
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    created_meds, skipped = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    medication_id = created_meds[0].id
    
    # When: Processing time change command
    user_message = "Аспирин теперь в 11:00"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [
        {"id": med.id, "name": med.name, "time": med.time}
        for med in schedule
    ]
    
    # Detect and process command
    command_type = await mock_groq_client.detect_command_type(user_message)
    assert command_type == "time_change"
    
    result = await mock_groq_client.process_time_change_command(user_message, schedule_dict)
    assert result["status"] == "success"
    
    # Update time
    await schedule_manager.update_medication_time(
        user_id,
        result["medication_id"],
        result["new_times"]
    )
    
    # Then: Time should be updated
    user_data = await data_manager.get_user_data(user_id)
    assert user_data.medications[0].time == "11:00"


# Additional test: Dose change flow
@pytest.mark.asyncio
async def test_dose_change_flow(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test complete flow of changing medication dosage."""
    # Given: User with medication
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    created_meds, skipped = await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    medication_id = created_meds[0].id
    
    # When: Processing dose change command
    user_message = "Аспирин теперь 300 мг"
    
    # Get current schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    schedule_dict = [
        {"id": med.id, "name": med.name, "dosage": med.dosage, "time": med.time}
        for med in schedule
    ]
    
    # Detect and process command
    command_type = await mock_groq_client.detect_command_type(user_message)
    assert command_type == "dose_change"
    
    result = await mock_groq_client.process_dose_change_command(user_message, schedule_dict)
    assert result["status"] == "success"
    
    # Update dosage
    await schedule_manager.update_medication_dosage(
        user_id,
        result["medication_id"],
        result["new_dosage"]
    )
    
    # Then: Dosage should be updated
    user_data = await data_manager.get_user_data(user_id)
    assert user_data.medications[0].dosage == "300 мг"


# Additional test: List medications flow
@pytest.mark.asyncio
async def test_list_medications_flow(
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test complete flow of listing medications."""
    # Given: User with medications
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    await schedule_manager.add_medication(user_id, "аспирин", ["10:00"], "200 мг")
    await schedule_manager.add_medication(user_id, "парацетамол", ["18:00"], "400 мг")
    
    # When: Processing list command
    user_message = "Что я принимаю?"
    command_type = await mock_groq_client.detect_command_type(user_message)
    assert command_type == "list"
    
    # Get schedule
    schedule = await schedule_manager.get_user_schedule(user_id)
    
    # Format for display
    formatted = schedule_manager.format_schedule_for_display(schedule)
    
    # Then: Should return formatted schedule
    assert "Вы принимаете:" in formatted
    assert "аспирин" in formatted
    assert "парацетамол" in formatted
    assert "10:00" in formatted
    assert "18:00" in formatted
