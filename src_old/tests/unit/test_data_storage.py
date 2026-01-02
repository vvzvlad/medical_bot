"""Unit tests for data storage."""

import asyncio
import json

import pytest

from src.data.models import UserData
from src.data.storage import DataManager


# TC-STORAGE-001: Create New User
@pytest.mark.asyncio
async def test_create_new_user(data_manager, temp_data_dir):
    """Test creating a new user file."""
    # Given: User doesn't exist
    user_id = 123456789
    timezone_offset = "+03:00"
    
    # When: Creating new user
    user_data = await data_manager.create_user(user_id, timezone_offset)
    
    # Then: User file should exist
    user_file = temp_data_dir / f"{user_id}.json"
    assert user_file.exists()
    
    # And: User data should be correct
    assert user_data.user_id == user_id
    assert user_data.timezone_offset == timezone_offset
    assert user_data.medications == []


# TC-STORAGE-002: Load Existing User
@pytest.mark.asyncio
async def test_load_existing_user(data_manager, temp_data_dir):
    """Test loading existing user data."""
    # Given: User file exists
    user_id = 123456789
    user_file = temp_data_dir / f"{user_id}.json"
    user_file.write_text(json.dumps({
        "user_id": user_id,
        "timezone_offset": "+03:00",
        "medications": [
            {
                "id": 1,
                "name": "аспирин",
                "dosage": "200 мг",
                "time": "10:00",
                "last_taken": None,
                "reminder_message_id": None
            }
        ]
    }, ensure_ascii=False))
    
    # When: Loading user data
    user_data = await data_manager.get_user_data(user_id)
    
    # Then: Data should be loaded correctly
    assert user_data.user_id == user_id
    assert len(user_data.medications) == 1
    assert user_data.medications[0].name == "аспирин"


# TC-STORAGE-003: Atomic Write Success
@pytest.mark.asyncio
async def test_atomic_write_success(data_manager, temp_data_dir):
    """Test atomic write pattern."""
    # Given: User data
    user_id = 123456789
    user_data = UserData(user_id=user_id, timezone_offset="+03:00", medications=[])
    
    # When: Saving user data
    await data_manager.save_user_data(user_data)
    
    # Then: Final file should exist
    user_file = temp_data_dir / f"{user_id}.json"
    assert user_file.exists()
    
    # And: Temp file should not exist
    temp_file = temp_data_dir / f"{user_id}.json.tmp"
    assert not temp_file.exists()


# TC-STORAGE-004: Atomic Write Failure Recovery
@pytest.mark.asyncio
async def test_atomic_write_failure_recovery(data_manager, temp_data_dir, monkeypatch):
    """Test recovery from write failure."""
    # Given: Write operation will fail
    user_id = 123456789
    user_data = UserData(user_id=user_id, timezone_offset="+03:00", medications=[])
    
    # Mock aiofiles.open to fail with proper async context manager
    import aiofiles
    
    class MockAsyncFile:
        async def __aenter__(self):
            raise IOError("Disk full")
        
        async def __aexit__(self, *args):
            pass
    
    def mock_open_fail(*args, **kwargs):
        if 'w' in kwargs.get('mode', ''):
            return MockAsyncFile()
        return aiofiles.open(*args, **kwargs)
    
    monkeypatch.setattr("aiofiles.open", mock_open_fail)
    
    # When: Attempting to save
    with pytest.raises(IOError):
        await data_manager.save_user_data(user_data)
    
    # Then: Temp file should be cleaned up
    temp_file = temp_data_dir / f"{user_id}.json.tmp"
    assert not temp_file.exists()


# TC-STORAGE-005: Corrupted File Recovery
@pytest.mark.asyncio
async def test_corrupted_file_recovery(data_manager, temp_data_dir):
    """Test recovery from corrupted JSON file."""
    # Given: Corrupted user file
    user_id = 123456789
    user_file = temp_data_dir / f"{user_id}.json"
    user_file.write_text("{ invalid json }")
    
    # When: Loading user data
    user_data = await data_manager.get_user_data(user_id)
    
    # Then: Should return None (file removed)
    assert user_data is None
    
    # And: Corrupted file should be removed
    assert not user_file.exists()


# TC-STORAGE-006: Add Medication Updates File
@pytest.mark.asyncio
async def test_add_medication_updates_file(data_manager, schedule_manager, temp_data_dir):
    """Test that adding medication updates user file."""
    # Given: Existing user
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    # When: Adding medication
    await schedule_manager.add_medication(
        user_id=user_id,
        name="аспирин",
        times=["10:00"],
        dosage="200 мг"
    )
    
    # Then: File should be updated
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 1
    assert user_data.medications[0].name == "аспирин"
    
    # And: File on disk should match
    user_file = temp_data_dir / f"{user_id}.json"
    file_content = json.loads(user_file.read_text())
    assert len(file_content["medications"]) == 1


# TC-STORAGE-007: Delete Medication Updates File
@pytest.mark.asyncio
async def test_delete_medication_updates_file(data_manager, schedule_manager, temp_data_dir):
    """Test that deleting medication updates user file."""
    # Given: User with medication
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    meds, skipped = await schedule_manager.add_medication(user_id, "аспирин", ["10:00"], "200 мг")
    medication_id = meds[0].id
    
    # When: Deleting medication
    await schedule_manager.delete_medications(user_id, [medication_id])
    
    # Then: File should be updated
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data.medications) == 0
    
    # And: File on disk should match
    user_file = temp_data_dir / f"{user_id}.json"
    file_content = json.loads(user_file.read_text())
    assert len(file_content["medications"]) == 0


# TC-STORAGE-008: Update Time Updates File
@pytest.mark.asyncio
async def test_update_time_updates_file(data_manager, schedule_manager, temp_data_dir):
    """Test that updating time updates user file."""
    # Given: User with medication
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    meds, skipped = await schedule_manager.add_medication(user_id, "аспирин", ["10:00"], "200 мг")
    medication_id = meds[0].id
    
    # When: Updating time
    await schedule_manager.update_medication_time(user_id, medication_id, ["11:00"])
    
    # Then: File should be updated
    user_data = await data_manager.get_user_data(user_id)
    assert user_data.medications[0].time == "11:00"
    
    # And: File on disk should match
    user_file = temp_data_dir / f"{user_id}.json"
    file_content = json.loads(user_file.read_text())
    assert file_content["medications"][0]["time"] == "11:00"


# TC-STORAGE-009: Mark Taken Updates File
@pytest.mark.asyncio
async def test_mark_taken_updates_file(data_manager, schedule_manager, temp_data_dir):
    """Test that marking medication as taken updates user file."""
    # Given: User with medication
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    meds, skipped = await schedule_manager.add_medication(user_id, "аспирин", ["10:00"], "200 мг")
    medication_id = meds[0].id
    
    # When: Marking as taken
    await schedule_manager.mark_medication_taken(user_id, medication_id)
    
    # Then: File should be updated
    user_data = await data_manager.get_user_data(user_id)
    assert user_data.medications[0].last_taken is not None
    
    # And: File on disk should match
    user_file = temp_data_dir / f"{user_id}.json"
    file_content = json.loads(user_file.read_text())
    assert file_content["medications"][0]["last_taken"] is not None


# TC-STORAGE-010: Concurrent Write Safety
@pytest.mark.asyncio
async def test_concurrent_write_safety(data_manager, temp_data_dir):
    """Test that concurrent writes don't corrupt data."""
    # Given: User data
    user_id = 123456789
    user_data = UserData(user_id=user_id, timezone_offset="+03:00", medications=[])
    
    # When: Multiple concurrent writes
    tasks = [
        data_manager.save_user_data(user_data)
        for _ in range(10)
    ]
    await asyncio.gather(*tasks)
    
    # Then: File should be valid
    loaded_data = await data_manager.get_user_data(user_id)
    assert loaded_data is not None
    assert loaded_data.user_id == user_id


# Additional test: User exists check
@pytest.mark.asyncio
async def test_user_exists(data_manager):
    """Test checking if user exists."""
    user_id = 123456789
    
    # Initially user doesn't exist
    assert not data_manager.user_exists(user_id)
    
    # After creating user
    await data_manager.create_user(user_id, "+03:00")
    assert data_manager.user_exists(user_id)


# Additional test: Get all user IDs
@pytest.mark.asyncio
async def test_get_all_user_ids(data_manager):
    """Test getting all user IDs."""
    # Create multiple users
    await data_manager.create_user(111, "+03:00")
    await data_manager.create_user(222, "+03:00")
    await data_manager.create_user(333, "+03:00")
    
    # Get all user IDs
    user_ids = data_manager.get_all_user_ids()
    
    assert len(user_ids) == 3
    assert 111 in user_ids
    assert 222 in user_ids
    assert 333 in user_ids


# Additional test: Delete user
@pytest.mark.asyncio
async def test_delete_user(data_manager):
    """Test deleting user."""
    user_id = 123456789
    
    # Create user
    await data_manager.create_user(user_id, "+03:00")
    assert data_manager.user_exists(user_id)
    
    # Delete user
    result = await data_manager.delete_user(user_id)
    assert result is True
    assert not data_manager.user_exists(user_id)
    
    # Try to delete non-existent user
    result = await data_manager.delete_user(user_id)
    assert result is False
