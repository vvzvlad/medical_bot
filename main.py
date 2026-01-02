"""Main entry point for medication reminder bot."""

import asyncio
import sys
from pathlib import Path
from loguru import logger

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.settings import settings
from src.database import Database
from src.llm_client import LLMClient
from src.llm_processor import LLMProcessor
from src.telegram_bot import MedicationBot
from src.scheduler import NotificationScheduler


async def main():
    """Main application entry point."""
    
    # Configure logging to stdout with loguru
    logger.remove()  # Remove default handler
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    logger.info("Starting Medication Reminder Bot")
    
    # Initialize database
    database = Database(settings.database_path)
    
    # Initialize database schema if needed
    try:
        await database.init()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Initialize LLM client
    llm_client = LLMClient(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        timeout=settings.groq_timeout,
        max_retries=settings.groq_max_retries
    )
    logger.info("LLM client initialized")
    
    llm_processor = LLMProcessor(llm_client)
    
    # Initialize Telegram bot
    bot = MedicationBot(
        llm_processor=llm_processor,
        database=database
    )
    logger.info("Telegram bot initialized")
    
    # Initialize scheduler
    scheduler = NotificationScheduler(
        database=database,
        bot=bot,
        interval_seconds=settings.scheduler_interval,
        reminder_interval_hours=settings.reminder_interval_hours
    )
    
    # Start scheduler and bot concurrently
    logger.info("Starting services...")
    try:
        await asyncio.gather(
            scheduler.start(),
            bot.start()
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())