"""Comprehensive tests for medication notification timing.

This test suite verifies the notification timing logic:

1. Time-reached matching: Notifications trigger when scheduled time has arrived (>=)
2. No minute-level repeats: Hourly reminders don't repeat every minute
3. Proper cycle behavior: Notifications respect "next appropriate cycle" logic
4. Deduplication: Once sent, a notification is not re-sent (handled by caller via DB)
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock, call
import asyncio
import time

from src.timezone_utils import (
    is_time_to_send_notification,
    should_send_hourly_reminder,
    is_time_for_next_dose,
    get_user_current_time,
    parse_timezone_offset
)


class TestTimeReachedMatching:
    """Test cases for time-reached matching in is_time_to_send_notification."""

    def test_exact_time_match_triggers_notification(self):
        """Test that notification triggers at exact scheduled time."""
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
            mock_time.return_value = mock_now

            result = is_time_to_send_notification(
                medication_time="11:00",
                user_timezone="+00:00",
                last_taken=None,
                reminder_message_id=None
            )
            assert result is True

    def test_after_scheduled_time_triggers(self):
        """Test that notification triggers after scheduled time (>= semantics).

        Deduplication is the caller's job via reminder_message_id in the DB.
        The function only answers 'has the scheduled time arrived?'
        """
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 19, 0, 0, tzinfo=timezone.utc)
            mock_time.return_value = mock_now

            result = is_time_to_send_notification(
                medication_time="11:00",
                user_timezone="+00:00",
                last_taken=None,
                reminder_message_id=None
            )
            assert result is True

    def test_one_minute_after_triggers(self):
        """Test that 1 minute after scheduled time still triggers."""
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 11, 1, 0, tzinfo=timezone.utc)
            mock_time.return_value = mock_now

            result = is_time_to_send_notification(
                medication_time="11:00",
                user_timezone="+00:00",
                last_taken=None,
                reminder_message_id=None
            )
            assert result is True

    def test_before_scheduled_time_does_not_trigger(self):
        """Test that notification does NOT trigger before scheduled time."""
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 10, 59, 0, tzinfo=timezone.utc)
            mock_time.return_value = mock_now

            result = is_time_to_send_notification(
                medication_time="11:00",
                user_timezone="+00:00",
                last_taken=None,
                reminder_message_id=None
            )
            assert result is False

    def test_timezone_offset_matching(self):
        """Test time matching with timezone offsets."""
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
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
        with patch('src.timezone_utils.get_user_current_time') as mock_time:
            mock_now = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
            mock_time.return_value = mock_now

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

    def test_scheduler_before_and_after_scheduled_time(self):
        """Test that notification triggers at and after scheduled time, not before."""
        medication_time = "14:00"

        test_cases = [
            (13, 59, False),  # 13:59 — before scheduled time
            (14,  0, True),   # 14:00 — at scheduled time
            (14,  1, True),   # 14:01 — after (scheduler drift safe)
            (14, 30, True),   # 14:30 — well after
        ]

        for hour, minute, expected in test_cases:
            with patch('src.timezone_utils.get_user_current_time') as mock_time:
                test_time = datetime(2024, 1, 1, hour, minute, 0, tzinfo=timezone.utc)
                mock_time.return_value = test_time

                result = is_time_to_send_notification(
                    medication_time=medication_time,
                    user_timezone="+00:00",
                    last_taken=None,
                    reminder_message_id=None
                )

                assert result is expected, (
                    f"At {hour:02d}:{minute:02d} for med at {medication_time}: "
                    f"expected {expected}, got {result}"
                )

    def test_late_check_still_triggers(self):
        """Test that a notification is returned as due even hours later.

        The caller (scheduler) uses the DB reminder_message_id to prevent
        duplicate sends, so the function only answers 'has time arrived?'
        """
        medication_time = "11:00"
        test_times = ["11:01", "12:00", "13:30", "19:00"]

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

                assert result is True, (
                    f"Should trigger at {test_time} for medication at {medication_time} "
                    f"(deduplication is the caller's job)"
                )

    def test_hourly_reminder_with_send_reset_cycle(self):
        """Test hourly reminders with the realistic send-and-reset cycle.

        After each send the caller updates reminder_sent_at, resetting the
        timer.  This test simulates that cycle.
        """
        base_time = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
        reminder_sent_at = int(base_time.timestamp())

        # Minutes 1-59: not yet 1 hour → False
        for minute in range(1, 60):
            ts = int((base_time + timedelta(minutes=minute)).timestamp())
            assert should_send_hourly_reminder(reminder_sent_at, ts, 1) is False

        # Minute 60: exactly 1 hour → True (send, then reset)
        ts_60 = int((base_time + timedelta(minutes=60)).timestamp())
        assert should_send_hourly_reminder(reminder_sent_at, ts_60, 1) is True

        # Simulate reset: caller updates reminder_sent_at to now
        reminder_sent_at = ts_60

        # Minutes 61-119: not yet 1 hour from new base → False
        for minute in range(61, 120):
            ts = int((base_time + timedelta(minutes=minute)).timestamp())
            assert should_send_hourly_reminder(reminder_sent_at, ts, 1) is False

        # Minute 120: exactly 1 hour from reset → True
        ts_120 = int((base_time + timedelta(minutes=120)).timestamp())
        assert should_send_hourly_reminder(reminder_sent_at, ts_120, 1) is True


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


class TestOldNotificationDeletion:
    """Test cases for old notification deletion when sending new ones."""

    def test_old_notification_deleted_when_sending_new_notification(self):
        """Test that old notifications are deleted when new ones are sent."""
        mock_db = MagicMock()
        mock_bot = MagicMock()
        mock_bot.bot = MagicMock()

        from src.scheduler import NotificationScheduler
        scheduler = NotificationScheduler(mock_db, mock_bot)

        mock_status = {
            "reminder_message_id": 12345,
            "medication_id": 1,
            "name": "aspirin",
            "dosage": "100mg"
        }

        mock_db.get_intake_status = AsyncMock(return_value=mock_status)
        mock_bot.bot.delete_message = AsyncMock(return_value=True)
        mock_bot.send_notification = AsyncMock(return_value=67890)
        mock_db.set_reminder_message_id = AsyncMock(return_value=True)

        medication = {"id": 1, "name": "aspirin", "dosage": "100mg", "time": "11:00"}
        asyncio.run(scheduler._send_notification(123, medication, "2024-01-01"))

        mock_bot.bot.delete_message.assert_called_with(123, 12345)
        mock_bot.send_notification.assert_called_once_with(123, medication, "2024-01-01")
        mock_db.set_reminder_message_id.assert_called_once_with(123, 1, "2024-01-01", 67890)

    def test_no_old_notification_no_deletion_needed(self):
        """Test that no deletion occurs when there's no old notification."""
        mock_db = MagicMock()
        mock_bot = MagicMock()
        mock_bot.bot = MagicMock()

        from src.scheduler import NotificationScheduler
        scheduler = NotificationScheduler(mock_db, mock_bot)

        mock_db.get_intake_status = AsyncMock(return_value=None)
        mock_bot.send_notification = AsyncMock(return_value=67890)
        mock_db.create_intake_status = AsyncMock(return_value=1)

        medication = {"id": 1, "name": "aspirin", "dosage": "100mg", "time": "11:00"}
        asyncio.run(scheduler._send_notification(123, medication, "2024-01-01"))

        mock_bot.bot.delete_message.assert_not_called()
        mock_bot.send_notification.assert_called_once_with(123, medication, "2024-01-01")
        mock_db.create_intake_status.assert_called_once_with(123, 1, "2024-01-01", 67890)

    def test_old_notification_deletion_failure_handled_gracefully(self):
        """Test that deletion failure doesn't prevent new notification."""
        mock_db = MagicMock()
        mock_bot = MagicMock()
        mock_bot.bot = MagicMock()

        from src.scheduler import NotificationScheduler
        scheduler = NotificationScheduler(mock_db, mock_bot)

        mock_status = {
            "reminder_message_id": 12345,
            "medication_id": 1,
            "name": "aspirin",
            "dosage": "100mg"
        }
        mock_db.get_intake_status = AsyncMock(return_value=mock_status)
        mock_bot.bot.delete_message = AsyncMock(side_effect=Exception("Message not found"))
        mock_bot.send_notification = AsyncMock(return_value=67890)
        mock_db.set_reminder_message_id = AsyncMock(return_value=True)

        medication = {"id": 1, "name": "aspirin", "dosage": "100mg", "time": "11:00"}
        asyncio.run(scheduler._send_notification(123, medication, "2024-01-01"))

        mock_bot.bot.delete_message.assert_called_once_with(123, 12345)
        mock_bot.send_notification.assert_called_once_with(123, medication, "2024-01-01")
        mock_db.set_reminder_message_id.assert_called_once_with(123, 1, "2024-01-01", 67890)

    def test_multiple_medications_each_gets_separate_notification_handling(self):
        """Test that each medication gets its own notification handling."""
        mock_db = MagicMock()
        mock_bot = MagicMock()
        mock_bot.bot = MagicMock()

        from src.scheduler import NotificationScheduler
        scheduler = NotificationScheduler(mock_db, mock_bot)

        medications = [
            {"id": 1, "name": "aspirin", "dosage": "100mg", "time": "08:00"},
            {"id": 2, "name": "vitamin", "dosage": "500mg", "time": "12:00"},
            {"id": 3, "name": "ibuprofen", "dosage": "200mg", "time": "18:00"}
        ]

        def mock_get_intake_status(user_id, medication_id, date):
            if medication_id == 1:
                return {"reminder_message_id": 11111}
            elif medication_id == 2:
                return {"reminder_message_id": 22222}
            else:
                return None

        mock_db.get_intake_status = AsyncMock(side_effect=mock_get_intake_status)
        mock_bot.bot.delete_message = AsyncMock(return_value=True)
        mock_bot.send_notification = AsyncMock(side_effect=[11112, 22223, 33333])
        mock_db.set_reminder_message_id = AsyncMock(return_value=True)
        mock_db.create_intake_status = AsyncMock(return_value=1)

        async def run_all():
            for med in medications:
                await scheduler._send_notification(123, med, "2024-01-01")

        asyncio.run(run_all())

        expected_deletions = [call(123, 11111), call(123, 22222)]
        assert mock_bot.bot.delete_message.call_args_list == expected_deletions
        assert mock_bot.send_notification.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])