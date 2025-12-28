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
    last_taken: Optional[int] = None,
) -> bool:
    """Check if it's time to take medication.
    
    Logic:
    - Current time must be >= medication time (same day)
    - If last_taken is None, return True
    - If last_taken is set, check if it was taken on a previous day
    
    Args:
        medication_time: Time to take medication in "HH:MM" format
        current_time: Current time in user's timezone
        last_taken: Unix timestamp of last intake or None
        
    Returns:
        True if it's time to take medication, False otherwise
        
    Examples:
        >>> # Current time is 10:30, medication time is 10:00, never taken
        >>> is_time_to_take("10:00", datetime(2024, 1, 1, 10, 30), None)
        True
        
        >>> # Current time is 10:30, medication time is 10:00, taken today
        >>> is_time_to_take("10:00", datetime(2024, 1, 1, 10, 30), 1704096000)
        False
        
        >>> # Current time is 09:30, medication time is 10:00
        >>> is_time_to_take("10:00", datetime(2024, 1, 1, 9, 30), None)
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
        
        # Check if current time is past medication time
        if current_time < med_datetime:
            logger.debug(
                f"Not time yet: current {current_time.strftime('%H:%M')} < "
                f"medication {medication_time}"
            )
            return False
        
        # If never taken, it's time to take
        if last_taken is None:
            logger.debug(f"Time to take (never taken): {medication_time}")
            return True
        
        # Check if last taken was on a previous day
        last_taken_datetime = datetime.fromtimestamp(last_taken)
        
        # Compare dates (ignore time)
        last_taken_date = last_taken_datetime.date()
        current_date = current_time.date()
        
        if current_date > last_taken_date:
            logger.debug(
                f"Time to take (last taken on previous day): {medication_time}, "
                f"last taken: {last_taken_date}"
            )
            return True
        
        logger.debug(
            f"Already taken today: {medication_time}, "
            f"last taken: {last_taken_datetime.strftime('%Y-%m-%d %H:%M')}"
        )
        return False
        
    except (ValueError, AttributeError) as e:
        logger.error(
            f"Error checking medication time: medication_time={medication_time}, "
            f"current_time={current_time}, last_taken={last_taken}, error={e}"
        )
        return False
