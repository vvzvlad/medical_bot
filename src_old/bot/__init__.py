"""Bot module exports."""

from src.bot.bot import (
    get_bot,
    get_data_manager,
    get_groq_client,
    get_schedule_manager,
    init_bot,
    start_polling,
)
from src.bot.handlers import increment_reminders_sent, router

__all__ = [
    "init_bot",
    "start_polling",
    "get_bot",
    "get_data_manager",
    "get_schedule_manager",
    "get_groq_client",
    "router",
    "increment_reminders_sent",
]
