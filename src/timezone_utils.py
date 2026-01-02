"""Timezone utilities for medication bot."""

from datetime import datetime, timedelta, timezone
from typing import Optional


def parse_timezone_offset(offset_str: str) -> timedelta:
    """Parse '+03:00' or '-05:00' to timedelta.
    
    Args:
        offset_str: Timezone offset string like '+03:00' or '-05:00'
        
    Returns:
        timedelta representation of the offset
    """
    sign = 1 if offset_str[0] == '+' else -1
    hours, minutes = map(int, offset_str[1:].split(':'))
    return timedelta(hours=sign * hours, minutes=sign * minutes)


def get_user_current_time(timezone_offset: str) -> datetime:
    """Get current time in user's timezone.
    
    Args:
        timezone_offset: Timezone offset string like '+03:00'
        
    Returns:
        Current datetime in user's timezone
    """
    utc_now = datetime.now(timezone.utc)
    offset = parse_timezone_offset(timezone_offset)
    user_tz = timezone(offset)
    return utc_now.astimezone(user_tz)


def format_date_for_user(timezone_offset: str) -> str:
    """Get date string YYYY-MM-DD in user's timezone.
    
    Args:
        timezone_offset: Timezone offset string like '+03:00'
        
    Returns:
        Date string in format YYYY-MM-DD
    """
    user_time = get_user_current_time(timezone_offset)
    return user_time.strftime("%Y-%m-%d")


def is_time_to_send_notification(
    medication_time: str,  # "HH:MM"
    user_timezone: str,
    last_taken: Optional[int] = None,
    reminder_message_id: Optional[int] = None
) -> bool:
    """Check if notification should be sent now.
    
    Args:
        medication_time: Medication time in HH:MM format
        user_timezone: User's timezone offset like '+03:00'
        last_taken: Unix timestamp when last taken (None if never taken)
        reminder_message_id: ID of last reminder message (None if no active reminder)
        
    Returns:
        True if notification should be sent, False otherwise
    """
    # If already taken today, don't send
    if last_taken is not None:
        # Convert last_taken timestamp to user's timezone date
        user_time = get_user_current_time(user_timezone)
        last_taken_date = datetime.fromtimestamp(last_taken, tz=timezone.utc).astimezone(
            timezone(parse_timezone_offset(user_timezone))
        ).strftime("%Y-%m-%d")
        
        current_date = user_time.strftime("%Y-%m-%d")
        if last_taken_date == current_date:
            return False
    
    user_now = get_user_current_time(user_timezone)
    med_hour, med_minute = map(int, medication_time.split(':'))
    
    # Check if current time >= medication time
    current_minutes = user_now.hour * 60 + user_now.minute
    med_minutes = med_hour * 60 + med_minute
    
    return current_minutes >= med_minutes


def should_send_hourly_reminder(
    reminder_sent_at: int,  # Unix timestamp
    current_timestamp: Optional[int] = None,
    interval_hours: int = 1
) -> bool:
    """Check if hourly reminder should be sent.
    
    Args:
        reminder_sent_at: Unix timestamp when last reminder was sent
        current_timestamp: Current Unix timestamp (defaults to now)
        interval_hours: Hours between reminders (default 1)
        
    Returns:
        True if hourly reminder should be sent, False otherwise
    """
    if current_timestamp is None:
        current_timestamp = int(datetime.utcnow().timestamp())
    
    hours_passed = (current_timestamp - reminder_sent_at) / 3600
    return hours_passed >= interval_hours


def is_time_for_next_dose(
    current_med_time: str,  # "HH:MM"
    next_med_time: str,     # "HH:MM"
    user_timezone: str
) -> bool:
    """Check if it's time for the next dose (to auto-mark previous as taken).
    
    Args:
        current_med_time: Current medication time in HH:MM format
        next_med_time: Next medication time in HH:MM format
        user_timezone: User's timezone offset like '+03:00'
        
    Returns:
        True if it's time for next dose, False otherwise
    """
    user_now = get_user_current_time(user_timezone)
    current_hour, current_minute = map(int, current_med_time.split(':'))
    next_hour, next_minute = map(int, next_med_time.split(':'))
    
    # Check if current time >= next medication time
    current_minutes = user_now.hour * 60 + user_now.minute
    next_minutes = next_hour * 60 + next_minute
    
    return current_minutes >= next_minutes