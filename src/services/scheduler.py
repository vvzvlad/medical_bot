"""Reminder scheduler for medication bot."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNotFound
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.config import settings
from src.data.models import Medication
from src.data.storage import DataManager
from src.services.notification_manager import NotificationManager
from src.services.schedule_manager import ScheduleManager
from src.utils import log_operation, logger


class ReminderScheduler:
    """Background scheduler for medication reminders.
    
    Runs as a background task that checks all users every minute
    and sends reminders for medications that need to be taken.
    
    Features:
    - Checks all users every SCHEDULER_INTERVAL_SECONDS
    - Groups multiple medications in one message
    - Deletes previous reminder if same medication time comes
    - Sends hourly repeat reminders for unpicked medications
    - Handles Telegram API errors gracefully
    """
    
    def __init__(
        self,
        bot: Bot,
        data_manager: DataManager,
        schedule_manager: ScheduleManager,
    ):
        """Initialize reminder scheduler.
        
        Args:
            bot: Telegram Bot instance
            data_manager: DataManager instance
            schedule_manager: ScheduleManager instance
        """
        self.bot = bot
        self.data_manager = data_manager
        self.schedule_manager = schedule_manager
        self.notification_manager = NotificationManager(data_manager)
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        logger.info("ReminderScheduler initialized")
    
    async def start(self):
        """Start the scheduler loop."""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler started")
    
    async def stop(self):
        """Stop the scheduler gracefully."""
        if not self._running:
            logger.warning("Scheduler not running")
            return
        
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop that runs every SCHEDULER_INTERVAL_SECONDS."""
        logger.info(
            f"Scheduler loop started (interval: {settings.scheduler_interval_seconds}s)"
        )
        
        while self._running:
            try:
                await self.check_and_send_reminders()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
            
            # Wait for next iteration
            await asyncio.sleep(settings.scheduler_interval_seconds)
    
    async def check_and_send_reminders(self):
        """Check all users and send reminders if needed."""
        logger.debug("Checking reminders for all users...")
        
        # Get all user files
        user_files = list(settings.data_dir.glob("*.json"))
        
        if not user_files:
            logger.debug("No users found")
            return
        
        logger.debug(f"Checking {len(user_files)} user(s)")
        
        # Process each user
        for user_file in user_files:
            try:
                user_id = int(user_file.stem)
                await self.process_user_reminders(user_id)
            except ValueError:
                logger.warning(f"Invalid user file name: {user_file.name}")
            except Exception as e:
                logger.error(
                    f"Error processing reminders for user {user_file.stem}: {e}",
                    exc_info=True
                )
                # Continue with other users even if one fails
                continue
    
    async def process_user_reminders(self, user_id: int):
        """Process reminders for a single user.
        
        Args:
            user_id: Telegram user ID
        """
        try:
            # Get medications that need reminders
            medications = await self.notification_manager.get_medications_to_remind(user_id)
            
            if not medications:
                logger.debug(f"No medications to remind for user {user_id}")
                return
            
            logger.info(
                f"Found {len(medications)} medication(s) to remind for user {user_id}"
            )
            
            # Check for previous reminders to delete
            await self._handle_previous_reminders(user_id, medications)
            
            # Send reminder
            await self.send_reminder(user_id, medications)
            
        except ValueError as e:
            logger.error(f"User {user_id} not found: {e}")
        except Exception as e:
            logger.error(
                f"Error processing reminders for user {user_id}: {e}",
                exc_info=True
            )
    
    async def _handle_previous_reminders(
        self,
        user_id: int,
        medications: list[Medication],
    ):
        """Handle deletion of previous reminders.
        
        According to business logic: if same medication (by name) time comes,
        delete previous reminder and consider that intake was done.
        
        Args:
            user_id: Telegram user ID
            medications: List of medications to remind about
        """
        for medication in medications:
            try:
                # Check if there's a previous reminder for same medication name
                message_id = await self.notification_manager.should_delete_previous_reminder(
                    user_id=user_id,
                    medication_name=medication.name,
                    current_medication_id=medication.id,
                )
                
                if message_id:
                    # Delete previous reminder
                    await self.delete_previous_reminder(user_id, message_id)
                    
                    # Clear reminder_message_id for the old medication
                    # Find the medication with this message_id
                    user_data = await self.data_manager.get_user_data(user_id)
                    if user_data:
                        for med in user_data.medications:
                            if med.reminder_message_id == message_id:
                                await self.notification_manager.clear_reminder_message_id(
                                    user_id, med.id
                                )
                                # Mark old medication as taken (consider intake was done)
                                await self.schedule_manager.mark_medication_taken(
                                    user_id, med.id
                                )
                                logger.info(
                                    f"Marked old medication {med.id} as taken "
                                    f"(same name: {medication.name})"
                                )
                                break
            except Exception as e:
                logger.error(
                    f"Error handling previous reminder for medication "
                    f"{medication.id}: {e}",
                    exc_info=True
                )
    
    async def send_reminder(self, user_id: int, medications: list[Medication]):
        """Send reminder message with inline keyboard.
        
        Args:
            user_id: Telegram user ID
            medications: List of medications to remind about
        """
        try:
            # Format message
            message_text = self.notification_manager.format_reminder_message(medications)
            
            # Create inline keyboard
            keyboard_data = self.notification_manager.create_reminder_keyboard(medications)
            
            # Convert to aiogram keyboard
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=button["text"],
                            callback_data=button["callback_data"]
                        )
                    ]
                    for button in [row[0] for row in keyboard_data["inline_keyboard"]]
                ]
            )
            
            # Send message
            message = await self.bot.send_message(
                chat_id=user_id,
                text=message_text,
                reply_markup=keyboard
            )
            
            medication_names = [med.name for med in medications]
            log_operation(
                "reminder_sent",
                user_id=user_id,
                medications_count=len(medications),
                medication_names=medication_names,
                message_id=message.message_id
            )
            logger.info(
                f"Sent reminder to user {user_id} for {len(medications)} medication(s): "
                f"{', '.join(medication_names)}, message_id: {message.message_id}"
            )
            
            # Store reminder_message_id for each medication
            for medication in medications:
                await self.notification_manager.set_reminder_message_id(
                    user_id=user_id,
                    medication_id=medication.id,
                    message_id=message.message_id,
                )
            
            # Increment stats counter
            from src.bot.handlers import increment_reminders_sent
            increment_reminders_sent()
            
        except TelegramForbiddenError as e:
            logger.warning(
                f"User {user_id} blocked the bot",
                extra={"user_id": user_id, "error": str(e)}
            )
        except TelegramNotFound as e:
            logger.warning(
                f"Chat {user_id} not found",
                extra={"user_id": user_id, "error": str(e)}
            )
        except TelegramBadRequest as e:
            logger.error(
                f"Bad request when sending reminder to user {user_id}: {e}",
                exc_info=True,
                extra={"user_id": user_id}
            )
        except Exception as e:
            logger.error(
                f"Error sending reminder to user {user_id}: {type(e).__name__}: {e}",
                exc_info=True,
                extra={"user_id": user_id, "medications_count": len(medications)}
            )
    
    async def delete_previous_reminder(self, user_id: int, message_id: int):
        """Delete previous reminder message.
        
        Args:
            user_id: Telegram user ID
            message_id: Message ID to delete
        """
        try:
            await self.bot.delete_message(chat_id=user_id, message_id=message_id)
            logger.info(f"Deleted previous reminder message {message_id} for user {user_id}")
        except TelegramBadRequest as e:
            logger.warning(
                f"Could not delete message {message_id} for user {user_id}: {e}"
            )
        except Exception as e:
            logger.error(
                f"Error deleting message {message_id} for user {user_id}: {e}",
                exc_info=True
            )
