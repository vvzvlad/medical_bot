"""Main entry point for medication bot."""

import asyncio
import signal
import sys

from src.bot.bot import get_bot, get_data_manager, get_schedule_manager, init_bot
from src.config import settings
from src.services.scheduler import ReminderScheduler
from src.utils import logger, setup_logger


async def main():
    """Main application entry point."""
    # Setup logging
    setup_logger(
        console_level=settings.log_level,
    )
    
    logger.info("=" * 60)
    logger.info("Starting Medication Bot")
    logger.info("=" * 60)
    
    # Log configuration
    logger.info(f"Data directory: {settings.data_dir}")
    logger.info(f"Default timezone: {settings.default_timezone_offset}")
    logger.info(f"Scheduler interval: {settings.scheduler_interval_seconds}s")
    logger.info(f"Reminder repeat interval: {settings.reminder_repeat_interval_hours}h")
    
    # Initialize bot and services
    try:
        bot, dp = init_bot()
        logger.info("Bot and services initialized")
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}", exc_info=True)
        sys.exit(1)
    
    # Initialize scheduler
    try:
        data_manager = get_data_manager()
        schedule_manager = get_schedule_manager()
        
        scheduler = ReminderScheduler(
            bot=bot,
            data_manager=data_manager,
            schedule_manager=schedule_manager,
        )
        logger.info("Scheduler initialized")
    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {e}", exc_info=True)
        sys.exit(1)
    
    # Setup graceful shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        shutdown_event.set()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start scheduler
    try:
        await scheduler.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        sys.exit(1)
    
    # Start bot polling
    logger.info("Starting bot polling...")
    
    try:
        # Create polling task
        polling_task = asyncio.create_task(
            dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        )
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
        logger.info("Shutdown signal received, stopping services...")
        
        # Stop scheduler
        await scheduler.stop()
        logger.info("Scheduler stopped")
        
        # Stop polling
        await dp.stop_polling()
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        logger.info("Bot polling stopped")
        
        # Close bot session
        await bot.session.close()
        logger.info("Bot session closed")
        
    except Exception as e:
        logger.error(f"Error during bot operation: {e}", exc_info=True)
        
        # Ensure cleanup
        try:
            await scheduler.stop()
        except Exception:
            pass
        
        try:
            await bot.session.close()
        except Exception:
            pass
        
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Medication Bot stopped")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, exiting...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
