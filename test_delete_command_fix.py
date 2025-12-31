#!/usr/bin/env python3
"""Test script to verify the delete command fix handles both dict and list responses."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.bot.handlers import handle_delete_command
from src.llm.client import GroqClient


async def test_delete_command_with_dict_response():
    """Test delete command with single dictionary response (expected format)."""
    print("Testing delete command with dict response...")
    
    # Mock message and user
    mock_message = MagicMock()
    mock_message.from_user.id = 12345
    mock_message.answer = AsyncMock()
    
    # Mock thinking message
    mock_thinking_msg = MagicMock()
    
    # Mock GroqClient to return a dict response
    mock_groq_client = MagicMock(spec=GroqClient)
    mock_groq_client.process_delete_command = AsyncMock(return_value={
        "status": "success",
        "medication_name": "Аспирин",
        "medication_ids": [1]
    })
    
    # Mock schedule_manager
    mock_schedule_manager = MagicMock()
    mock_schedule_manager.get_user_schedule = AsyncMock(return_value=[
        MagicMock(id=1, name="Аспирин", time="12:00", to_dict=lambda: {"id": 1, "name": "Аспирин", "time": "12:00"})
    ])
    mock_schedule_manager.delete_medications = AsyncMock(return_value=True)
    
    # Patch the global variables
    import src.bot.handlers as handlers
    handlers.groq_client = mock_groq_client
    handlers.schedule_manager = mock_schedule_manager
    
    try:
        await handle_delete_command(mock_message, 12345, "удали аспирин", mock_thinking_msg)
        print("✓ Dict response test passed")
        return True
    except Exception as e:
        print(f"✗ Dict response test failed: {e}")
        return False


async def test_delete_command_with_list_response():
    """Test delete command with list response (what was causing the error)."""
    print("Testing delete command with list response...")
    
    # Mock message and user
    mock_message = MagicMock()
    mock_message.from_user.id = 12345
    mock_message.answer = AsyncMock()
    
    # Mock thinking message
    mock_thinking_msg = MagicMock()
    
    # Mock GroqClient to return a list response (what was causing the error)
    mock_groq_client = MagicMock(spec=GroqClient)
    mock_groq_client.process_delete_command = AsyncMock(return_value=[
        {
            "status": "success", 
            "medication_name": "Героин", 
            "medication_ids": [32]
        },
        {
            "status": "success", 
            "medication_name": "Монстр", 
            "medication_ids": [1]
        }
    ])
    
    # Mock schedule_manager
    mock_schedule_manager = MagicMock()
    mock_schedule_manager.get_user_schedule = AsyncMock(return_value=[
        MagicMock(id=32, name="Героин", time="12:00", to_dict=lambda: {"id": 32, "name": "Героин", "time": "12:00"}),
        MagicMock(id=1, name="Монстр", time="11:00", to_dict=lambda: {"id": 1, "name": "Монстр", "time": "11:00"})
    ])
    mock_schedule_manager.delete_medications = AsyncMock(return_value=True)
    
    # Patch the global variables
    import src.bot.handlers as handlers
    handlers.groq_client = mock_groq_client
    handlers.schedule_manager = mock_schedule_manager
    
    try:
        await handle_delete_command(mock_message, 12345, "удали героин и монстр", mock_thinking_msg)
        print("✓ List response test passed")
        return True
    except Exception as e:
        print(f"✗ List response test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("Testing delete command fix...")
    print("=" * 50)
    
    results = []
    results.append(await test_delete_command_with_dict_response())
    results.append(await test_delete_command_with_list_response())
    
    print("=" * 50)
    if all(results):
        print("✓ All tests passed! The fix handles both dict and list responses.")
    else:
        print("✗ Some tests failed. The fix needs more work.")
    
    return all(results)


if __name__ == "__main__":
    asyncio.run(main())