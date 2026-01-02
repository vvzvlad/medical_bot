"""Telegram bot implementation for medication reminder."""

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from datetime import datetime
from loguru import logger
from src.enhanced_logger import get_enhanced_logger
from src.settings import settings
from src.database import Database
from src.llm_processor import LLMProcessor
from src.timezone_utils import format_date_for_user

# Initialize enhanced logger
enhanced_logger = get_enhanced_logger()


class MedicationBot:
    def __init__(self, llm_processor: LLMProcessor, database: Database):
        self.bot = Bot(token=settings.telegram_bot_token)
        self.dp = Dispatcher()
        self.llm = llm_processor
        self.db = database
        
        # Setup handlers
        router = Router()
        router.message.register(self.handle_message)
        router.callback_query.register(
            self.handle_taken_callback,
            F.data.startswith("taken:")
        )
        self.dp.include_router(router)
    
    async def send_thinking_message(self, chat_id: int) -> int:
        """Send a thinking message that will be deleted later.
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            Message ID of the thinking message
        """
        try:
            message = await self.bot.send_message(chat_id, "думаю...")
            return message.message_id
        except Exception as e:
            logger.error(f"Error sending thinking message: {e}")
            return None
    
    async def delete_thinking_message(self, chat_id: int, message_id: int):
        """Delete a thinking message.
        
        Args:
            chat_id: Telegram chat ID
            message_id: Message ID of the thinking message to delete
        """
        try:
            await self.bot.delete_message(chat_id, message_id)
        except Exception as e:
            logger.error(f"Error deleting thinking message: {e}")
    
    async def handle_message(self, message: Message):
        """Process incoming text message.
        
        Args:
            message: Telegram message object
        """
        user_id = message.from_user.id
        text = message.text
        
        # Set user context for detailed logging
        user_context = {
            'username': message.from_user.username or 'unknown',
            'first_name': message.from_user.first_name or '',
            'last_name': message.from_user.last_name or '',
            'timezone': 'unknown'  # Will be updated after user lookup
        }
        enhanced_logger.set_user_context(user_id, user_context)
        
        # Log incoming message with detailed context
        enhanced_logger.log_user_message(user_id, text, "incoming")
        
        # Ensure user exists and get timezone
        user = await self.db.get_user(user_id)
        if user is None:
            timezone_offset = settings.default_timezone
            await self.db.create_user(user_id, timezone_offset)
            enhanced_logger.log_info("USER_CREATED", user_id, f"New user created with timezone {timezone_offset}")
        else:
            timezone_offset = user["timezone_offset"]
            # Update user context with timezone
            user_context['timezone'] = timezone_offset
            enhanced_logger.set_user_context(user_id, user_context)
        
        # Send thinking message
        thinking_message_id = await self.send_thinking_message(message.chat.id)
        
        try:
            with enhanced_logger.timer("MESSAGE_PROCESSING", user_id, message_text=text):
                # Stage 1: Classify intent
                with enhanced_logger.timer("LLM_CLASSIFICATION", user_id):
                    command_type = await self.llm.classify_intent(text, user_id)
                
                enhanced_logger.log_info("INTENT_CLASSIFIED", user_id, f"Classified as: {command_type}")
                
                # Stage 2: Process based on classification
                if command_type == "add":
                    await self._handle_add(message, text, user_id)
                elif command_type == "done":
                    await self._handle_done(message, text, user_id, timezone_offset)
                elif command_type == "delete":
                    await self._handle_delete(message, text, user_id)
                elif command_type == "time_change":
                    await self._handle_time_change(message, text, user_id)
                elif command_type == "dose_change":
                    await self._handle_dose_change(message, text, user_id)
                elif command_type == "timezone_change":
                    await self._handle_timezone_change(message, text, user_id)
                elif command_type == "list":
                    await self._handle_list(message, user_id)
                elif command_type == "help":
                    await self._handle_help(message)
                else:
                    await self._handle_unknown(message, text)
        
        except Exception as e:
            enhanced_logger.log_error("MESSAGE_PROCESSING", user_id, str(e), {"message_text": text})
            await message.reply("Произошла ошибка. Попробуйте еще раз.")
        finally:
            # Delete thinking message if it was sent
            if thinking_message_id:
                await self.delete_thinking_message(message.chat.id, thinking_message_id)
    
    async def _handle_add(self, message: Message, text: str, user_id: int):
        """Handle ADD command.
        
        Args:
            message: Telegram message object
            text: User's message text
            user_id: Telegram user ID
        """
        # Parse medications with detailed logging
        with enhanced_logger.timer("LLM_PARSING_ADD", user_id, user_message=text):
            medications = await self.llm.process_add(text, user_id)
        
        added = []
        duplicates = []
        
        enhanced_logger.log_info("MEDICATION_PARSING_RESULT", user_id, f"Parsed {len(medications)} medications from text", medications_count=len(medications))
        
        for med_data in medications:
            name = med_data["medication_name"]
            dosage = med_data.get("dosage")
            times = med_data["times"]
            
            enhanced_logger.log_info("PROCESSING_MEDICATION", user_id, f"Processing {name} at times {times}", dosage=dosage)
            
            for time in times:
                # Check duplicate
                if await self.db.check_duplicate(user_id, name, time):
                    duplicates.append(f"{name} в {time}")
                    enhanced_logger.log_info("DUPLICATE_MEDICATION_FOUND", user_id, f"Duplicate found: {name} at {time}")
                else:
                    med_id = await self.db.add_medication(user_id, name, time, dosage)
                    if med_id:
                        added.append(f"{name} в {time}")
                        enhanced_logger.log_info("MEDICATION_ADDED_SUCCESS", user_id, f"Successfully added {name} at {time} (ID: {med_id})")
        
        # Format response
        if added and duplicates:
            response = "Добавлено:\n" + "\n".join(f"✓ {item}" for item in added)
            response += "\n\nУже в расписании:\n" + "\n".join(f"• {item}" for item in duplicates)
        elif added:
            response = "Добавлено:\n" + "\n".join(f"✓ {item}" for item in added)
        elif duplicates:
            response = "Уже в расписании:\n" + "\n".join(f"• {item}" for item in duplicates)
        else:
            response = "Не удалось добавить медикаменты. Попробуйте переформулировать."
        
        enhanced_logger.log_info("SENDING_RESPONSE", user_id, f"Response: {response}",
                               added_count=len(added), duplicates_count=len(duplicates))
        
        with enhanced_logger.timer("TELEGRAM_API_SEND_MESSAGE", user_id, response_text=response):
            await message.reply(response)
        
        enhanced_logger.log_info("RESPONSE_SENT_SUCCESS", user_id, "Response sent successfully")
    
    async def _handle_done(self, message: Message, text: str, user_id: int, timezone_offset: str):
        """Handle DONE command.
        
        Args:
            message: Telegram message object
            text: User's message text
            user_id: Telegram user ID
            timezone_offset: User's timezone offset
        """
        # Load schedule
        medications = await self.db.get_medications(user_id)
        schedule = [
            {"id": m["id"], "name": m["name"], "time": m["time"], "dosage": m["dosage"]}
            for m in medications
        ]
        
        # Parse
        result = await self.llm.process_done(text, schedule)
        medication_ids = result.get("medication_ids", [])
        
        if not medication_ids:
            await message.reply(f"{result['medication_name']} не найден в расписании")
            return
        
        # Mark as taken
        user_date = format_date_for_user(timezone_offset)
        now = int(datetime.utcnow().timestamp())
        
        for med_id in medication_ids:
            await self.db.mark_as_taken(user_id, med_id, user_date, now)
        
        # Generate confirmation message
        confirmation = await self.llm.generate_confirmation_message(
            result['medication_name'],
            result.get('time'),
            medications[0].get('dosage') if medications else None
        )
        
        await message.reply(confirmation.get("message", f"Отмечено: {result['medication_name']} принят ✓"))
    
    async def _handle_delete(self, message: Message, text: str, user_id: int):
        """Handle DELETE command.
        
        Args:
            message: Telegram message object
            text: User's message text
            user_id: Telegram user ID
        """
        # Load schedule
        medications = await self.db.get_medications(user_id)
        schedule = [
            {"id": m["id"], "name": m["name"], "time": m["time"], "dosage": m["dosage"]}
            for m in medications
        ]
        
        # Parse
        result = await self.llm.process_delete(text, schedule)
        
        status = result.get("status")
        medication_ids = result.get("medication_ids", [])
        medication_name = result.get("medication_name", "Медикамент")
        
        if status == "clarification_needed":
            await message.reply(result.get("message", "Пожалуйста, уточните, какой медикамент вы хотите удалить"))
            return
        elif status == "not_found":
            await message.reply(f"{medication_name} не найден в расписании")
            return
        elif status == "success":
            if not medication_ids:
                await message.reply(f"{medication_name} не найден в расписании")
                return
                
            # Delete medications
            deleted_count = await self.db.delete_medications(medication_ids)
            
            if deleted_count > 0:
                if deleted_count == 1:
                    await message.reply(f"{medication_name} удален из расписания")
                else:
                    await message.reply(f"{medication_name} ({deleted_count} записей) удален из расписания")
            else:
                await message.reply(f"Не удалось удалить {medication_name}")
        else:
            await message.reply("Произошла ошибка при удалении медикамента")
    
    async def _handle_time_change(self, message: Message, text: str, user_id: int):
        """Handle TIME_CHANGE command.
        
        Args:
            message: Telegram message object
            text: User's message text
            user_id: Telegram user ID
        """
        # Load schedule
        medications = await self.db.get_medications(user_id)
        schedule = [
            {"id": m["id"], "name": m["name"], "time": m["time"], "dosage": m["dosage"]}
            for m in medications
        ]
        
        # Parse
        result = await self.llm.process_time_change(text, schedule)
        
        status = result.get("status", "unknown")
        medication_id = result.get("medication_id")
        new_times = result.get("new_times", [])
        medication_name = result.get("medication_name", "медикамента")
        
        if status == "clarification_needed":
            await message.reply(result.get("message", "Пожалуйста, уточните, какой медикамент вы хотите изменить"))
            return
        elif status == "success":
            if not medication_id or not new_times:
                await message.reply("Не удалось получить информацию о медикаменте или новом времени")
                return
            
            if len(new_times) == 1:
                # Simple case: update time
                if await self.db.update_medication_time(medication_id, new_times[0]):
                    await message.reply(f"Время приема {medication_name} изменено на {new_times[0]}")
                else:
                    await message.reply("Не удалось изменить время приема")
            else:
                # Complex case: multiple times - delete old and add new
                medication = await self.db.get_medication(medication_id)
                if medication:
                    # Delete old medication
                    await self.db.delete_medication(medication_id)
                    
                    # Add new medications for each time
                    added_times = []
                    for time in new_times:
                        new_med_id = await self.db.add_medication(
                            user_id, 
                            medication["name"], 
                            time, 
                            medication["dosage"]
                        )
                        if new_med_id:
                            added_times.append(time)
                    
                    if added_times:
                        await message.reply(f"Время приема {medication_name} изменено на: {', '.join(added_times)}")
                    else:
                        await message.reply("Не удалось изменить время приема")
                else:
                    await message.reply("Медикамент не найден")
        else:
            await message.reply("Произошла ошибка при изменении времени приема")
    
    async def _handle_dose_change(self, message: Message, text: str, user_id: int):
        """Handle DOSE_CHANGE command.
        
        Args:
            message: Telegram message object
            text: User's message text
            user_id: Telegram user ID
        """
        # Load schedule
        medications = await self.db.get_medications(user_id)
        schedule = [
            {"id": m["id"], "name": m["name"], "time": m["time"], "dosage": m["dosage"]}
            for m in medications
        ]
        
        # Parse
        result = await self.llm.process_dose_change(text, schedule)
        
        status = result.get("status", "unknown")
        medication_id = result.get("medication_id")
        new_dosage = result.get("new_dosage")
        medication_name = result.get("medication_name", "медикамента")
        
        if status == "clarification_needed":
            await message.reply(result.get("message", "Пожалуйста, уточните, какой медикамент вы хотите изменить"))
            return
        elif status == "success":
            if not medication_id or not new_dosage:
                await message.reply("Не удалось получить информацию о медикаменте или новой дозировке")
                return
                
            if await self.db.update_medication_dosage(medication_id, new_dosage):
                await message.reply(f"Дозировка {medication_name} изменена на {new_dosage}")
            else:
                await message.reply("Не удалось изменить дозировку")
        else:
            await message.reply("Произошла ошибка при изменении дозировки")
    
    async def _handle_timezone_change(self, message: Message, text: str, user_id: int):
        """Handle TIMEZONE_CHANGE command.
        
        Args:
            message: Telegram message object
            text: User's message text
            user_id: Telegram user ID
        """
        # Parse
        result = await self.llm.process_timezone_change(text)
        
        status = result.get("status", "unknown")
        timezone_offset = result.get("timezone_offset")
        city_name = result.get("city_name", "")
        
        if status == "clarification_needed":
            await message.reply(result.get("message", "Пожалуйста, уточните часовой пояс"))
            return
        elif status == "success":
            if not timezone_offset:
                await message.reply("Не удалось получить информацию о часовом поясе")
                return
                
            if await self.db.update_user_timezone(user_id, timezone_offset):
                if city_name:
                    await message.reply(f"Часовой пояс изменен на {city_name} ({timezone_offset})")
                else:
                    await message.reply(f"Часовой пояс изменен на {timezone_offset}")
            else:
                await message.reply("Не удалось изменить часовой пояс")
        else:
            await message.reply("Произошла ошибка при изменении часового пояса")
    
    async def _handle_list(self, message: Message, user_id: int):
        """Handle LIST command.
        
        Args:
            message: Telegram message object
            user_id: Telegram user ID
        """
        medications = await self.db.get_medications(user_id)
        
        if not medications:
            await message.reply("Ваше расписание пусто. Добавьте медикаменты командой типа \"я принимаю аспирин в 19:00\".")
            return
        
        # Sort by time
        medications.sort(key=lambda m: m["time"])
        
        lines = ["Ваше расписание:"]
        for med in medications:
            dosage_str = f" ({med['dosage']})" if med["dosage"] else ""
            lines.append(f"• {med['time']} - {med['name'].capitalize()}{dosage_str}")
        
        await message.reply("\n".join(lines))
    
    async def _handle_help(self, message: Message):
        """Handle HELP command.
        
        Args:
            message: Telegram message object
        """
        result = await self.llm.process_help()
        await message.reply(result.get("message", "Помощь недоступна"))
    
    async def _handle_unknown(self, message: Message, text: str):
        """Handle UNKNOWN command.
        
        Args:
            message: Telegram message object
            text: User's message text
        """
        result = await self.llm.process_unknown(text)
        await message.reply(result.get("message", "Извините, я не понял команду. Напишите 'помощь' для справки."))
    
    async def handle_taken_callback(self, callback: CallbackQuery):
        """Handle 'Принял' button press.
        
        Args:
            callback: Telegram callback query object
        """
        try:
            # Parse callback data: "taken:{medication_id}:{date}"
            parts = callback.data.split(":")
            if len(parts) < 3:
                await callback.answer("Ошибка: некорректные данные")
                return
                
            medication_id = int(parts[1])
            date = parts[2]
            user_id = callback.from_user.id
            
            # Mark as taken
            now = int(datetime.utcnow().timestamp())
            if await self.db.mark_as_taken(user_id, medication_id, date, now):
                # Edit message
                try:
                    await callback.message.edit_text(
                        callback.message.text + "\n\n✅ Принято",
                        reply_markup=None
                    )
                except Exception:
                    # If can't edit, send new message
                    await callback.message.reply("✅ Принято")
                    
                await callback.answer("Отмечено!")
            else:
                await callback.answer("Ошибка при отметке приема")
        except Exception as e:
            logger.error(f"Error handling taken callback: {e}", exc_info=True)
            await callback.answer("Произошла ошибка")
    
    async def send_notification(self, user_id: int, medication: dict, date: str):
        """Send medication notification to user.
        
        Args:
            user_id: Telegram user ID
            medication: Medication dictionary
            date: Date in YYYY-MM-DD format
            
        Returns:
            Message ID if sent successfully, None otherwise
        """
        try:
            # Format message
            dosage_str = f" ({medication['dosage']})" if medication["dosage"] else ""
            text = f"Надо принять:\n{medication['name'].capitalize()}{dosage_str}"
            
            # Create button
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="Принял",
                    callback_data=f"taken:{medication['id']}:{date}"
                )]
            ])
            
            # Send message
            message = await self.bot.send_message(
                user_id,
                text,
                reply_markup=keyboard
            )
            
            return message.message_id
        except Exception as e:
            logger.error(f"Error sending notification to user {user_id}: {e}", exc_info=True)
            return None
    
    async def start(self):
        """Start bot."""
        logger.info("Starting bot...")
        await self.dp.start_polling(self.bot)