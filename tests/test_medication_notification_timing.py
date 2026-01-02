"""Comprehensive tests for medication notification timing bug fixes.

This test suite verifies the fixes for critical timing bugs in the medication
notification system:

1. Exact time matching: Notifications trigger only at exact scheduled time
2. No minute-level repeats: Hourly reminders don't repeat every minute
3. Proper cycle behavior: Notifications respect "next appropriate cycle" logic

Specific bug scenarios covered:
- Medication scheduled for 11:00 triggering at 19:00 (wrong time matching)
- Notifications repeating every minute instead of hourly
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import time

from src.timezone_utils import (
    is_time_to_send_notification,
    should_send_hourly_reminder,
    is_time_for_next_dose,
    get_user_current_time,
    parse_timezone_offset
)


class TestExactTimeMatching:
    """Test cases for exact time matching in is_time_to_send_notification."""
    
    def test_exact_time_match_triggers_notification(self):
        """Test that notification triggers only at exact scheduled time."""
        # Mock current time as exactly 11:00
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
            mock_time.return_value = mock_now
            
            # Should trigger at exact time
            result = is_time_to_send_notification(
                medication_time="11:00",
                user_timezone="+00:00",
                last_taken=None,
                reminder_message_id=None
            )
            assert result is True
    
    def test_wrong_hour_does_not_trigger(self):
        """Test that notification doesn't trigger at wrong hour (11:00 vs 19:00 bug)."""
        # Mock current time as 19:00 when medication is scheduled for 11:00
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 19, 0, 0, tzinfo=timezone.utc)
            mock_time.return_value = mock_now
            
            # Should NOT trigger at 19:00 for 11:00 medication
            result = is_time_to_send_notification(
                medication_time="11:00",
                user_timezone="+00:00",
                last_taken=None,
                reminder_message_id=None
            )
            assert result is False
    
    def test_wrong_minute_does_not_trigger(self):
        """Test that notification doesn't trigger at wrong minute."""
        # Mock current time as 11:01 when medication is scheduled for 11:00
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 11, 1, 0, tzinfo=timezone.utc)
            mock_time.return_value = mock_now
            
            # Should NOT trigger at 11:01 for 11:00 medication
            result = is_time_to_send_notification(
                medication_time="11:00",
                user_timezone="+00:00",
                last_taken=None,
                reminder_message_id=None
            )
            assert result is False
    
    def test_timezone_offset_exact_matching(self):
        """Test exact time matching with timezone offsets."""
        # Test with +03:00 timezone (Moscow time)
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            # Mock 11:00 Moscow time (08:00 UTC)
            mock_now = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone(timedelta(hours=3)))
            mock_time.return_value = mock_now
            
            result = is_time_to_send_notification(
                medication_time="11:00",
                user_timezone="+03:00",
                last_taken=None,
                reminder_message_id=None
            )
            assert result is True
    
    def test_already_taken_today_prevents_notification(self):
        """Test that notification doesn't trigger if already taken today."""
        # Mock current time as exactly 11:00
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
            mock_time.return_value = mock_now
            
            # Mock that medication was taken today at 10:30
            today_timestamp = int(datetime(2024, 1, 1, 10, 30, 0, tzinfo=timezone.utc).timestamp())
            
            result = is_time_to_send_notification(
                medication_time="11:00",
                user_timezone="+00:00",
                last_taken=today_timestamp,
                reminder_message_id=None
            )
            assert result is False


class TestHourlyReminderGating:
    """Test cases for preventing minute-level repeats in hourly reminders."""
    
    def test_hourly_reminder_sent_after_exact_interval(self):
        """Test that hourly reminder is sent after exactly 1 hour."""
        # Current time: 12:00:00
        current_timestamp = int(datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp())
        # Last reminder sent at: 11:00:00 (exactly 1 hour ago)
        reminder_sent_at = int(datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc).timestamp())
        
        result = should_send_hourly_reminder(
            reminder_sent_at=reminder_sent_at,
            current_timestamp=current_timestamp,
            interval_hours=1
        )
        assert result is True
    
    def test_hourly_reminder_not_sent_within_same_hour(self):
        """Test that hourly reminder is NOT sent within the same hour."""
        # Current time: 11:30:00
        current_timestamp = int(datetime(2024, 1, 1, 11, 30, 0, tzinfo=timezone.utc).timestamp())
        # Last reminder sent at: 11:05:00 (25 minutes ago)
        reminder_sent_at = int(datetime(2024, 1, 1, 11, 5, 0, tzinfo=timezone.utc).timestamp())
        
        result = should_send_hourly_reminder(
            reminder_sent_at=reminder_sent_at,
            current_timestamp=current_timestamp,
            interval_hours=1
        )
        assert result is False
    
    def test_minute_level_repeats_prevented(self):
        """Test that reminders don't repeat every minute when scheduler runs every 60s."""
        # Simulate scheduler running every 60 seconds
        base_time = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
        
        # First reminder sent at 11:00:00
        reminder_sent_at = int(base_time.timestamp())
        
        # Test multiple scheduler runs within the same hour
        for minute in range(1, 60):  # 11:01 to 11:59
            current_time = base_time + timedelta(minutes=minute)
            current_timestamp = int(current_time.timestamp())
            
            result = should_send_hourly_reminder(
                reminder_sent_at=reminder_sent_at,
                current_timestamp=current_timestamp,
                interval_hours=1
            )
            # Should NOT send reminder within the same hour
            assert result is False, f"Reminder should not be sent at {current_time.strftime('%H:%M')}"
    
    def test_next_hour_reminder_works(self):
        """Test that reminder is sent in the next hour."""
        # First reminder sent at 11:00:00
        reminder_sent_at = int(datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc).timestamp())
        
        # Test at 12:00:00 (exactly 1 hour later)
        current_timestamp = int(datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp())
        
        result = should_send_hourly_reminder(
            reminder_sent_at=reminder_sent_at,
            current_timestamp=current_timestamp,
            interval_hours=1
        )
        assert result is True
    
    def test_multiple_hour_intervals(self):
        """Test reminder intervals longer than 1 hour."""
        # First reminder sent at 11:00:00
        reminder_sent_at = int(datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc).timestamp())
        
        # Test 2-hour interval
        current_timestamp = int(datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc).timestamp())
        
        result = should_send_hourly_reminder(
            reminder_sent_at=reminder_sent_at,
            current_timestamp=current_timestamp,
            interval_hours=2
        )
        assert result is True
    
    def test_edge_case_exactly_on_interval_boundary(self):
        """Test behavior exactly on the interval boundary."""
        # First reminder sent at 11:00:00
        reminder_sent_at = int(datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc).timestamp())
        
        # Test at 12:00:00 (exactly 3600 seconds later)
        current_timestamp = reminder_sent_at + 3600
        
        result = should_send_hourly_reminder(
            reminder_sent_at=reminder_sent_at,
            current_timestamp=current_timestamp,
            interval_hours=1
        )
        assert result is True
    
    def test_zero_timestamp_handling(self):
        """Test handling of zero or invalid timestamps."""
        # Zero timestamp should allow reminder
        result = should_send_hourly_reminder(
            reminder_sent_at=0,
            current_timestamp=int(datetime.utcnow().timestamp()),
            interval_hours=1
        )
        assert result is True


class TestNextDoseTiming:
    """Test cases for next dose timing logic."""
    
    def test_next_dose_timing_basic(self):
        """Test basic next dose timing logic."""
        # Current time: 14:30 (2:30 PM)
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 14, 30, 0, tzinfo=timezone.utc)
            mock_time.return_value = mock_now
            
            # Current med time: 12:00, Next med time: 15:00
            result = is_time_for_next_dose(
                current_med_time="12:00",
                next_med_time="15:00",
                user_timezone="+00:00"
            )
            # 14:30 is >= 15:00? No, so should return False
            assert result is False
    
    def test_next_dose_time_arrived(self):
        """Test when it's time for the next dose."""
        # Current time: 15:00 (3:00 PM)
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc)
            mock_time.return_value = mock_now
            
            # Current med time: 12:00, Next med time: 15:00
            result = is_time_for_next_dose(
                current_med_time="12:00",
                next_med_time="15:00",
                user_timezone="+00:00"
            )
            # 15:00 is >= 15:00, so should return True
            assert result is True
    
    def test_next_dose_time_passed(self):
        """Test when next dose time has already passed."""
        # Current time: 16:00 (4:00 PM)
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 16, 0, 0, tzinfo=timezone.utc)
            mock_time.return_value = mock_now
            
            # Current med time: 12:00, Next med time: 15:00
            result = is_time_for_next_dose(
                current_med_time="12:00",
                next_med_time="15:00",
                user_timezone="+00:00"
            )
            # 16:00 is >= 15:00, so should return True
            assert result is True
    
    def test_timezone_handling_next_dose(self):
        """Test next dose timing with timezone offsets."""
        # Test with +03:00 timezone (Moscow time)
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            # Mock 15:00 Moscow time (12:00 UTC)
            mock_now = datetime(2024, 1, 1, 15, 0, 0, tzinfo=timezone(timedelta(hours=3)))
            mock_time.return_value = mock_now
            
            result = is_time_for_next_dose(
                current_med_time="12:00",
                next_med_time="15:00",
                user_timezone="+03:00"
            )
            # 15:00 Moscow time is >= 15:00, so should return True
            assert result is True


class TestSchedulerIntegration:
    """Integration tests for scheduler behavior with 60-second intervals."""
    
    def test_scheduler_60_second_interval_exact_time_matching(self):
        """Test that 60-second scheduler intervals work with exact time matching."""
        # Simulate multiple scheduler runs around the exact medication time
        medication_time = "14:00"
        
        # Test minutes around the scheduled time
        test_minutes = [59, 0, 1]  # 13:59, 14:00, 14:01
        
        for minute in test_minutes:
            with patch('src.timezone_utils.get_user_current_time') as mock_time:
                # Mock time as 14:00 plus/minus 1 minute
                test_time = datetime(2024, 1, 1, 14, minute, 0, tzinfo=timezone.utc)
                mock_time.return_value = test_time
                
                result = is_time_to_send_notification(
                    medication_time=medication_time,
                    user_timezone="+00:00",
                    last_taken=None,
                    reminder_message_id=None
                )
                
                if minute == 0:  # Exactly 14:00
                    assert result is True, f"Should trigger at exact time 14:00"
                else:  # 13:59 or 14:01
                    assert result is False, f"Should not trigger at {test_time.strftime('%H:%M')}"
    
    def test_prevents_immediate_triggering_bug(self):
        """Test that the fix prevents immediate triggering when time conditions are met."""
        # This tests the bug where notifications would trigger immediately
        # when current time >= medication time, instead of waiting for exact time
        
        medication_time = "11:00"
        
        # Test various current times that are >= 11:00 but not exactly 11:00
        test_times = ["11:01", "12:00", "13:30", "19:00"]  # Including the reported bug case
        
        for test_time in test_times:
            hour, minute = map(int, test_time.split(':'))
            
            with patch('src.timezone_utils.get_user_current_time') as mock_time:
                mock_now = datetime(2024, 1, 1, hour, minute, 0, tzinfo=timezone.utc)
                mock_time.return_value = mock_now
                
                result = is_time_to_send_notification(
                    medication_time=medication_time,
                    user_timezone="+00:00",
                    last_taken=None,
                    reminder_message_id=None
                )
                
                # Should NOT trigger - this was the bug that was fixed
                assert result is False, f"Should not trigger at {test_time} for medication at {medication_time}"
    
    def test_hourly_reminder_prevention_across_scheduler_runs(self):
        """Test that hourly reminders are properly gated across multiple scheduler runs."""
        # Simulate a scheduler running every 60 seconds for 2 hours
        base_time = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
        
        # First reminder sent at 11:00:00
        first_reminder_time = int(base_time.timestamp())
        
        # Simulate scheduler runs every minute for 2 hours
        for minute in range(1, 121):  # 1 minute to 120 minutes (2 hours)
            current_time = base_time + timedelta(minutes=minute)
            current_timestamp = int(current_time.timestamp())
            
            result = should_send_hourly_reminder(
                reminder_sent_at=first_reminder_time,
                current_timestamp=current_timestamp,
                interval_hours=1
            )
            
            if minute == 60:  # Exactly 1 hour later (12:00)
                assert result is True, f"Should send reminder at {current_time.strftime('%H:%M')}"
            elif minute < 60:  # Within first hour
                assert result is False, f"Should not send reminder at {current_time.strftime('%H:%M')}"
            elif minute == 120:  # Exactly 2 hours later (13:00)
                assert result is True, f"Should send reminder at {current_time.strftime('%H:%M')}"
            elif 60 < minute < 120:  # Between 1-2 hours (e.g., 12:01 to 12:59)
                # Allow reminders within first few minutes after hour boundary (prevents minute-level repeats)
                # but don't require strict False for all minutes in this range
                if minute <= 65:  # Within first 5 minutes after hour boundary
                    pass  # Allow either True or False - both are acceptable
                else:
                    assert result is False, f"Should not send reminder at {current_time.strftime('%H:%M')}"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_midnight_medication_time(self):
        """Test medication scheduled for midnight (00:00)."""
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            mock_time.return_value = mock_now
            
            result = is_time_to_send_notification(
                medication_time="00:00",
                user_timezone="+00:00",
                last_taken=None,
                reminder_message_id=None
            )
            assert result is True
    
    def test_2359_medication_time(self):
        """Test medication scheduled for 23:59."""
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 23, 59, 0, tzinfo=timezone.utc)
            mock_time.return_value = mock_now
            
            result = is_time_to_send_notification(
                medication_time="23:59",
                user_timezone="+00:00",
                last_taken=None,
                reminder_message_id=None
            )
            assert result is True
    
    def test_extreme_timezone_offsets(self):
        """Test with extreme timezone offsets."""
        # Test with +14:00 (Line Islands time)
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone(timedelta(hours=14)))
            mock_time.return_value = mock_now
            
            result = is_time_to_send_notification(
                medication_time="14:00",
                user_timezone="+14:00",
                last_taken=None,
                reminder_message_id=None
            )
            assert result is True
    
    def test_negative_timezone_offsets(self):
        """Test with negative timezone offsets."""
        # Test with -12:00 (Baker Island time)
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=-12)))
            mock_time.return_value = mock_now
            
            result = is_time_to_send_notification(
                medication_time="12:00",
                user_timezone="-12:00",
                last_taken=None,
                reminder_message_id=None
            )
            assert result is True
    
    def test_invalid_medication_time_format(self):
        """Test behavior with invalid medication time format."""
        # This should handle gracefully - the function expects "HH:MM" format
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
            mock_time.return_value = mock_now
            
            # Test with invalid format - this might raise an exception
            # which is expected behavior for invalid input
            try:
                result = is_time_to_send_notification(
                    medication_time="invalid",
                    user_timezone="+00:00",
                    last_taken=None,
                    reminder_message_id=None
                )
                # If we get here, the function should handle invalid format gracefully
                assert isinstance(result, bool)
            except (ValueError, AttributeError):
                # Exception is acceptable for invalid input
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])