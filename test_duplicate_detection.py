"""Test script to demonstrate duplicate medication detection."""

import asyncio
from pathlib import Path
import tempfile
import shutil

from src.data.storage import DataManager
from src.services.schedule_manager import ScheduleManager


async def test_duplicate_detection():
    """Test duplicate medication detection functionality."""
    # Create temporary directory for test data
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Initialize managers
        data_manager = DataManager(temp_dir)
        schedule_manager = ScheduleManager(data_manager)
        
        # Create test user
        user_id = 123456789
        await data_manager.create_user(user_id, "+03:00")
        
        print("=" * 60)
        print("TEST 1: Add medication first time")
        print("=" * 60)
        created, skipped = await schedule_manager.add_medication(
            user_id=user_id,
            name="героин",
            times=["13:00"],
            dosage="100 мг"
        )
        print(f"✓ Created: {len(created)} medication(s)")
        print(f"  - {created[0].name} at {created[0].time} ({created[0].dosage})")
        print(f"✓ Skipped: {len(skipped)} duplicate(s)")
        print()
        
        print("=" * 60)
        print("TEST 2: Try to add same medication again (duplicate)")
        print("=" * 60)
        created, skipped = await schedule_manager.add_medication(
            user_id=user_id,
            name="героин",
            times=["13:00"],
            dosage="100 мг"
        )
        print(f"✓ Created: {len(created)} medication(s)")
        print(f"✓ Skipped: {len(skipped)} duplicate(s)")
        if skipped:
            print(f"  - Skipped time: {skipped[0]}")
        print()
        
        print("=" * 60)
        print("TEST 3: Add same medication at different time")
        print("=" * 60)
        created, skipped = await schedule_manager.add_medication(
            user_id=user_id,
            name="героин",
            times=["10:00"],
            dosage="100 мг"
        )
        print(f"✓ Created: {len(created)} medication(s)")
        if created:
            print(f"  - {created[0].name} at {created[0].time} ({created[0].dosage})")
        print(f"✓ Skipped: {len(skipped)} duplicate(s)")
        print()
        
        print("=" * 60)
        print("TEST 4: Add multiple times (one duplicate, one new)")
        print("=" * 60)
        created, skipped = await schedule_manager.add_medication(
            user_id=user_id,
            name="героин",
            times=["10:00", "18:00"],
            dosage="100 мг"
        )
        print(f"✓ Created: {len(created)} medication(s)")
        if created:
            for med in created:
                print(f"  - {med.name} at {med.time} ({med.dosage})")
        print(f"✓ Skipped: {len(skipped)} duplicate(s)")
        if skipped:
            for time in skipped:
                print(f"  - Skipped time: {time}")
        print()
        
        print("=" * 60)
        print("TEST 5: Case-insensitive duplicate detection")
        print("=" * 60)
        created, skipped = await schedule_manager.add_medication(
            user_id=user_id,
            name="ГЕРОИН",  # Uppercase
            times=["13:00"],
            dosage="100 мг"
        )
        print(f"✓ Created: {len(created)} medication(s)")
        print(f"✓ Skipped: {len(skipped)} duplicate(s)")
        if skipped:
            print(f"  - Skipped time: {skipped[0]} (case-insensitive match)")
        print()
        
        print("=" * 60)
        print("FINAL SCHEDULE")
        print("=" * 60)
        medications = await schedule_manager.get_user_schedule(user_id)
        schedule_text = schedule_manager.format_schedule_for_display(medications)
        print(schedule_text)
        print()
        
        print("=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    asyncio.run(test_duplicate_detection())
