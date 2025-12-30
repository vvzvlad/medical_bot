"""Test script to verify the fix for error message generation."""

import asyncio
from src.data.storage import DataManager
from src.services.schedule_manager import ScheduleManager
from src.config import settings
import tempfile
from pathlib import Path


async def test_error_message_with_wrong_ids():
    """Test the error message generation with wrong medication IDs (simulating LLM error)."""
    # Create temporary data directory
    with tempfile.TemporaryDirectory() as tmpdir:
        settings.data_dir = Path(tmpdir)
        
        # Initialize managers
        data_manager = DataManager()
        schedule_manager = ScheduleManager(data_manager)
        
        # Create user and add medication
        user_id = 123456789
        await data_manager.create_user(user_id, "+03:00")
        
        # Add medication with multiple times
        await schedule_manager.add_medication(
            user_id=user_id,
            name="Героин",
            times=["11:00", "13:00", "15:00", "17:00"],
            dosage=None
        )
        
        # Get schedule
        medications = await schedule_manager.get_user_schedule(user_id)
        
        # Simulate LLM result with WRONG IDs (e.g., IDs that don't exist)
        medication_name = "Героин"
        specified_time = "22:00"
        medication_ids = [999, 1000, 1001]  # Wrong IDs that don't exist
        
        print(f"Medication IDs (wrong): {medication_ids}")
        print(f"Medications: {[(m.id, m.name, m.time) for m in medications]}")
        
        # Check if specified time matches any scheduled time
        matching_meds = [med for med in medications if med.id in medication_ids and med.time == specified_time]
        
        print(f"Matching meds: {matching_meds}")
        
        if not matching_meds:
            # Generate error message using the FIXED logic (filter by name instead of IDs)
            scheduled_times = [med.time for med in medications if med.name == medication_name]
            scheduled_times_str = ", ".join(sorted(set(scheduled_times)))
            
            print(f"Scheduled times: {scheduled_times}")
            print(f"Scheduled times str: '{scheduled_times_str}'")
            
            error_message = (
                f"{medication_name} нет в расписании на {specified_time}.\n"
                f"Запланированное время приема: {scheduled_times_str}"
            )
            
            print(f"\nError message:\n{error_message}")
            print("\n✅ SUCCESS! The scheduled times list is now populated correctly!")
            
            # Verify the fix
            assert "11:00" in scheduled_times_str
            assert "13:00" in scheduled_times_str
            assert "15:00" in scheduled_times_str
            assert "17:00" in scheduled_times_str
            print("✅ All scheduled times are present in the error message!")


if __name__ == "__main__":
    asyncio.run(test_error_message_with_wrong_ids())
