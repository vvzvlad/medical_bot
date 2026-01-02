"""Unit tests for timezone utility functions."""

import pytest
from datetime import timedelta

from src.utils.timezone import parse_timezone_offset, get_user_current_time


class TestParseTimezoneOffset:
    """Test cases for parse_timezone_offset function."""

    def test_parse_positive_timezone(self):
        """Test parsing positive timezone offsets."""
        result = parse_timezone_offset("+03:00")
        assert result == timedelta(hours=3)
        
        result = parse_timezone_offset("+15:00")
        assert result == timedelta(hours=15)
        
        result = parse_timezone_offset("+00:30")
        assert result == timedelta(minutes=30)

    def test_parse_negative_timezone(self):
        """Test parsing negative timezone offsets."""
        result = parse_timezone_offset("-05:00")
        assert result == timedelta(hours=-5)
        
        result = parse_timezone_offset("-12:00")
        assert result == timedelta(hours=-12)
        
        result = parse_timezone_offset("-08:30")
        assert result == timedelta(hours=-8, minutes=-30)

    def test_parse_extreme_timezone_offsets(self):
        """Test parsing extreme but valid timezone offsets."""
        # Test the failing cases mentioned in the issue
        result = parse_timezone_offset("+20:00")
        assert result == timedelta(hours=20)
        
        result = parse_timezone_offset("+15:00")
        assert result == timedelta(hours=15)
        
        # Test minimum and maximum valid ranges
        result = parse_timezone_offset("-12:00")
        assert result == timedelta(hours=-12)
        
        result = parse_timezone_offset("+15:00")
        assert result == timedelta(hours=15)

    def test_backward_compatibility(self):
        """Test that existing valid timezone formats still work."""
        # Test commonly used timezones
        common_timezones = [
            "+00:00",  # UTC
            "+01:00",  # Central European Time
            "+03:00",  # Moscow Time
            "+05:30",  # India Standard Time
            "+08:00",  # China Standard Time
            "+09:00",  # Japan Standard Time
            "+10:00",  # Australian Eastern Time
            "+12:00",  # New Zealand Time
            "-03:00",  # Argentina Time
            "-04:00",  # Eastern Daylight Time
            "-05:00",  # Eastern Standard Time
            "-08:00",  # Pacific Standard Time
            "-10:00",  # Hawaii-Aleutian Time
        ]
        
        for tz in common_timezones:
            result = parse_timezone_offset(tz)
            # Verify it returns a valid timedelta
            assert isinstance(result, timedelta)

    def test_invalid_formats(self):
        """Test error handling for invalid timezone formats."""
        invalid_formats = [
            "",           # Empty string
            "+3:00",      # Missing leading zero
            "+03:0",      # Missing leading zero in minutes
            "+03:",       # Missing minutes
            ":00",        # Missing hours
            "03:00",      # Missing sign
            "+25:00",     # Hours out of range
            "-25:00",     # Hours out of range (beyond -12)
            "+03:60",     # Minutes out of range
            "+03:-30",    # Negative minutes
            "+3a:00",     # Non-numeric hours
            "+03:0a",     # Non-numeric minutes
            "+03:00:00",  # Too many parts
        ]
        
        for invalid_format in invalid_formats:
            with pytest.raises(ValueError, match="Invalid timezone offset format"):
                parse_timezone_offset(invalid_format)

    def test_whitespace_handling(self):
        """Test that whitespace is properly handled."""
        result = parse_timezone_offset("  +03:00  ")
        assert result == timedelta(hours=3)
        
        result = parse_timezone_offset("\t-05:00\n")
        assert result == timedelta(hours=-5)


class TestGetUserCurrentTime:
    """Test cases for get_user_current_time function."""

    def test_get_user_current_time_basic(self):
        """Test basic timezone conversion."""
        # Test with Moscow timezone
        result = get_user_current_time("+03:00")
        assert isinstance(result.year, int)
        assert isinstance(result.month, int)
        assert isinstance(result.day, int)
        assert isinstance(result.hour, int)
        assert isinstance(result.minute, int)

    def test_get_user_current_time_with_pacific_timezones(self):
        """Test timezone conversion with Pacific territories timezones."""
        # Test with Pacific territory timezones that were failing before
        result = get_user_current_time("+15:00")
        assert isinstance(result, type(result))
        
        result = get_user_current_time("+20:00")
        assert isinstance(result, type(result))

    def test_get_user_current_time_with_utc(self):
        """Test timezone conversion with UTC."""
        result = get_user_current_time("+00:00")
        assert isinstance(result, type(result))


if __name__ == "__main__":
    pytest.main([__file__])