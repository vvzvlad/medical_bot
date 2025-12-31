#!/usr/bin/env python3
"""Test script to debug the capitalization issue."""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.llm.client import GroqClient
from src.config import settings

async def test_capitalization():
    """Test how capitalization affects command detection."""
    
    # Initialize Groq client
    groq_client = GroqClient()
    
    # Test messages with different capitalization
    test_messages = [
        "выпила монстр в 10:00",      # lowercase
        "Выпила монстр в 10:00",      # capital V
        "выпил монстр в 10:00",       # lowercase
        "Выпил монстр в 10:00",       # capital V
        "принял монстр в 10:00",       # lowercase
        "Принял монстр в 10:00",       # capital P
    ]
    
    print("Testing capitalization impact on command detection...")
    print("=" * 60)
    
    for message in test_messages:
        try:
            command_type = await groq_client.detect_command_type(message)
            print(f"'{message}' -> {command_type}")
        except Exception as e:
            print(f"'{message}' -> Error: {e}")
        print("-" * 40)
    
    print("Done!")

if __name__ == "__main__":
    # Check if GROQ_API_KEY is set
    if not settings.groq_api_key:
        print("GROQ_API_KEY is not set. Please set it in your environment.")
        exit(1)
    
    asyncio.run(test_capitalization())