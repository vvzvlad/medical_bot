"""Integration test for duplicate medication detection functionality."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

from src.data.storage import DataManager
from src.services.schedule_manager import ScheduleManager


@pytest.mark.asyncio
async def test_duplicate_medication_detection():
    """Test that duplicate medications are properly detected and prevented."""
    
    # Create temporary directory for test data
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Initialize managers
        data_manager = DataManager(temp_dir)
        schedule_manager = ScheduleManager(data_manager)
        
        # Create test user
        user_id = 123456789
        await data_manager.create_user(user_id, "+03:00")
        
        # TEST 1: Add medication first time
        created, skipped = await schedule_manager.add_medication(
            user_id=user_id,
            name="героин",
            times=["13:00"],
            dosage="100 мг"
        )
        
        # Verify first medication was created
        assert len(created) == 1
        assert created[0].name == "героин"
        assert created[0].time == "13:00"
        assert created[0].dosage == "100 мг"
        assert len(skipped) == 0
        
        # TEST 2: Try to add same medication again (duplicate)
        created, skipped = await schedule_manager.add_medication(
            user_id=user_id,
            name="героин",
            times=["13:00"],
            dosage="100 мг"
        )
        
        # Verify duplicate was skipped
        assert len(created) == 0
        assert len(skipped) == 1
        assert skipped[0] == "13:00"
        
        # TEST 3: Add same medication at different time
        created, skipped = await schedule_manager.add_medication(
            user_id=user_id,
            name="героин",
            times=["10:00"],
            dosage="100 мг"
        )
        
        # Verify new time was created
        assert len(created) == 1
        assert created[0].name == "героин"
        assert created[0].time == "10:00"
        assert created[0].dosage == "100 мг"
        assert len(skipped) == 0
        
        # TEST 4: Add multiple times (one duplicate, one new)
        created, skipped = await schedule_manager.add_medication(
            user_id=user_id,
            name="героин",
            times=["10:00", "18:00"],
            dosage="100 мг"
        )
        
        # Verify only new time was created, duplicate was skipped
        assert len(created) == 1
        assert created[0].time == "18:00"
        assert len(skipped) == 1
        assert skipped[0] == "10:00"
        
        # TEST 5: Case-insensitive duplicate detection
        created, skipped = await schedule_manager.add_medication(
            user_id=user_id,
            name="ГЕРОИН",  # Uppercase
            times=["13:00"],
            dosage="100 мг"
        )
        
        # Verify case-insensitive duplicate was skipped
        assert len(created) == 0
        assert len(skipped) == 1
        assert skipped[0] == "13:00"
        
        # TEST 6: Verify final schedule
        medications = await schedule_manager.get_user_schedule(user_id)
        schedule_text = schedule_manager.format_schedule_for_display(medications)
        
        # Should have 3 medications total (13:00, 10:00, 18:00)
        assert len(medications) == 3
        
        # Verify the schedule text contains expected medications
        assert "героин" in schedule_text
        assert "13:00" in schedule_text
        assert "10:00" in schedule_text
        assert "18:00" in schedule_text
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_duplicate_detection_with_different_dosages():
    """Test that medications with same name but different dosages are handled correctly."""
    
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        data_manager = DataManager(temp_dir)
        schedule_manager = ScheduleManager(data_manager)
        
        user_id = 123456790
        await data_manager.create_user(user_id, "+03:00")
        
        # Add medication with specific dosage
        created, skipped = await schedule_manager.add_medication(
            user_id=user_id,
            name="аспирин",
            times=["09:00"],
            dosage="200 мг"
        )
        
        assert len(created) == 1
        assert created[0].dosage == "200 мг"
        
        # Try to add same medication with different dosage at same time
        created, skipped = await schedule_manager.add_medication(
            user_id=user_id,
            name="аспирин",
            times=["09:00"],
            dosage="300 мг"  # Different dosage
        )
        
        # Should be treated as duplicate since name and time match
        assert len(created) == 0
        assert len(skipped) == 1
        assert skipped[0] == "09:00"
        
    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_empty_times_validation():
    """Test that empty times list is properly handled."""
    
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        data_manager = DataManager(temp_dir)
        schedule_manager = ScheduleManager(data_manager)
        
        user_id = 123456791
        await data_manager.create_user(user_id, "+03:00")
        
        # Try to add medication with empty times list
        with pytest.raises(ValueError, match="Times list cannot be empty"):
            await schedule_manager.add_medication(
                user_id=user_id,
                name="тест",
                times=[],
                dosage="100 мг"
            )
        
    finally:
        shutil.rmtree(temp_dir)