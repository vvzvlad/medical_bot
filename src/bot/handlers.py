"""Telegram bot handlers for medication bot."""

import asyncio
from datetime import datetime
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.config import settings
from src.data.storage import DataManager
from src.llm.client import GroqAPIError, GroqClient, GroqInsufficientFundsError, GroqTimeoutError
from src.services.schedule_manager import ScheduleManager
from src.utils import format_error_for_user, log_operation, logger

# Initialize router
router = Router()

# Initialize services (will be set in bot.py)
data_manager: Optional[DataManager] = None
schedule_manager: Optional[ScheduleManager] = None
groq_client: Optional[GroqClient] = None

# Stats counters
stats = {
    "reminders_sent": 0,
    "start_time": datetime.utcnow()
}


def init_handlers(dm: DataManager, sm: ScheduleManager, gc: GroqClient):
    """Initialize handlers with service instances.
    
    Args:
        dm: DataManager instance
        sm: ScheduleManager instance
        gc: GroqClient instance
    """
    global data_manager, schedule_manager, groq_client
    data_manager = dm
    schedule_manager = sm
    groq_client = gc
    logger.info("Handlers initialized with service instances")


async def generate_onboarding_message() -> str:
    """Generate onboarding message using LLM.
    
    Returns:
        Welcome message with timezone setup prompt
    """
    prompt = """Ты ассистент для управления приемом медикаментов. 
Напиши приветственное сообщение для нового пользователя.
Сообщение должно:
- Кратко описать возможности бота (управление расписанием приема медикаментов, напоминания)
- Предложить установить часовой пояс (например, "моя часовая зона Москва" или "я в Москве")
- Быть дружелюбным и понятным

Пример ответа:
{"message": "Привет! Я помогу вам не забывать принимать медикаменты..."}

Ответ должен быть в формате JSON."""
    
    try:
        result = await groq_client._make_request(prompt)
        return result.get("message", "Привет! Я бот для управления приемом медикаментов. Для начала укажите ваш часовой пояс, например: 'моя часовая зона Москва'")
    except Exception as e:
        logger.error(f"Failed to generate onboarding message: {e}")
        return "Привет! Я бот для управления приемом медикаментов. Для начала укажите ваш часовой пояс, например: 'моя часовая зона Москва'"


@router.message(Command("delete_me"))
async def handle_delete_me_command(message: Message):
    """Handle /delete_me command - delete user data.
    
    Args:
        message: Incoming message with /delete_me command
    """
    user_id = message.from_user.id
    logger.info(f"Delete_me command from user {user_id}")
    
    try:
        # Check if user exists
        user_data = await data_manager.get_user_data(user_id)
        if user_data is None:
            await message.answer("У вас нет данных для удаления.")
            return
        
        # Delete user data file
        user_file = settings.data_dir / f"{user_id}.json"
        if user_file.exists():
            user_file.unlink()
            logger.info(f"Deleted user data file for user {user_id}")
            await message.answer("Ваши данные успешно удалены. Для начала работы отправьте любое сообщение.")
        else:
            await message.answer("Файл данных не найден.")
            
    except Exception as e:
        logger.error(f"Error deleting user data for user {user_id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при удалении данных.")


@router.message(Command("stats"))
async def handle_stats_command(message: Message):
    """Handle /stats command - show bot statistics.
    
    Args:
        message: Incoming message with /stats command
    """
    logger.info(f"Stats command from user {message.from_user.id}")
    
    try:
        # Count total users
        user_files = list(settings.data_dir.glob("*.json"))
        total_users = len(user_files)
        
        # Count total medications
        total_medications = 0
        for user_file in user_files:
            try:
                user_data = await data_manager.get_user_data(int(user_file.stem))
                if user_data:
                    total_medications += len(user_data.medications)
            except Exception as e:
                logger.warning(f"Failed to load user data from {user_file}: {e}")
        
        # Calculate uptime
        uptime = datetime.utcnow() - stats["start_time"]
        uptime_hours = int(uptime.total_seconds() // 3600)
        uptime_minutes = int((uptime.total_seconds() % 3600) // 60)
        
        # Format stats message
        stats_message = (
            f"📊 Статистика бота:\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"💊 Всего медикаментов: {total_medications}\n"
            f"🔔 Отправлено напоминаний: {stats['reminders_sent']}\n"
            f"⏱ Время работы: {uptime_hours}ч {uptime_minutes}м"
        )
        
        await message.answer(stats_message)
        logger.info(f"Stats sent to user {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error handling stats command: {e}")
        await message.answer("Произошла ошибка при получении статистики.")


@router.message(F.text)
async def handle_text_message(message: Message):
    """Handle all text messages through LLM processing.
    
    Args:
        message: Incoming text message
    """
    user_id = message.from_user.id
    user_message = message.text
    
    log_operation("message_received", user_id=user_id, message_length=len(user_message))
    logger.info(f"Message from user {user_id}: {user_message[:100]}...")
    
    try:
        # Check if user exists, if not - create with onboarding
        user_data = await data_manager.get_user_data(user_id)
        if user_data is None:
            log_operation("new_user_onboarding", user_id=user_id)
            logger.info(f"New user {user_id}, creating with onboarding")
            
            # Create new user with default timezone
            await data_manager.create_user(user_id, settings.default_timezone_offset)
            
            # Generate and send onboarding message
            onboarding_msg = await generate_onboarding_message()
            await message.answer(onboarding_msg)
            return
        
        # Stage 1: Detect command type
        try:
            command_type = await groq_client.detect_command_type(user_message)
            log_operation("command_detected", user_id=user_id, command_type=command_type)
            logger.info(f"Detected command type: {command_type} for user {user_id}")
        except GroqInsufficientFundsError as e:
            logger.error(f"LLM API insufficient funds for user {user_id}", exc_info=True)
            await message.answer(format_error_for_user(e))
            return
        except GroqTimeoutError as e:
            logger.warning(f"LLM API timeout for user {user_id}", exc_info=True)
            await message.answer(format_error_for_user(e))
            return
        except GroqAPIError as e:
            logger.error(f"LLM API error for user {user_id}: {e}", exc_info=True)
            await message.answer(format_error_for_user(e))
            return
        
        # Stage 2: Process command based on type
        if command_type == "list":
            await handle_list_command(message, user_id)
            
        elif command_type == "add":
            await handle_add_command(message, user_id, user_message)
            
        elif command_type == "delete":
            await handle_delete_command(message, user_id, user_message)
            
        elif command_type == "time_change":
            await handle_time_change_command(message, user_id, user_message)
            
        elif command_type == "dose_change":
            await handle_dose_change_command(message, user_id, user_message)
            
        elif command_type == "timezone_change":
            await handle_timezone_change_command(message, user_id, user_message)
            
        elif command_type == "done":
            await handle_done_command(message, user_id, user_message)
            
        else:  # unknown
            await handle_unknown_command(message, user_message)
            
    except Exception as e:
        logger.error(
            f"Unexpected error handling message from user {user_id}: {type(e).__name__}: {e}",
            exc_info=True,
            extra={"user_id": user_id, "message_text": user_message[:100]}
        )
        await message.answer(format_error_for_user(e))


async def handle_list_command(message: Message, user_id: int):
    """Handle list command - show user's medication schedule.
    
    Args:
        message: Incoming message
        user_id: User ID
    """
    try:
        medications = await schedule_manager.get_user_schedule(user_id)
        schedule_text = schedule_manager.format_schedule_for_display(medications)
        await message.answer(schedule_text)
        logger.info(f"Sent schedule to user {user_id}")
    except Exception as e:
        logger.error(f"Error showing schedule for user {user_id}: {e}")
        await message.answer("Произошла ошибка при получении расписания.")


async def handle_add_command(message: Message, user_id: int, user_message: str):
    """Handle add medication command.
    
    Args:
        message: Incoming message
        user_id: User ID
        user_message: User's message text
    """
    medication_name = None  # Initialize to avoid UnboundLocalError in exception handler
    
    try:
        result = await groq_client.process_add_command(user_message)
        
        # Handle both single medication (dict) and multiple medications (list)
        medications_to_add = []
        
        if isinstance(result, list):
            # Multiple medications
            medications_to_add = result
        elif isinstance(result, dict):
            # Single medication
            medications_to_add = [result]
        else:
            logger.warning(
                f"Unexpected result type from process_add_command for user {user_id}",
                extra={"result_type": type(result).__name__, "result": result}
            )
            await message.answer("Не удалось распознать команду. Попробуйте переформулировать.")
            return
        
        # Validate and add each medication
        added_medications = []
        for med_data in medications_to_add:
            medication_name = med_data.get("medication_name")
            times = med_data.get("times", [])
            dosage = med_data.get("dosage")
            
            if not medication_name or not times:
                logger.warning(
                    f"Failed to parse medication data for user {user_id}",
                    extra={"med_data": med_data}
                )
                continue
            
            # Add medication
            created_meds = await schedule_manager.add_medication(
                user_id=user_id,
                name=medication_name,
                times=times,
                dosage=dosage
            )
            
            # Track added medications for response
            times_str = " и ".join(times)
            dosage_str = f" {dosage}" if dosage else ""
            added_medications.append(f"{medication_name}{dosage_str} в {times_str}")
            
            log_operation(
                "medication_added",
                user_id=user_id,
                medication_name=medication_name,
                times=times,
                dosage=dosage
            )
            logger.info(f"Added medication for user {user_id}: {medication_name} at {times_str}")
        
        # Send response
        if added_medications:
            if len(added_medications) == 1:
                response = f"Добавлено: {added_medications[0]}"
            else:
                response = "Добавлено:\n" + "\n".join(f"• {med}" for med in added_medications)
            await message.answer(response)
        else:
            await message.answer("Не удалось распознать название медикамента или время приема. Попробуйте переформулировать.")
        
    except GroqAPIError as e:
        logger.error(f"LLM API error in add command for user {user_id}: {e}", exc_info=True)
        await message.answer(format_error_for_user(e))
    except Exception as e:
        logger.error(
            f"Error adding medication for user {user_id}: {type(e).__name__}: {e}",
            exc_info=True,
            extra={"user_id": user_id, "medication_name": medication_name}
        )
        await message.answer(format_error_for_user(e))


async def handle_delete_command(message: Message, user_id: int, user_message: str):
    """Handle delete medication command.
    
    Args:
        message: Incoming message
        user_id: User ID
        user_message: User's message text
    """
    try:
        # Get current schedule
        medications = await schedule_manager.get_user_schedule(user_id)
        schedule = [med.to_dict() for med in medications]
        
        if not schedule:
            await message.answer("У вас нет медикаментов в расписании.")
            return
        
        result = await groq_client.process_delete_command(user_message, schedule)
        
        status = result.get("status")
        
        if status == "clarification_needed":
            clarification_msg = result.get("message", "Уточните, какой именно медикамент вы хотите удалить.")
            await message.answer(clarification_msg)
            return
        
        if status == "not_found":
            await message.answer("Не удалось найти указанный медикамент в вашем расписании.")
            return
        
        medication_ids = result.get("medication_ids", [])
        
        if not medication_ids:
            await message.answer("Не удалось определить, какой медикамент удалить. Попробуйте переформулировать.")
            return
        
        # Validate that returned IDs exist in the schedule
        valid_ids = {med.id for med in medications}
        original_ids = medication_ids.copy()
        medication_ids = [id for id in medication_ids if id in valid_ids]
        
        # Log if any IDs were filtered out
        filtered_ids = [id for id in original_ids if id not in medication_ids]
        if filtered_ids:
            logger.warning(
                f"LLM returned invalid medication IDs for user {user_id}: {filtered_ids}. "
                f"Valid IDs: {list(valid_ids)}. Filtered them out.",
                extra={"user_id": user_id, "invalid_ids": filtered_ids, "valid_ids": list(valid_ids)}
            )
        
        if not medication_ids:
            await message.answer("Не удалось найти указанный медикамент в вашем расписании.")
            return
        
        # Delete medications
        deleted = await schedule_manager.delete_medications(user_id, medication_ids)
        
        if deleted:
            if len(medication_ids) == 1:
                await message.answer("Медикамент удален из расписания.")
            else:
                await message.answer(f"Удалено медикаментов: {len(medication_ids)}")
        else:
            await message.answer("У вас нет такого медикамента в расписании.")
        
        logger.info(f"Deleted medications for user {user_id}: {medication_ids}")
        
    except GroqAPIError as e:
        await message.answer(f"Произошла ошибка при обработке команды: {str(e)}. Попробуйте еще раз.")
    except Exception as e:
        logger.error(f"Error deleting medication for user {user_id}: {e}")
        await message.answer("Произошла ошибка при удалении медикамента.")


async def handle_time_change_command(message: Message, user_id: int, user_message: str):
    """Handle time change command.
    
    Args:
        message: Incoming message
        user_id: User ID
        user_message: User's message text
    """
    try:
        # Get current schedule
        medications = await schedule_manager.get_user_schedule(user_id)
        schedule = [med.to_dict() for med in medications]
        
        if not schedule:
            await message.answer("У вас нет медикаментов в расписании.")
            return
        
        result = await groq_client.process_time_change_command(user_message, schedule)
        
        status = result.get("status")
        
        if status == "clarification_needed":
            clarification_msg = result.get("message", "Уточните, для какого медикамента вы хотите изменить время.")
            await message.answer(clarification_msg)
            return
        
        medication_id = result.get("medication_id")
        new_times = result.get("new_times", [])
        
        if not medication_id or not new_times:
            await message.answer("Не удалось определить медикамент или новое время. Попробуйте переформулировать.")
            return
        
        # Update medication time
        updated_meds = await schedule_manager.update_medication_time(
            user_id=user_id,
            medication_id=medication_id,
            new_times=new_times
        )
        
        times_str = " и ".join(new_times)
        await message.answer(f"Время приема изменено на {times_str}")
        
        logger.info(f"Updated medication time for user {user_id}: {medication_id} -> {new_times}")
        
    except GroqAPIError as e:
        await message.answer(f"Произошла ошибка при обработке команды: {str(e)}. Попробуйте еще раз.")
    except ValueError as e:
        await message.answer(str(e))
    except Exception as e:
        logger.error(f"Error changing medication time for user {user_id}: {e}")
        await message.answer("Произошла ошибка при изменении времени приема.")


async def handle_dose_change_command(message: Message, user_id: int, user_message: str):
    """Handle dose change command.
    
    Args:
        message: Incoming message
        user_id: User ID
        user_message: User's message text
    """
    try:
        # Get current schedule
        medications = await schedule_manager.get_user_schedule(user_id)
        schedule = [med.to_dict() for med in medications]
        
        if not schedule:
            await message.answer("У вас нет медикаментов в расписании.")
            return
        
        result = await groq_client.process_dose_change_command(user_message, schedule)
        
        status = result.get("status")
        
        if status == "clarification_needed":
            clarification_msg = result.get("message", "Уточните, для какого медикамента вы хотите изменить дозировку.")
            await message.answer(clarification_msg)
            return
        
        medication_id = result.get("medication_id")
        new_dosage = result.get("new_dosage")
        
        if not medication_id or not new_dosage:
            await message.answer("Не удалось определить медикамент или новую дозировку. Попробуйте переформулировать.")
            return
        
        # Update medication dosage
        await schedule_manager.update_medication_dosage(
            user_id=user_id,
            medication_id=medication_id,
            new_dosage=new_dosage
        )
        
        await message.answer(f"Дозировка изменена на {new_dosage}")
        
        logger.info(f"Updated medication dosage for user {user_id}: {medication_id} -> {new_dosage}")
        
    except GroqAPIError as e:
        await message.answer(f"Произошла ошибка при обработке команды: {str(e)}. Попробуйте еще раз.")
    except ValueError as e:
        await message.answer(str(e))
    except Exception as e:
        logger.error(f"Error changing medication dosage for user {user_id}: {e}")
        await message.answer("Произошла ошибка при изменении дозировки.")


async def handle_timezone_change_command(message: Message, user_id: int, user_message: str):
    """Handle timezone change command.
    
    Args:
        message: Incoming message
        user_id: User ID
        user_message: User's message text
    """
    try:
        result = await groq_client.process_timezone_change_command(user_message)
        
        status = result.get("status")
        
        if status == "clarification_needed":
            clarification_msg = result.get("message", "Укажите часовой пояс в виде смещения относительно UTC, например +3 или -5")
            await message.answer(clarification_msg)
            return
        
        timezone_offset = result.get("timezone_offset")
        
        if not timezone_offset:
            await message.answer("Не удалось определить часовой пояс. Попробуйте переформулировать.")
            return
        
        # Update timezone
        await schedule_manager.update_timezone(user_id, timezone_offset)
        
        await message.answer(f"Часовой пояс изменен на {timezone_offset}")
        
        logger.info(f"Updated timezone for user {user_id}: {timezone_offset}")
        
    except GroqAPIError as e:
        await message.answer(f"Произошла ошибка при обработке команды: {str(e)}. Попробуйте еще раз.")
    except Exception as e:
        logger.error(f"Error changing timezone for user {user_id}: {e}")
        await message.answer("Произошла ошибка при изменении часового пояса.")


async def handle_done_command(message: Message, user_id: int, user_message: str):
    """Handle done command - mark medication as taken early.
    
    Args:
        message: Incoming message
        user_id: User ID
        user_message: User's message text
    """
    try:
        # Get current schedule
        medications = await schedule_manager.get_user_schedule(user_id)
        schedule = [med.to_dict() for med in medications]
        
        if not schedule:
            await message.answer("У вас нет медикаментов в расписании.")
            return
        
        result = await groq_client.process_done_command(user_message, schedule)
        
        medication_ids = result.get("medication_ids", [])
        
        if not medication_ids:
            await message.answer("Не удалось определить, какой медикамент вы приняли. Попробуйте переформулировать.")
            return
        
        # If multiple IDs, find the one closest to current time
        if len(medication_ids) > 1:
            from datetime import datetime
            current_time = datetime.now().strftime("%H:%M")
            
            # Find medication closest to current time
            closest_med = None
            min_diff = float('inf')
            
            for med in medications:
                if med.id in medication_ids:
                    # Simple time difference calculation
                    med_minutes = int(med.time.split(':')[0]) * 60 + int(med.time.split(':')[1])
                    curr_minutes = int(current_time.split(':')[0]) * 60 + int(current_time.split(':')[1])
                    diff = abs(med_minutes - curr_minutes)
                    
                    if diff < min_diff:
                        min_diff = diff
                        closest_med = med
            
            if closest_med:
                medication_ids = [closest_med.id]
        
        # Mark medication as taken
        for med_id in medication_ids:
            await schedule_manager.mark_medication_taken(user_id, med_id)
        
        await message.answer("Отмечено как принято ✓")
        
        logger.info(f"Marked medication as taken for user {user_id}: {medication_ids}")
        
    except GroqAPIError as e:
        await message.answer(f"Произошла ошибка при обработке команды: {str(e)}. Попробуйте еще раз.")
    except Exception as e:
        logger.error(f"Error marking medication as done for user {user_id}: {e}")
        await message.answer("Произошла ошибка при отметке приема.")


async def handle_unknown_command(message: Message, user_message: str):
    """Handle unknown command.
    
    Args:
        message: Incoming message
        user_message: User's message text
    """
    try:
        result = await groq_client.process_unknown_command(user_message)
        error_message = result.get("message", "Извините, я не понял вашу команду. Попробуйте переформулировать.")
        await message.answer(error_message)
        
    except GroqAPIError as e:
        await message.answer("Извините, я не понял вашу команду. Попробуйте переформулировать или напишите 'что я принимаю' чтобы увидеть ваше расписание.")
    except Exception as e:
        logger.error(f"Error handling unknown command: {e}")
        await message.answer("Извините, я не понял вашу команду. Попробуйте переформулировать.")


@router.callback_query(F.data.startswith("taken:"))
async def handle_medication_taken_callback(callback: CallbackQuery):
    """Handle callback when user presses 'taken' button.
    
    Args:
        callback: Callback query from inline button
    """
    user_id = callback.from_user.id
    
    try:
        # Parse medication_id from callback_data (format: "taken:123")
        medication_id = int(callback.data.split(":")[1])
        
        log_operation("medication_taken_callback", user_id=user_id, medication_id=medication_id)
        logger.info(f"User {user_id} marked medication {medication_id} as taken")
        
        # Check if medication exists and not already taken
        user_data = await data_manager.get_user_data(user_id)
        if not user_data:
            logger.warning(f"User {user_id} not found in callback handler")
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
        
        medication = user_data.get_medication_by_id(medication_id)
        if not medication:
            logger.warning(
                f"Medication {medication_id} not found for user {user_id}",
                extra={"user_id": user_id, "medication_id": medication_id}
            )
            await callback.answer("Медикамент не найден в расписании", show_alert=True)
            return
        
        # Check if already taken today
        if medication.last_taken:
            from datetime import datetime
            last_taken_date = datetime.fromtimestamp(medication.last_taken).date()
            today = datetime.now().date()
            
            if last_taken_date == today:
                logger.info(f"Medication {medication_id} already taken today by user {user_id}")
                await callback.answer("Вы уже отметили прием этого медикамента", show_alert=True)
                return
        
        # Mark as taken
        await schedule_manager.mark_medication_taken(user_id, medication_id)
        
        # Update message - remove button for this medication
        if callback.message and callback.message.reply_markup:
            # Get current keyboard
            current_keyboard = callback.message.reply_markup.inline_keyboard
            
            # Filter out the button for taken medication
            new_keyboard = []
            for row in current_keyboard:
                new_row = [btn for btn in row if btn.callback_data != callback.data]
                if new_row:
                    new_keyboard.append(new_row)
            
            # If no buttons left, delete message
            if not new_keyboard:
                await callback.message.delete()
                await callback.answer("Все медикаменты приняты ✓")
            else:
                # Update message with new keyboard
                new_markup = InlineKeyboardMarkup(inline_keyboard=new_keyboard)
                await callback.message.edit_reply_markup(reply_markup=new_markup)
                await callback.answer("Отмечено ✓")
        else:
            await callback.answer("Отмечено ✓")
        
        log_operation(
            "medication_marked_taken",
            user_id=user_id,
            medication_id=medication_id,
            medication_name=medication.name
        )
        logger.info(
            f"Successfully marked medication {medication_id} ({medication.name}) "
            f"as taken for user {user_id}"
        )
        
    except ValueError as e:
        logger.error(
            f"Invalid callback_data format: {callback.data}",
            exc_info=True,
            extra={"callback_data": callback.data, "user_id": user_id}
        )
        await callback.answer("Ошибка обработки", show_alert=True)
    except Exception as e:
        logger.error(
            f"Error handling medication taken callback: {type(e).__name__}: {e}",
            exc_info=True,
            extra={"user_id": user_id, "callback_data": callback.data}
        )
        await callback.answer(format_error_for_user(e), show_alert=True)


def increment_reminders_sent():
    """Increment the reminders sent counter."""
    stats["reminders_sent"] += 1
