"""Shared fixtures for tests."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.data.storage import DataManager
from src.services.notification_manager import NotificationManager
from src.services.schedule_manager import ScheduleManager
from src.llm.client import GroqClient


@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data.
    
    Yields:
        Path: Path to temporary directory
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def data_manager(temp_data_dir):
    """Create DataManager with temp directory.
    
    Args:
        temp_data_dir: Temporary directory fixture
        
    Returns:
        DataManager: DataManager instance for testing
    """
    return DataManager(data_dir=str(temp_data_dir))


@pytest.fixture
def schedule_manager(data_manager):
    """Create ScheduleManager.
    
    Args:
        data_manager: DataManager fixture
        
    Returns:
        ScheduleManager: ScheduleManager instance for testing
    """
    return ScheduleManager(data_manager)


@pytest.fixture
def notification_manager(data_manager):
    """Create NotificationManager.
    
    Args:
        data_manager: DataManager fixture
        
    Returns:
        NotificationManager: NotificationManager instance for testing
    """
    return NotificationManager(data_manager)


@pytest.fixture
def mock_groq_client():
    """Create mock GroqClient.
    
    Returns:
        MagicMock: Mocked GroqClient with common methods
    """
    client = MagicMock(spec=GroqClient)
    
    # Mock detect_command_type
    async def mock_detect(message):
        message_lower = message.lower()
        # Check more specific patterns first (longer phrases before shorter ones)
        if "что я принимаю" in message_lower or "список" in message_lower or "покажи" in message_lower:
            return "list"
        elif "добавь" in message_lower or ("принимаю" in message_lower and "в" in message_lower):
            return "add"
        elif "удали" in message_lower:
            return "delete"
        elif "теперь в" in message_lower and any(c.isdigit() for c in message):
            return "time_change"
        elif "теперь" in message_lower and "мг" in message_lower:
            return "dose_change"
        elif "часовая зона" in message_lower or "timezone" in message_lower:
            return "timezone_change"
        elif "принял" in message_lower or "выпил" in message_lower:
            return "done"
        else:
            return "unknown"
    
    client.detect_command_type = AsyncMock(side_effect=mock_detect)
    
    # Mock process_add_command
    async def mock_process_add(message):
        # Simple mock that returns basic structure
        return [{
            "medication_name": "аспирин",
            "times": ["10:00"],
            "dosage": "200 мг"
        }]
    
    client.process_add_command = AsyncMock(side_effect=mock_process_add)
    
    # Mock process_delete_command
    async def mock_process_delete(message, schedule):
        if not schedule:
            return {"status": "error", "message": "No medications"}
        # If message contains specific medication name, return success
        for med in schedule:
            if med["name"].lower() in message.lower():
                return {"status": "success", "medication_ids": [med["id"]]}
        # Otherwise need clarification
        return {
            "status": "clarification_needed",
            "message": f"Какое лекарство удалить? {', '.join(m['name'] for m in schedule)}"
        }
    
    client.process_delete_command = AsyncMock(side_effect=mock_process_delete)
    
    # Mock process_time_change_command
    async def mock_process_time_change(message, schedule):
        if not schedule:
            return {"status": "error", "message": "No medications"}
        # Extract time from message (simple regex)
        import re
        time_match = re.search(r'(\d{1,2}):(\d{2})', message)
        if time_match:
            new_time = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
            # Find medication in message
            for med in schedule:
                if med["name"].lower() in message.lower():
                    return {
                        "status": "success",
                        "medication_id": med["id"],
                        "new_times": [new_time]
                    }
        return {"status": "clarification_needed", "message": "Не понял"}
    
    client.process_time_change_command = AsyncMock(side_effect=mock_process_time_change)
    
    # Mock process_dose_change_command
    async def mock_process_dose_change(message, schedule):
        if not schedule:
            return {"status": "error", "message": "No medications"}
        # Extract dosage from message
        import re
        dosage_match = re.search(r'(\d+)\s*(мг|таблетки|таблетка)', message)
        if dosage_match:
            new_dosage = f"{dosage_match.group(1)} {dosage_match.group(2)}"
            # Find medication in message
            for med in schedule:
                if med["name"].lower() in message.lower():
                    return {
                        "status": "success",
                        "medication_id": med["id"],
                        "new_dosage": new_dosage
                    }
        return {"status": "clarification_needed", "message": "Не понял"}
    
    client.process_dose_change_command = AsyncMock(side_effect=mock_process_dose_change)
    
    # Mock process_timezone_change_command
    async def mock_process_timezone(message):
        # Simple timezone detection
        if "москва" in message.lower():
            return {"status": "success", "timezone_offset": "+03:00"}
        elif "лондон" in message.lower():
            return {"status": "success", "timezone_offset": "+00:00"}
        elif "нью-йорк" in message.lower():
            return {"status": "success", "timezone_offset": "-05:00"}
        return {"status": "clarification_needed", "message": "Не понял часовую зону"}
    
    client.process_timezone_change_command = AsyncMock(side_effect=mock_process_timezone)
    
    # Mock process_done_command
    async def mock_process_done(message, schedule):
        if not schedule:
            return {"medication_ids": []}
        # Find medications mentioned in message
        medication_ids = []
        for med in schedule:
            if med["name"].lower() in message.lower():
                medication_ids.append(med["id"])
        return {"medication_ids": medication_ids}
    
    client.process_done_command = AsyncMock(side_effect=mock_process_done)
    
    return client


@pytest.fixture
def real_groq_client():
    """Create real GroqClient for integration tests.
    
    This fixture creates an actual GroqClient instance that will make
    real API calls to Groq LLM. Use this for integration tests that
    verify real-world behavior.
    
    Note: Tests using this fixture should be marked with @pytest.mark.llm_real
    and will be skipped if GROQ_API_KEY is not set.
    
    Returns:
        GroqClient: Real GroqClient instance
    """
    return GroqClient()


@pytest.fixture
def mock_bot():
    """Create mock Bot.
    
    Returns:
        MagicMock: Mocked Telegram Bot with common methods
    """
    bot = MagicMock()
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=12345))
    bot.delete_message = AsyncMock()
    bot.edit_message_reply_markup = AsyncMock()
    return bot


@pytest.fixture
def mock_message():
    """Create mock Message.
    
    Returns:
        MagicMock: Mocked Telegram Message
    """
    message = MagicMock()
    message.from_user.id = 123456789
    message.text = "test message"
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    return message


@pytest.fixture
def mock_callback_query():
    """Create mock CallbackQuery.
    
    Returns:
        MagicMock: Mocked Telegram CallbackQuery
    """
    callback = MagicMock()
    callback.from_user.id = 123456789
    callback.data = "taken:1"
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.edit_reply_markup = AsyncMock()
    callback.message.delete = AsyncMock()
    callback.message.message_id = 12345
    return callback
