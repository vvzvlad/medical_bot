"""Timezone utility functions for medication bot."""

from datetime import datetime, timedelta
from typing import Optional

from loguru import logger


def parse_timezone_offset(offset_str: str) -> timedelta:
    """Parse timezone offset string to timedelta.
    
    Args:
        offset_str: Timezone offset in format "+03:00" or "-05:00"
        
    Returns:
        timedelta representing the offset
        
    Raises:
        ValueError: If offset string format is invalid
        
    Examples:
        >>> parse_timezone_offset("+03:00")
        timedelta(hours=3)
        >>> parse_timezone_offset("-05:00")
        timedelta(hours=-5)
    """
    try:
        # Remove whitespace
        offset_str = offset_str.strip()
        
        # Check format
        if len(offset_str) != 6 or offset_str[0] not in ['+', '-']:
            raise ValueError(f"Invalid timezone offset format: {offset_str}")
        
        # Parse sign
        sign = 1 if offset_str[0] == '+' else -1
        
        # Parse hours and minutes
        hours_str, minutes_str = offset_str[1:].split(':')
        hours = int(hours_str)
        minutes = int(minutes_str)
        
        # Validate ranges
        if not (0 <= hours <= 14):
            raise ValueError(f"Hours out of range: {hours}")
        if not (0 <= minutes <= 59):
            raise ValueError(f"Minutes out of range: {minutes}")
        
        # Create timedelta
        total_minutes = sign * (hours * 60 + minutes)
        return timedelta(minutes=total_minutes)
        
    except (ValueError, IndexError) as e:
        logger.error(f"Failed to parse timezone offset '{offset_str}': {e}")
        raise ValueError(f"Invalid timezone offset format: {offset_str}") from e


def get_user_current_time(timezone_offset: str) -> datetime:
    """Get current time in user's timezone.
    
    Args:
        timezone_offset: User's timezone offset (e.g., "+03:00", "-05:00")
        
    Returns:
        Current datetime in user's timezone (naive datetime)
        
    Examples:
        >>> # If UTC time is 10:00
        >>> get_user_current_time("+03:00")
        # Returns datetime with time 13:00
    """
    try:
        offset = parse_timezone_offset(timezone_offset)
        utc_now = datetime.utcnow()
        user_time = utc_now + offset
        
        logger.debug(
            f"Converted UTC {utc_now.strftime('%H:%M:%S')} to "
            f"user time {user_time.strftime('%H:%M:%S')} "
            f"(offset: {timezone_offset})"
        )
        
        return user_time
        
    except Exception as e:
        logger.error(f"Error getting user current time: {e}")
        raise


def is_time_to_take(
    medication_time: str,
    current_time: datetime,
    timezone_offset: str,
    last_taken: Optional[int] = None,
    reminder_message_id: Optional[int] = None,
) -> bool:
    """Check if it's time to take medication.
    
    Logic:
    - Current time must be >= medication time
    - If last_taken is set and is today, return False (already taken)
    - If reminder_message_id is set (reminder already sent today), return False
    - Otherwise return True to send reminder
    
    Args:
        medication_time: Time to take medication in "HH:MM" format
        current_time: Current time in user's timezone
        timezone_offset: User's timezone offset (e.g., "+03:00")
        last_taken: Unix timestamp of last intake or None
        reminder_message_id: Telegram message ID of active reminder or None
        
    Returns:
        True if it's time to send reminder, False otherwise
        
    Examples:
        >>> # Current time is 10:30, medication time is 10:00, never taken
        >>> is_time_to_take("10:00", datetime(2024, 1, 1, 10, 30), "+03:00", None, None)
        True
        
        >>> # Current time is 10:30, medication time is 10:00, taken today
        >>> is_time_to_take("10:00", datetime(2024, 1, 1, 10, 30), "+03:00", 1704096000, None)
        False
        
        >>> # Current time is 09:30, medication time is 10:00
        >>> is_time_to_take("10:00", datetime(2024, 1, 1, 9, 30), "+03:00", None, None)
        False
    """
    try:
        # Parse medication time
        med_hour, med_minute = map(int, medication_time.split(':'))
        
        # Create datetime for medication time today
        med_datetime = current_time.replace(
            hour=med_hour,
            minute=med_minute,
            second=0,
            microsecond=0
        )
        
        # Check if current time is before medication time
        if current_time < med_datetime:
            logger.debug(
                f"Not time yet: current {current_time.strftime('%H:%M')} < "
                f"medication {medication_time}"
            )
            return False
        
        # Check if already taken today
        if last_taken is not None:
            # Convert last_taken UTC timestamp to user's timezone for date comparison
            last_taken_utc = datetime.utcfromtimestamp(last_taken)
            
            # Parse timezone offset and apply it to get the date in user's timezone
            offset = parse_timezone_offset(timezone_offset)
            last_taken_user_tz = last_taken_utc + offset
            
            # Compare dates in user's timezone
            last_taken_date = last_taken_user_tz.date()
            current_date = current_time.date()
            
            if current_date == last_taken_date:
                logger.debug(
                    f"Already taken today: {medication_time}, "
                    f"last taken: {last_taken_user_tz.strftime('%Y-%m-%d %H:%M')} (user timezone)"
                )
                return False
        
        # Check if reminder already sent (and not yet taken)
        # If reminder_message_id is set, it means we already sent a reminder
        # and user hasn't clicked the button yet
        if reminder_message_id is not None:
            logger.debug(
                f"Reminder already sent for {medication_time}, "
                f"message_id: {reminder_message_id}"
            )
            return False
        
        # Time to send reminder
        logger.debug(f"Time to take: {medication_time}")
        return True
        
    except (ValueError, AttributeError) as e:
        logger.error(
            f"Error checking medication time: medication_time={medication_time}, "
            f"current_time={current_time}, last_taken={last_taken}, error={e}"
        )
        return False
