"""Schedule manager for medication bot."""

from typing import Optional

from loguru import logger

from src.data.models import Medication, UserData
from src.data.storage import DataManager


class ScheduleManager:
    """Manager for medication schedule CRUD operations.
    
    Handles all operations related to medication schedules:
    - Adding medications
    - Deleting medications
    - Updating medication times and dosages
    - Updating user timezone
    - Marking medications as taken
    - Retrieving and formatting schedules
    """
    
    def __init__(self, data_manager: DataManager):
        """Initialize schedule manager.
        
        Args:
            data_manager: DataManager instance for persistence
        """
        self.data_manager = data_manager
        logger.debug("ScheduleManager initialized")
    
    async def add_medication(
        self,
        user_id: int,
        name: str,
        times: list[str],
        dosage: Optional[str] = None,
    ) -> tuple[list[Medication], list[str]]:
        """Add medication(s) to user's schedule with duplicate detection.
        
        If multiple times are provided, creates separate medication entries
        for each time (same medication taken multiple times per day).
        Skips times that would create duplicates (same name and time).
        
        Args:
            user_id: Telegram user ID
            name: Medication name
            times: List of times in "HH:MM" format
            dosage: Optional dosage information
            
        Returns:
            Tuple of (created_medications, skipped_times):
                - created_medications: List of created Medication instances
                - skipped_times: List of times that were skipped as duplicates
            
        Raises:
            ValueError: If user doesn't exist or times list is empty
            
        Examples:
            >>> # Add medication with single time
            >>> created, skipped = await manager.add_medication(123, "Аспирин", ["10:00"], "200 мг")
            
            >>> # Add medication with multiple times (one duplicate)
            >>> created, skipped = await manager.add_medication(123, "Парацетамол", ["10:00", "18:00"])
            >>> # If 10:00 already exists, created will have only 18:00, skipped will be ["10:00"]
        """
        if not times:
            raise ValueError("Times list cannot be empty")
        
        # Load user data
        user_data = await self.data_manager.get_user_data(user_id)
        if user_data is None:
            logger.error(f"User {user_id} not found when adding medication")
            raise ValueError(f"User {user_id} not found")
        
        # Check for duplicates - case-insensitive name matching, exact time matching
        name_lower = name.lower()
        existing_medications = {
            (med.name.lower(), med.time)
            for med in user_data.medications
        }
        
        # Filter out duplicate times
        times_to_add = []
        skipped_times = []
        
        for time in times:
            if (name_lower, time) in existing_medications:
                skipped_times.append(time)
                logger.warning(
                    f"Skipping duplicate medication for user {user_id}: "
                    f"{name} at {time} already exists"
                )
            else:
                times_to_add.append(time)
        
        # Create medication entries for non-duplicate times
        created_medications = []
        for time in times_to_add:
            medication = user_data.add_medication(
                name=name,
                time=time,
                dosage=dosage,
            )
            created_medications.append(medication)
            logger.info(
                f"Added medication for user {user_id}: {name} at {time} "
                f"(dosage: {dosage or 'not specified'})"
            )
        
        # Save updated data only if medications were added
        if created_medications:
            await self.data_manager.save_user_data(user_data)
        
        # Log summary if there were duplicates
        if skipped_times:
            logger.info(
                f"Duplicate detection summary for user {user_id}: "
                f"added {len(created_medications)} time(s), "
                f"skipped {len(skipped_times)} duplicate(s) for {name}"
            )
        
        return created_medications, skipped_times
    
    async def delete_medications(
        self,
        user_id: int,
        medication_ids: list[int],
    ) -> bool:
        """Delete medication(s) by ID.
        
        Args:
            user_id: Telegram user ID
            medication_ids: List of medication IDs to delete
            
        Returns:
            True if at least one medication was deleted, False otherwise
            
        Raises:
            ValueError: If user doesn't exist
        """
        if not medication_ids:
            logger.warning(f"Empty medication_ids list for user {user_id}")
            return False
        
        # Load user data
        user_data = await self.data_manager.get_user_data(user_id)
        if user_data is None:
            logger.error(f"User {user_id} not found when deleting medications")
            raise ValueError(f"User {user_id} not found")
        
        # Remove medications
        removed_count = user_data.remove_medications(medication_ids)
        
        if removed_count > 0:
            # Save updated data
            await self.data_manager.save_user_data(user_data)
            logger.info(
                f"Deleted {removed_count} medication(s) for user {user_id}: "
                f"IDs {medication_ids}"
            )
            return True
        else:
            logger.warning(
                f"No medications deleted for user {user_id}: "
                f"IDs {medication_ids} not found"
            )
            return False
    
    async def update_medication_time(
        self,
        user_id: int,
        medication_id: int,
        new_times: list[str],
    ) -> list[Medication]:
        """Update medication time(s).
        
        If multiple times are provided, the original medication is deleted
        and new medication entries are created for each time.
        
        Args:
            user_id: Telegram user ID
            medication_id: ID of medication to update
            new_times: List of new times in "HH:MM" format
            
        Returns:
            List of medication instances (updated or newly created)
            
        Raises:
            ValueError: If user or medication not found, or times list is empty
        """
        if not new_times:
            raise ValueError("New times list cannot be empty")
        
        # Load user data
        user_data = await self.data_manager.get_user_data(user_id)
        if user_data is None:
            logger.error(f"User {user_id} not found when updating medication time")
            raise ValueError(f"User {user_id} not found")
        
        # Find medication
        medication = user_data.get_medication_by_id(medication_id)
        if medication is None:
            logger.error(
                f"Medication {medication_id} not found for user {user_id}"
            )
            raise ValueError(f"Medication {medication_id} not found")
        
        # Store medication details
        name = medication.name
        dosage = medication.dosage
        
        # If single time, update in place
        if len(new_times) == 1:
            medication.time = new_times[0]
            medication.last_taken = None  # Reset last taken
            medication.reminder_message_id = None  # Reset reminder
            
            await self.data_manager.save_user_data(user_data)
            logger.info(
                f"Updated medication {medication_id} time for user {user_id}: "
                f"{name} now at {new_times[0]}"
            )
            return [medication]
        
        # If multiple times, delete original and create new entries
        user_data.remove_medication(medication_id)
        
        created_medications = []
        for time in new_times:
            new_med = user_data.add_medication(
                name=name,
                time=time,
                dosage=dosage,
            )
            created_medications.append(new_med)
        
        await self.data_manager.save_user_data(user_data)
        logger.info(
            f"Updated medication {medication_id} times for user {user_id}: "
            f"{name} now at {', '.join(new_times)}"
        )
        
        return created_medications
    
    async def update_medication_dosage(
        self,
        user_id: int,
        medication_id: int,
        new_dosage: str,
    ) -> Medication:
        """Update medication dosage.
        
        Args:
            user_id: Telegram user ID
            medication_id: ID of medication to update
            new_dosage: New dosage information
            
        Returns:
            Updated Medication instance
            
        Raises:
            ValueError: If user or medication not found
        """
        # Load user data
        user_data = await self.data_manager.get_user_data(user_id)
        if user_data is None:
            logger.error(f"User {user_id} not found when updating medication dosage")
            raise ValueError(f"User {user_id} not found")
        
        # Find medication
        medication = user_data.get_medication_by_id(medication_id)
        if medication is None:
            logger.error(
                f"Medication {medication_id} not found for user {user_id}"
            )
            raise ValueError(f"Medication {medication_id} not found")
        
        # Update dosage
        old_dosage = medication.dosage
        medication.dosage = new_dosage
        
        await self.data_manager.save_user_data(user_data)
        logger.info(
            f"Updated medication {medication_id} dosage for user {user_id}: "
            f"{medication.name} from '{old_dosage}' to '{new_dosage}'"
        )
        
        return medication
    
    async def update_timezone(
        self,
        user_id: int,
        timezone_offset: str,
    ) -> None:
        """Update user's timezone offset.
        
        Args:
            user_id: Telegram user ID
            timezone_offset: New timezone offset (e.g., "+03:00", "-05:00")
            
        Raises:
            ValueError: If user not found
        """
        # Load user data
        user_data = await self.data_manager.get_user_data(user_id)
        if user_data is None:
            logger.error(f"User {user_id} not found when updating timezone")
            raise ValueError(f"User {user_id} not found")
        
        # Update timezone
        old_timezone = user_data.timezone_offset
        user_data.timezone_offset = timezone_offset
        
        await self.data_manager.save_user_data(user_data)
        logger.info(
            f"Updated timezone for user {user_id}: "
            f"from {old_timezone} to {timezone_offset}"
        )
    
    async def mark_medication_taken(
        self,
        user_id: int,
        medication_id: int,
    ) -> None:
        """Mark medication as taken (set current timestamp and clear reminder).
        
        Args:
            user_id: Telegram user ID
            medication_id: ID of medication to mark as taken
            
        Raises:
            ValueError: If user or medication not found
        """
        from datetime import datetime
        
        # Load user data
        user_data = await self.data_manager.get_user_data(user_id)
        if user_data is None:
            logger.error(f"User {user_id} not found when marking medication taken")
            raise ValueError(f"User {user_id} not found")
        
        # Find medication
        medication = user_data.get_medication_by_id(medication_id)
        if medication is None:
            logger.error(
                f"Medication {medication_id} not found for user {user_id}"
            )
            raise ValueError(f"Medication {medication_id} not found")
        
        # Mark as taken and clear reminder
        timestamp = int(datetime.utcnow().timestamp())
        medication.last_taken = timestamp
        medication.reminder_message_id = None  # Clear reminder so new one can be sent tomorrow
        
        await self.data_manager.save_user_data(user_data)
        logger.info(
            f"Marked medication {medication_id} as taken for user {user_id}: "
            f"{medication.name} at {medication.time}"
        )
    
    async def get_user_schedule(self, user_id: int) -> list[Medication]:
        """Get user's medication schedule.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of Medication instances, sorted by time
            
        Raises:
            ValueError: If user not found
        """
        # Load user data
        user_data = await self.data_manager.get_user_data(user_id)
        if user_data is None:
            logger.error(f"User {user_id} not found when getting schedule")
            raise ValueError(f"User {user_id} not found")
        
        # Sort medications by time
        medications = sorted(user_data.medications, key=lambda m: m.time)
        
        logger.debug(
            f"Retrieved schedule for user {user_id}: "
            f"{len(medications)} medication(s)"
        )
        
        return medications
    
    def format_schedule_for_display(self, medications: list[Medication]) -> str:
        """Format medication schedule for user display.
        
        Groups medications by name and displays times together.
        Format:
            Вы принимаете:
            1) в 10:00 — Аспирин 200 мг
            2) в 12:00 и 18:00 — Парацетамол 400 мг
        
        Args:
            medications: List of Medication instances
            
        Returns:
            Formatted schedule string in Russian
        """
        if not medications:
            return "У вас пока нет медикаментов в расписании."
        
        # Group medications by name and dosage
        grouped = {}
        for med in medications:
            key = (med.name, med.dosage or "")
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(med.time)
        
        # Format output
        lines = ["Вы принимаете:"]
        
        for idx, ((name, dosage), times) in enumerate(grouped.items(), start=1):
            # Sort times
            times_sorted = sorted(times)
            times_str = " и ".join(times_sorted)
            
            # Format dosage
            dosage_str = f" {dosage}" if dosage else ""
            
            # Add line
            lines.append(f"{idx}) в {times_str} — {name}{dosage_str}")
        
        result = "\n".join(lines)
        logger.debug(f"Formatted schedule: {len(grouped)} medication group(s)")
        
        return result
