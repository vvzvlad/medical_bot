#!/usr/bin/env python3

"""
Test for the "'str' object has no attribute 'time'" bug fix.

This test validates that the defensive programming added to handle
different time formats prevents the AttributeError when processing
medication times.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.telegram_bot import MedicationBot
from src.llm_processor import LLMProcessor
from src.database import Database


class TestTimeAttributeBugFix:
    """Test cases for the time attribute bug fix."""
    
    @pytest.mark.asyncio
    async def test_str_time_attribute_error_prevention(self):
        """Test that the "'str' object has no attribute 'time'" error is prevented."""
        
        # Create mock objects
        mock_llm = AsyncMock(spec=LLMProcessor)
        mock_db = AsyncMock(spec=Database)
        
        # Set up the LLM classification to return "add"
        mock_llm.classify_intent.return_value = "add"
        
        # Set up the LLM to return the problematic data structure from the original log
        # The log showed: [{'medication_name': 'ламотриджин', 'times': ['11:00']}]
        mock_llm.process_add.return_value = [
            {'medication_name': 'ламотриджин', 'times': ['11:00']}
        ]
        
        # Set up database responses
        mock_db.get_user.return_value = None  # User doesn't exist
        mock_db.create_user.return_value = None
        mock_db.check_duplicate.return_value = False  # No duplicate
        mock_db.add_medication.return_value = 123  # Success
        
        # Create bot instance
        bot = MedicationBot(mock_llm, mock_db)
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.from_user.id = 85106994
        mock_message.from_user.username = "vvzvlad"
        mock_message.from_user.first_name = "Vlad"
        mock_message.from_user.last_name = ""
        mock_message.text = "ламотриджин в 11"
        mock_message.chat.id = 12345
        
        # Mock the bot's methods
        bot.send_thinking_message = AsyncMock(return_value=67890)
        bot.delete_thinking_message = AsyncMock()
        bot.bot = MagicMock()
        bot.bot.send_message = AsyncMock()
        bot.bot.delete_message = AsyncMock()
        
        # This should work without the 'str' object has no attribute 'time' error
        # The defensive programming in the _handle_add method should handle this correctly
        await bot.handle_message(mock_message)
        
        # Verify that the medication was processed correctly
        mock_llm.process_add.assert_called_once_with("ламотриджин в 11", 85106994)
        mock_db.check_duplicate.assert_called_once_with(85106994, 'ламотриджин', '11:00')
        mock_db.add_medication.assert_called_once_with(85106994, 'ламотриджин', '11:00', None)
        
        # Verify response was sent
        bot.bot.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multiple_time_formats_handling(self):
        """Test that various time formats are handled correctly by the defensive programming."""
        
        # Create mock objects
        mock_llm = AsyncMock(spec=LLMProcessor)
        mock_db = AsyncMock(spec=Database)
        
        # Test different LLM response formats that could potentially cause issues
        test_cases = [
            # Normal case (what we expect from LLM)
            [{'medication_name': 'аспирин', 'times': ['08:00', '20:00']}],
            
            # Single medication with single time
            [{'medication_name': 'парацетамол', 'times': ['12:00']}],
            
            # With dosage information
            [{'medication_name': 'ибупрофен', 'times': ['14:00'], 'dosage': '200 мг'}],
            
            # Single object instead of list (edge case)
            {'medication_name': 'витамин', 'times': ['09:00']},
            
            # Empty times (edge case)
            [{'medication_name': 'пробиотик', 'times': []}],
        ]
        
        for i, llm_response in enumerate(test_cases):
            print(f"Testing case {i+1}: {llm_response}")
            
            # Reset mocks
            mock_llm.reset_mock()
            mock_db.reset_mock()
            
            # Set up the LLM classification and response
            mock_llm.classify_intent.return_value = "add"
            mock_llm.process_add.return_value = llm_response
            
            # Set up database responses
            mock_db.get_user.return_value = None
            mock_db.create_user.return_value = None
            mock_db.check_duplicate.return_value = False
            mock_db.add_medication.return_value = 100 + i  # Different ID for each case
            
            # Create bot instance
            bot = MedicationBot(mock_llm, mock_db)
            
            # Create mock message
            mock_message = MagicMock()
            mock_message.from_user.id = 12345 + i
            mock_message.from_user.username = "test_user"
            mock_message.from_user.first_name = "Test"
            mock_message.from_user.last_name = ""
            mock_message.text = "test medication"
            mock_message.chat.id = 1000 + i
            
            # Mock the bot's methods
            bot.send_thinking_message = AsyncMock(return_value=500 + i)
            bot.delete_thinking_message = AsyncMock()
            bot.bot = MagicMock()
            bot.bot.send_message = AsyncMock()
            bot.bot.delete_message = AsyncMock()
            
            # This should work without any AttributeError
            await bot.handle_message(mock_message)
            
            # Verify that processing completed successfully
            mock_llm.process_add.assert_called_once()
            bot.bot.send_message.assert_called_once()
            
            print(f"✅ Case {i+1} passed!")
    
    @pytest.mark.asyncio
    async def test_original_bug_scenario(self):
        """Test the exact scenario from the original error log."""
        
        # Recreate the exact scenario from the log:
        # 2026-01-02 20:38:19.147 | INFO | src.enhanced_logger:log_info:150 | ℹ️ INFO INTENT_CLASSIFIED | User: vvzvlad (ID: 85106994) | Classified as: add
        # 2026-01-02 20:38:20.092 | INFO | src.enhanced_logger:log_llm_parsing:91 | 🔍 LLM PARSING ADD | User: vvzvlad (ID: 85106994) | Processing time: 943.89ms | Message: 'ламотриджин в 11' → Parsed: [{'medication_name': 'ламотриджин', 'times': ['11:00']}]
        
        mock_llm = AsyncMock(spec=LLMProcessor)
        mock_db = AsyncMock(spec=Database)
        
        # Set up the LLM classification and response
        mock_llm.classify_intent.return_value = "add"
        
        # Exact response from the log
        mock_llm.process_add.return_value = [
            {'medication_name': 'ламотриджин', 'times': ['11:00']}
        ]
        
        # Set up database responses
        mock_db.get_user.return_value = None
        mock_db.create_user.return_value = None
        mock_db.check_duplicate.return_value = False
        mock_db.add_medication.return_value = 123
        
        # Create bot instance
        bot = MedicationBot(mock_llm, mock_db)
        
        # Create mock message matching the original log
        mock_message = MagicMock()
        mock_message.from_user.id = 85106994
        mock_message.from_user.username = "vvzvlad"
        mock_message.from_user.first_name = "vvzvlad"
        mock_message.from_user.last_name = ""
        mock_message.text = "ламотриджин в 11"
        mock_message.chat.id = 12345
        
        # Mock the bot's methods
        bot.send_thinking_message = AsyncMock(return_value=67890)
        bot.delete_thinking_message = AsyncMock()
        bot.bot = MagicMock()
        bot.bot.send_message = AsyncMock()
        bot.bot.delete_message = AsyncMock()
        
        # This should complete successfully without the AttributeError
        # that originally caused: 'str' object has no attribute 'time'
        await bot.handle_message(mock_message)
        
        # Verify the exact processing from the log
        mock_llm.process_add.assert_called_once_with("ламотриджин в 11", 85106994)
        
        # The defensive programming should handle the string time correctly
        mock_db.check_duplicate.assert_called_once_with(85106994, 'ламотриджин', '11:00')
        mock_db.add_medication.assert_called_once_with(85106994, 'ламотриджин', '11:00', None)
        
        print("✅ Original bug scenario test passed!")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])