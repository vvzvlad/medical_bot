"""Notification manager for medication bot."""

from datetime import datetime
from typing import Optional

from loguru import logger

from src.data.models import Medication, UserData
from src.data.storage import DataManager
from src.utils.timezone import get_user_current_time, is_time_to_take


class NotificationManager:
    """Manager for medication notification logic.
    
    Handles all operations related to medication reminders:
    - Determining which medications need reminders
    - Formatting reminder messages
    - Creating inline keyboard structures
    - Checking if reminders should be sent
    """
    
    def __init__(self, data_manager: DataManager):
        """Initialize notification manager.
        
        Args:
            data_manager: DataManager instance for data access
        """
        self.data_manager = data_manager
        logger.debug("NotificationManager initialized")
    
    async def get_medications_to_remind(self, user_id: int) -> list[Medication]:
        """Get medications that need reminders.
        
        Checks all user's medications and returns those that:
        - Current time >= medication time
        - Not taken today (last_taken is None or from previous day)
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of Medication instances that need reminders, sorted by time
            
        Raises:
            ValueError: If user not found
        """
        # Load user data
        user_data = await self.data_manager.get_user_data(user_id)
        if user_data is None:
            logger.error(f"User {user_id} not found when getting medications to remind")
            raise ValueError(f"User {user_id} not found")
        
        # Get current time in user's timezone
        current_time = get_user_current_time(user_data.timezone_offset)
        
        # Filter medications that need reminders
        medications_to_remind = []
        for medication in user_data.medications:
            if self.should_send_reminder(medication, current_time):
                medications_to_remind.append(medication)
        
        # Sort by time
        medications_to_remind.sort(key=lambda m: m.time)
        
        logger.debug(
            f"Found {len(medications_to_remind)} medication(s) to remind "
            f"for user {user_id}"
        )
        
        return medications_to_remind
    
    def should_send_reminder(
        self,
        medication: Medication,
        current_time: datetime,
    ) -> bool:
        """Check if reminder should be sent for medication.
        
        Uses timezone utilities to determine if it's time to take medication.
        
        Args:
            medication: Medication instance
            current_time: Current time in user's timezone
            
        Returns:
            True if reminder should be sent, False otherwise
        """
        return is_time_to_take(
            medication_time=medication.time,
            current_time=current_time,
            last_taken=medication.last_taken,
            reminder_message_id=medication.reminder_message_id,
        )
    
    def format_reminder_message(self, medications: list[Medication]) -> str:
        """Format reminder message text.
        
        Format:
            Надо принять:
            Аспирин 200 мг
            Парацетамол 400 мг
        
        Args:
            medications: List of Medication instances to remind about
            
        Returns:
            Formatted reminder message in Russian
        """
        if not medications:
            return ""
        
        lines = ["Надо принять:"]
        
        for medication in medications:
            # Format medication line
            dosage_str = f" {medication.dosage}" if medication.dosage else ""
            lines.append(f"{medication.name}{dosage_str}")
        
        result = "\n".join(lines)
        logger.debug(f"Formatted reminder message for {len(medications)} medication(s)")
        
        return result
    
    def create_reminder_keyboard(self, medications: list[Medication]) -> dict:
        """Create inline keyboard data structure for reminder.
        
        Creates a button for each medication. The keyboard structure is
        returned as a dictionary that can be used by the bot layer to
        create actual Telegram inline keyboard.
        
        Structure:
            {
                "inline_keyboard": [
                    [{"text": "Аспирин", "callback_data": "taken:1"}],
                    [{"text": "Парацетамол", "callback_data": "taken:2"}],
                ]
            }
        
        Args:
            medications: List of Medication instances
            
        Returns:
            Dictionary with inline keyboard structure
        """
        if not medications:
            return {"inline_keyboard": []}
        
        # Create button for each medication
        buttons = []
        for medication in medications:
            button = {
                "text": medication.name,
                "callback_data": f"taken:{medication.id}",
            }
            buttons.append([button])  # Each button on separate row
        
        keyboard = {"inline_keyboard": buttons}
        
        logger.debug(
            f"Created reminder keyboard with {len(buttons)} button(s)"
        )
        
        return keyboard
    
    async def get_medications_by_name(
        self,
        user_id: int,
        medication_name: str,
    ) -> list[Medication]:
        """Get all medications with given name for user.
        
        Helper method for finding medications by name (case-insensitive).
        Useful for handling "done" commands where user mentions medication name.
        
        Args:
            user_id: Telegram user ID
            medication_name: Name of medication to find
            
        Returns:
            List of Medication instances with matching name
            
        Raises:
            ValueError: If user not found
        """
        # Load user data
        user_data = await self.data_manager.get_user_data(user_id)
        if user_data is None:
            logger.error(f"User {user_id} not found when getting medications by name")
            raise ValueError(f"User {user_id} not found")
        
        # Find medications with matching name (case-insensitive)
        name_lower = medication_name.lower()
        matching_medications = [
            med for med in user_data.medications
            if med.name.lower() == name_lower
        ]
        
        logger.debug(
            f"Found {len(matching_medications)} medication(s) with name "
            f"'{medication_name}' for user {user_id}"
        )
        
        return matching_medications
    
    async def find_closest_medication_by_time(
        self,
        user_id: int,
        medication_ids: list[int],
    ) -> Optional[Medication]:
        """Find medication closest to current time from given IDs.
        
        Used when user marks medication as taken and there are multiple
        medications with same name. Selects the one closest to current time.
        
        Args:
            user_id: Telegram user ID
            medication_ids: List of medication IDs to choose from
            
        Returns:
            Medication instance closest to current time, or None if not found
            
        Raises:
            ValueError: If user not found
        """
        if not medication_ids:
            return None
        
        # Load user data
        user_data = await self.data_manager.get_user_data(user_id)
        if user_data is None:
            logger.error(
                f"User {user_id} not found when finding closest medication"
            )
            raise ValueError(f"User {user_id} not found")
        
        # Get current time in user's timezone
        current_time = get_user_current_time(user_data.timezone_offset)
        current_minutes = current_time.hour * 60 + current_time.minute
        
        # Find medications with given IDs
        medications = [
            med for med in user_data.medications
            if med.id in medication_ids
        ]
        
        if not medications:
            logger.warning(
                f"No medications found with IDs {medication_ids} "
                f"for user {user_id}"
            )
            return None
        
        # Find closest by time
        closest_medication = None
        min_time_diff = float('inf')
        
        for medication in medications:
            # Parse medication time
            med_hour, med_minute = map(int, medication.time.split(':'))
            med_minutes = med_hour * 60 + med_minute
            
            # Calculate time difference (absolute value)
            time_diff = abs(current_minutes - med_minutes)
            
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                closest_medication = medication
        
        if closest_medication:
            logger.debug(
                f"Found closest medication for user {user_id}: "
                f"{closest_medication.name} at {closest_medication.time} "
                f"(time diff: {min_time_diff} minutes)"
            )
        
        return closest_medication
    
    async def should_delete_previous_reminder(
        self,
        user_id: int,
        medication_name: str,
        current_medication_id: int,
    ) -> Optional[int]:
        """Check if previous reminder should be deleted.
        
        According to business logic: if same medication (by name) time comes,
        delete previous reminder and consider that intake was done.
        
        Args:
            user_id: Telegram user ID
            medication_name: Name of medication
            current_medication_id: ID of current medication
            
        Returns:
            Message ID of previous reminder to delete, or None
            
        Raises:
            ValueError: If user not found
        """
        # Load user data
        user_data = await self.data_manager.get_user_data(user_id)
        if user_data is None:
            logger.error(
                f"User {user_id} not found when checking previous reminder"
            )
            raise ValueError(f"User {user_id} not found")
        
        # Find other medications with same name that have reminder_message_id
        name_lower = medication_name.lower()
        for medication in user_data.medications:
            if (medication.id != current_medication_id and
                medication.name.lower() == name_lower and
                medication.reminder_message_id is not None):
                
                logger.info(
                    f"Found previous reminder for {medication_name} "
                    f"(medication ID {medication.id}, message ID "
                    f"{medication.reminder_message_id}) for user {user_id}"
                )
                
                return medication.reminder_message_id
        
        return None
    
    async def clear_reminder_message_id(
        self,
        user_id: int,
        medication_id: int,
    ) -> None:
        """Clear reminder_message_id for medication.
        
        Args:
            user_id: Telegram user ID
            medication_id: ID of medication
            
        Raises:
            ValueError: If user or medication not found
        """
        # Load user data
        user_data = await self.data_manager.get_user_data(user_id)
        if user_data is None:
            logger.error(
                f"User {user_id} not found when clearing reminder message ID"
            )
            raise ValueError(f"User {user_id} not found")
        
        # Find medication
        medication = user_data.get_medication_by_id(medication_id)
        if medication is None:
            logger.error(
                f"Medication {medication_id} not found for user {user_id}"
            )
            raise ValueError(f"Medication {medication_id} not found")
        
        # Clear reminder message ID
        medication.reminder_message_id = None
        
        await self.data_manager.save_user_data(user_data)
        logger.debug(
            f"Cleared reminder message ID for medication {medication_id} "
            f"of user {user_id}"
        )
    
    async def set_reminder_message_id(
        self,
        user_id: int,
        medication_id: int,
        message_id: int,
    ) -> None:
        """Set reminder_message_id for medication.
        
        Args:
            user_id: Telegram user ID
            medication_id: ID of medication
            message_id: Telegram message ID
            
        Raises:
            ValueError: If user or medication not found
        """
        # Load user data
        user_data = await self.data_manager.get_user_data(user_id)
        if user_data is None:
            logger.error(
                f"User {user_id} not found when setting reminder message ID"
            )
            raise ValueError(f"User {user_id} not found")
        
        # Find medication
        medication = user_data.get_medication_by_id(medication_id)
        if medication is None:
            logger.error(
                f"Medication {medication_id} not found for user {user_id}"
            )
            raise ValueError(f"Medication {medication_id} not found")
        
        # Set reminder message ID
        medication.reminder_message_id = message_id
        
        await self.data_manager.save_user_data(user_data)
        logger.debug(
            f"Set reminder message ID {message_id} for medication "
            f"{medication_id} of user {user_id}"
        )
