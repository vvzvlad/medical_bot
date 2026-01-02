"""Notification scheduler for medication bot."""

import asyncio
from datetime import datetime
from loguru import logger
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.database import Database
from src.telegram_bot import MedicationBot
from src.timezone_utils import (
    get_user_current_time,
    format_date_for_user,
    is_time_to_send_notification,
    should_send_hourly_reminder,
    is_time_for_next_dose
)


class NotificationScheduler:
    def __init__(
        self, 
        database: Database, 
        bot: MedicationBot,
        interval_seconds: int = 60,
        reminder_interval_hours: int = 1
    ):
        self.db = database
        self.bot = bot
        self.interval = interval_seconds
        self.reminder_interval = reminder_interval_hours
        self.running = False
    
    async def start(self):
        """Start scheduler loop."""
        self.running = True
        logger.info("Scheduler started")
        
        while self.running:
            try:
                await self._check_and_send_notifications()
                await self._check_and_send_reminders()
                await self._check_missed_notifications()
            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)
            
            await asyncio.sleep(self.interval)
    
    def stop(self):
        """Stop scheduler."""
        self.running = False
        logger.info("Scheduler stopped")
    
    async def _check_and_send_notifications(self):
        """Check for medications that need initial notification."""
        users = await self.db.get_all_users()
        
        for user in users:
            user_id = user["user_id"]
            timezone = user["timezone_offset"]
            user_date = format_date_for_user(timezone)
            
            medications = await self.db.get_medications(user_id)
            
            for med in medications:
                # Check if it's time to send notification
                # First check if we already have an intake status for today
                status = await self.db.get_intake_status(
                    user_id,
                    med["id"],
                    user_date
                )
                
                # If no status or not taken yet, check if it's time to send
                if status is None or (status.get("taken_at") is None):
                    should_send = is_time_to_send_notification(
                        med["time"],
                        timezone,
                        status.get("taken_at") if status else None,
                        status.get("reminder_message_id") if status else None
                    )
                    
                    # Implement "next appropriate cycle" logic:
                    # Only send notification if we haven't already sent one for this medication today
                    # and it's exactly the scheduled time
                    if should_send:
                        # Check if we already have a reminder message ID (meaning we already sent notification)
                        if status and status.get("reminder_message_id"):
                            logger.debug(f"Skipping notification for {med['name']} - already sent today")
                            continue
                        
                        await self._send_notification(user_id, med, user_date)
    
    async def _send_notification(self, user_id: int, medication: dict, date: str):
        """Send initial notification for medication.
        
        Args:
            user_id: Telegram user ID
            medication: Medication dictionary
            date: Date in YYYY-MM-DD format
        """
        logger.info(f"Sending notification: {medication['name']} to user {user_id}")
        
        # Check if there's an existing notification that should be deleted
        status = await self.db.get_intake_status(user_id, medication["id"], date)
        if status and status.get("reminder_message_id"):
            # Delete the old notification message
            try:
                await self.bot.bot.delete_message(user_id, status["reminder_message_id"])
                logger.debug(f"Deleted old notification message {status['reminder_message_id']} for {medication['name']}")
            except Exception as e:
                # Message might already be deleted or unavailable
                logger.debug(f"Could not delete old notification message: {e}")
        
        # Send notification via bot
        message_id = await self.bot.send_notification(user_id, medication, date)
        
        if message_id:
            # Create or update intake_status record
            if status:
                # Update existing record
                await self.db.set_reminder_message_id(user_id, medication["id"], date, message_id)
            else:
                # Create new record
                await self.db.create_intake_status(
                    user_id,
                    medication["id"],
                    date,
                    message_id
                )
    
    async def _check_and_send_reminders(self):
        """Check for pending reminders (hourly repeats)."""
        users = await self.db.get_all_users()
        
        for user in users:
            user_id = user["user_id"]
            timezone = user["timezone_offset"]
            user_date = format_date_for_user(timezone)
            
            # Get pending reminders
            pending = await self.db.get_pending_reminders(user_id, user_date)
            
            for status in pending:
                # Check if it's time for next dose (auto-mark current as taken)
                medications = await self.db.get_medications(user_id)
                current_med = next((m for m in medications if m["id"] == status["medication_id"]), None)
                
                if current_med:
                    # Check if there's a next dose of the same medication
                    same_meds = [m for m in medications if m["name"] == current_med["name"]]
                    same_meds.sort(key=lambda m: m["time"])
                    
                    # Find next dose
                    next_med = None
                    for i, med in enumerate(same_meds):
                        if med["id"] == current_med["id"] and i < len(same_meds) - 1:
                            next_med = same_meds[i + 1]
                            break
                    
                    if next_med:
                        # Check if it's time for next dose
                        if is_time_for_next_dose(current_med["time"], next_med["time"], timezone):
                            # Auto-mark current dose as taken
                            now = int(datetime.utcnow().timestamp())
                            await self.db.mark_as_taken(user_id, current_med["id"], user_date, now)
                            
                            # Delete old reminder message
                            if status.get("reminder_message_id"):
                                try:
                                    await self.bot.bot.delete_message(user_id, status["reminder_message_id"])
                                except Exception:
                                    pass  # Message might already be deleted
                            
                            # Send notification for next dose
                            await self._send_notification(user_id, next_med, user_date)
                            continue  # Skip hourly reminder for current dose
                
                # Check if hour has passed since last reminder
                if status.get("reminder_sent_at"):
                    should_remind = should_send_hourly_reminder(
                        status["reminder_sent_at"],
                        int(datetime.utcnow().timestamp()),
                        self.reminder_interval
                    )
                    
                    if should_remind:
                        # Additional gating: ensure we haven't already sent a reminder in the last hour
                        # This prevents minute-level repeats when scheduler runs every 60 seconds
                        logger.info(f"Sending hourly reminder for medication {status['medication_id']} after {self.reminder_interval} hour(s)")
                        await self._send_hourly_reminder(user_id, status, user_date)
    
    async def _send_hourly_reminder(self, user_id: int, status: dict, date: str):
        """Send or edit hourly reminder.
        
        Args:
            user_id: Telegram user ID
            status: Intake status dictionary
            date: Date in YYYY-MM-DD format
        """
        logger.info(f"Sending hourly reminder for medication {status['medication_id']}")
        
        # Format message
        dosage_str = f" ({status['dosage']})" if status.get("dosage") else ""
        text = f"Напоминание:\n{status['name'].capitalize()}{dosage_str}"
        
        # Create button
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="Принял",
                callback_data=f"taken:{status['medication_id']}:{date}"
            )]
        ])
        
        # Try to edit existing message
        if status.get("reminder_message_id"):
            try:
                await self.bot.bot.edit_message_text(
                    text,
                    user_id,
                    status["reminder_message_id"],
                    reply_markup=keyboard
                )
            except Exception:
                # Message not found, send new
                try:
                    message = await self.bot.bot.send_message(
                        user_id,
                        text,
                        reply_markup=keyboard
                    )
                    await self.db.set_reminder_message_id(
                        user_id,
                        status["medication_id"],
                        date,
                        message.message_id
                    )
                except Exception as e:
                    logger.error(f"Failed to send reminder message: {e}")
        
        # Update timestamp
        await self.db.update_reminder_sent_at(
            status["id"],
            int(datetime.utcnow().timestamp())
        )
    
    async def _check_missed_notifications(self):
        """Check for missed notifications after downtime."""
        users = await self.db.get_all_users()
        
        for user in users:
            user_id = user["user_id"]
            timezone = user["timezone_offset"]
            user_date = format_date_for_user(timezone)
            
            # Get medications that should have had notifications but didn't
            missed = await self.db.get_missed_notifications(user_id, user_date)
            
            for med in missed:
                # Check if it's still relevant to send (not too late in the day)
                user_time = get_user_current_time(timezone)
                med_hour, med_minute = map(int, med["time"].split(":"))
                
                # If it's still the same day and before 23:59, send missed notification
                if user_time.hour < 23 or (user_time.hour == 23 and user_time.minute < 59):
                    # Check if we haven't already sent a reminder today
                    status = await self.db.get_intake_status(user_id, med["id"], user_date)
                    
                    if not status or not status.get("reminder_message_id"):
                        logger.info(f"Sending missed notification for {med['name']} to user {user_id}")
                        
                        # Delete old notification if it exists
                        if status and status.get("reminder_message_id"):
                            try:
                                await self.bot.bot.delete_message(user_id, status["reminder_message_id"])
                                logger.debug(f"Deleted old missed notification message {status['reminder_message_id']} for {med['name']}")
                            except Exception as e:
                                logger.debug(f"Could not delete old missed notification message: {e}")
                        
                        # Send notification with "пропущено" marker
                        dosage_str = f" ({med['dosage']})" if med.get("dosage") else ""
                        text = f"Надо принять (пропущено):\n{med['name'].capitalize()}{dosage_str}"
                        
                        # Create button
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text="Принял",
                                callback_data=f"taken:{med['id']}:{user_date}"
                            )]
                        ])
                        
                        try:
                            message = await self.bot.bot.send_message(
                                user_id,
                                text,
                                reply_markup=keyboard
                            )
                            
                            # Create or update intake_status record
                            if status:
                                await self.db.set_reminder_message_id(
                                    user_id,
                                    med["id"],
                                    user_date,
                                    message.message_id
                                )
                            else:
                                await self.db.create_intake_status(
                                    user_id,
                                    med["id"],
                                    user_date,
                                    message.message_id
                                )
                        except Exception as e:
                            logger.error(f"Failed to send missed notification: {e}")