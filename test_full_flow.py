#!/usr/bin/env python3
"""Test script to debug the full message processing flow."""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.llm.client import GroqClient
from src.config import settings

async def test_full_flow():
    """Test the full message processing flow."""
    
    # Initialize Groq client
    groq_client = GroqClient()
    
    # Test the exact user message from the conversation
    user_message = "Выпила монстр в 10:00"
    
    print(f"Testing full flow for: '{user_message}'")
    print("=" * 50)
    
    # Step 1: Command type detection
    try:
        command_type = await groq_client.detect_command_type(user_message)
        print(f"Step 1 - Command type detection: '{user_message}' -> {command_type}")
        
        if command_type == "done":
            # Step 2: Process done command
            # Mock schedule similar to what user might have
            schedule = [
                {"id": 1, "name": "Монстр", "time": "10:00", "dosage": ""},
                {"id": 2, "name": "Аспирин", "time": "08:00", "dosage": "200 мг"}
            ]
            
            print(f"Step 2 - Processing done command with schedule: {schedule}")
            
            result = await groq_client.process_done_command(user_message, schedule)
            print(f"Done command result: {result}")
            
            # Step 3: Generate confirmation message
            if result.get("medication_ids"):
                medication_name = result.get("medication_name", "Монстр")
                confirmation_message = await groq_client.generate_confirmation_message(
                    medication_name=medication_name,
                    medication_time="10:00"
                )
                print(f"Step 3 - Confirmation message: {confirmation_message}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check if GROQ_API_KEY is set
    if not settings.groq_api_key:
        print("GROQ_API_KEY is not set. Please set it in your environment.")
        exit(1)
    
    asyncio.run(test_full_flow())