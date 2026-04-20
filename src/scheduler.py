"""Notification scheduler for medication bot."""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from loguru import logger
from src.enhanced_logger import get_enhanced_logger
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.database import Database
from src.telegram_bot import MedicationBot
from src.timezone_utils import (
    get_user_current_time,
    format_date_for_user,
    is_time_to_send_notification,
    should_send_hourly_reminder,
    is_time_for_next_dose,
    parse_timezone_offset
)

# Initialize enhanced logger
enhanced_logger = get_enhanced_logger()


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
            tick_start = asyncio.get_event_loop().time()

            try:
                await self._check_and_send_notifications()
                await self._check_and_send_reminders()
            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)

            # Sleep for remaining time to prevent cumulative drift
            elapsed = asyncio.get_event_loop().time() - tick_start
            sleep_time = max(1, self.interval - elapsed)
            await asyncio.sleep(sleep_time)
    
    def stop(self):
        """Stop scheduler."""
        self.running = False
        logger.info("Scheduler stopped")
    
    async def _check_and_send_notifications(self):
        """Check for medications that need initial notification.

        Uses >= time comparison so notifications are never missed due to
        scheduler drift.  Deduplication is handled via reminder_message_id
        in the database — once a notification is sent, it won't be sent again.
        This also covers the former _check_missed_notifications functionality.
        """
        users = await self.db.get_all_users()

        for user in users:
            user_id = user["user_id"]
            tz_offset = user["timezone_offset"]
            user_date = format_date_for_user(tz_offset)

            medications = await self.db.get_medications(user_id)

            for med in medications:
                status = await self.db.get_intake_status(
                    user_id, med["id"], user_date
                )

                # Already taken today — skip
                if status and status.get("taken_at"):
                    continue

                # Notification already sent today — skip (reminders handled separately)
                if status and status.get("reminder_message_id"):
                    continue

                # Check if scheduled time has arrived (>= comparison)
                should_send = is_time_to_send_notification(
                    med["time"],
                    tz_offset,
                    status.get("taken_at") if status else None,
                    status.get("reminder_message_id") if status else None
                )

                if not should_send:
                    continue

                # Don't send if medication was created after its scheduled time today —
                # wait for next cycle
                med_created = med.get("created_at", 0)
                med_hour, med_minute = map(int, med["time"].split(':'))

                user_now = get_user_current_time(tz_offset)
                scheduled_time = user_now.replace(
                    hour=med_hour, minute=med_minute,
                    second=0, microsecond=0
                )

                created_dt = datetime.fromtimestamp(
                    med_created, tz=timezone.utc
                ).astimezone(
                    timezone(parse_timezone_offset(tz_offset))
                )

                if created_dt >= scheduled_time:
                    logger.debug(
                        f"Skipping notification for {med['name']} "
                        f"- added after scheduled time, will start from next cycle"
                    )
                    continue

                await self._send_notification(user_id, med, user_date)
    
    async def _send_notification(self, user_id: int, medication: dict, date: str):
        """Send initial notification for medication.
        
        Args:
            user_id: Telegram user ID
            medication: Medication dictionary
            date: Date in YYYY-MM-DD format
        """
        start_time = time.time()
        
        # Log notification attempt
        enhanced_logger.log_scheduler_operation(
            operation="send_notification",
            user_id=user_id,
            medication_data=medication,
            reason="Scheduled medication reminder",
            scheduled_time=medication.get('time', 'unknown')
        )
        
        # Check if there's an existing notification that should be deleted
        status = await self.db.get_intake_status(user_id, medication["id"], date)
        if status and status.get("reminder_message_id"):
            # Delete the old notification message
            try:
                await self.bot.bot.delete_message(user_id, status["reminder_message_id"])
                enhanced_logger.log_info(
                    "DELETED_OLD_NOTIFICATION",
                    user_id=user_id,
                    message=f"Deleted old notification message {status['reminder_message_id']} for {medication['name']}"
                )
            except Exception as e:
                # Message might already be deleted or unavailable
                enhanced_logger.log_warning(
                    "DELETE_OLD_NOTIFICATION_FAILED",
                    user_id=user_id,
                    warning_message=f"Could not delete old notification message: {e}",
                    context={"medication_name": medication['name']}
                )
        
        # Send notification via bot
        message_id = await self.bot.send_notification(user_id, medication, date)
        
        api_time = time.time() - start_time
        
        if message_id:
            enhanced_logger.log_info(
                "NOTIFICATION_SENT_SUCCESS",
                user_id=user_id,
                message=f"Sent notification for {medication['name']} (Message ID: {message_id})",
                api_time=api_time
            )
            
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
        else:
            enhanced_logger.log_error(
                "NOTIFICATION_SEND_FAILED",
                user_id=user_id,
                error_message=f"Failed to send notification for {medication['name']}",
                context={"api_time": api_time}
            )
    
    async def _check_and_send_reminders(self):
        """Check for pending reminders (hourly repeats)."""
        users = await self.db.get_all_users()

        for user in users:
            user_id = user["user_id"]
            tz_offset = user["timezone_offset"]
            user_date = format_date_for_user(tz_offset)

            # Also check yesterday's pending reminders (to continue past midnight)
            user_now = get_user_current_time(tz_offset)
            yesterday = (user_now - timedelta(days=1)).strftime("%Y-%m-%d")

            # Get pending reminders (today and yesterday)
            pending = await self.db.get_pending_reminders(user_id, user_date, yesterday)

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
                        if is_time_for_next_dose(current_med["time"], next_med["time"], tz_offset):
                            # Auto-mark current dose as taken (use status["date"] — may be yesterday)
                            now = int(datetime.now(timezone.utc).timestamp())
                            await self.db.mark_as_taken(user_id, current_med["id"], status["date"], now)

                            # Delete old reminder message
                            if status.get("reminder_message_id"):
                                try:
                                    await self.bot.bot.delete_message(user_id, status["reminder_message_id"])
                                except Exception:
                                    pass  # Message might already be deleted

                            # Send notification for next dose (always on today's date)
                            await self._send_notification(user_id, next_med, user_date)
                            continue  # Skip hourly reminder for current dose

                # Check if enough time has passed since last reminder
                if status.get("reminder_sent_at"):
                    should_remind = should_send_hourly_reminder(
                        status["reminder_sent_at"],
                        int(datetime.now(timezone.utc).timestamp()),
                        self.reminder_interval
                    )

                    if should_remind:
                        logger.info(f"Sending hourly reminder for medication {status['medication_id']} after {self.reminder_interval} hour(s)")
                        # Use status["date"] so the "Принял" button marks the correct record
                        await self._send_hourly_reminder(user_id, status, status["date"])
    
    async def _send_hourly_reminder(self, user_id: int, status: dict, date: str):
        """Send hourly reminder.
        
        Always deletes the old reminder message and sends a fresh one.
        
        Args:
            user_id: Telegram user ID
            status: Intake status dictionary
            date: Date in YYYY-MM-DD format
        """
        start_time = time.time()
        
        enhanced_logger.log_scheduler_operation(
            operation="send_hourly_reminder",
            user_id=user_id,
            medication_data={"id": status['medication_id'], "name": status['name']},
            reason="Hourly reminder for pending medication",
            scheduled_time=status.get('time', 'unknown')
        )
        
        # Delete the old reminder message if it exists
        if status.get("reminder_message_id"):
            try:
                await self.bot.bot.delete_message(user_id, status["reminder_message_id"])
                enhanced_logger.log_info(
                    "DELETED_OLD_REMINDER",
                    user_id=user_id,
                    message=f"Deleted old reminder message {status['reminder_message_id']} for {status['name']}"
                )
            except Exception as delete_error:
                # Message might already be deleted or unavailable
                enhanced_logger.log_warning(
                    "DELETE_OLD_REMINDER_FAILED",
                    user_id=user_id,
                    warning_message=f"Could not delete old reminder message: {delete_error}",
                    context={"medication_name": status['name']}
                )
        
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
        
        message_sent = False
        new_message_id = None
        
        # Send new reminder message
        try:
            message = await self.bot.bot.send_message(
                user_id,
                text,
                reply_markup=keyboard
            )
            new_message_id = message.message_id
            message_sent = True
            
            enhanced_logger.log_info(
                "HOURLY_REMINDER_SENT",
                user_id=user_id,
                message=f"Sent new hourly reminder message {new_message_id} for {status['name']}",
                api_time=time.time() - start_time
            )
            
            # Update message ID in database
            await self.db.set_reminder_message_id(
                user_id,
                status["medication_id"],
                date,
                message.message_id
            )
        except Exception as e:
            enhanced_logger.log_error(
                "HOURLY_REMINDER_SEND_FAILED",
                user_id=user_id,
                error_message=f"Failed to send hourly reminder: {e}",
                context={
                    "medication_name": status['name'],
                    "api_time": time.time() - start_time
                }
            )
        
        # Update timestamp only if message was sent successfully
        if message_sent:
            await self.db.update_reminder_sent_at(
                status["id"],
                int(datetime.now(timezone.utc).timestamp())
            )
    
