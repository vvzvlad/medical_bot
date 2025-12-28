"""Telegram bot initialization and setup."""

import asyncio
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from src.bot import handlers
from src.config import settings
from src.data.storage import DataManager
from src.llm.client import GroqClient
from src.services.schedule_manager import ScheduleManager

# Global bot instance
bot: Optional[Bot] = None
dp: Optional[Dispatcher] = None

# Service instances
data_manager: Optional[DataManager] = None
schedule_manager: Optional[ScheduleManager] = None
groq_client: Optional[GroqClient] = None


def init_bot() -> tuple[Bot, Dispatcher]:
    """Initialize bot and dispatcher with all services.
    
    Returns:
        Tuple of (Bot, Dispatcher) instances
    """
    global bot, dp, data_manager, schedule_manager, groq_client
    
    logger.info("Initializing bot...")
    
    # Initialize bot with default properties
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Initialize dispatcher
    dp = Dispatcher()
    
    # Initialize services
    data_manager = DataManager(settings.data_dir)
    groq_client = GroqClient()
    schedule_manager = ScheduleManager(data_manager)
    
    # Initialize handlers with service instances
    handlers.init_handlers(data_manager, schedule_manager, groq_client)
    
    # Register router
    dp.include_router(handlers.router)
    
    # Register startup and shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    logger.info("Bot initialized successfully")
    
    return bot, dp


async def on_startup():
    """Handler called when bot starts."""
    logger.info("Bot started")
    logger.info(f"Data directory: {settings.data_dir}")
    logger.info(f"Default timezone: {settings.default_timezone_offset}")
    
    # Log bot info
    if bot:
        bot_info = await bot.get_me()
        logger.info(f"Bot username: @{bot_info.username}")
        logger.info(f"Bot ID: {bot_info.id}")


async def on_shutdown():
    """Handler called when bot shuts down."""
    logger.info("Bot shutting down...")
    
    # Close bot session
    if bot:
        await bot.session.close()
    
    logger.info("Bot stopped")


async def start_polling():
    """Start bot polling."""
    if not bot or not dp:
        raise RuntimeError("Bot not initialized. Call init_bot() first.")
    
    logger.info("Starting polling...")
    
    try:
        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Error during polling: {e}", exc_info=True)
        raise
    finally:
        # Ensure cleanup
        await on_shutdown()


def get_bot() -> Bot:
    """Get bot instance.
    
    Returns:
        Bot instance
        
    Raises:
        RuntimeError: If bot not initialized
    """
    if bot is None:
        raise RuntimeError("Bot not initialized. Call init_bot() first.")
    return bot


def get_data_manager() -> DataManager:
    """Get data manager instance.
    
    Returns:
        DataManager instance
        
    Raises:
        RuntimeError: If data manager not initialized
    """
    if data_manager is None:
        raise RuntimeError("Data manager not initialized. Call init_bot() first.")
    return data_manager


def get_schedule_manager() -> ScheduleManager:
    """Get schedule manager instance.
    
    Returns:
        ScheduleManager instance
        
    Raises:
        RuntimeError: If schedule manager not initialized
    """
    if schedule_manager is None:
        raise RuntimeError("Schedule manager not initialized. Call init_bot() first.")
    return schedule_manager


def get_groq_client() -> GroqClient:
    """Get Groq client instance.
    
    Returns:
        GroqClient instance
        
    Raises:
        RuntimeError: If Groq client not initialized
    """
    if groq_client is None:
        raise RuntimeError("Groq client not initialized. Call init_bot() first.")
    return groq_client
