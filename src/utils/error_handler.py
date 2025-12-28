"""Error handling utilities for medication bot."""

import functools
from typing import Any, Callable, Optional, TypeVar

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError
from loguru import logger

# Type variable for generic function return type
T = TypeVar('T')


def handle_errors(
    default_return: Any = None,
    notify_user: bool = False,
    log_level: str = "ERROR",
) -> Callable:
    """Decorator for async functions that handles errors gracefully.
    
    Catches all exceptions, logs them with full traceback, and returns
    a default value. Optionally sends error notification to user.
    
    Args:
        default_return: Value to return on error (default: None)
        notify_user: Whether to send error notification to user (default: False)
        log_level: Log level for error messages (default: ERROR)
    
    Returns:
        Decorated function that handles errors
        
    Example:
        @handle_errors(default_return=[], notify_user=True)
        async def get_medications(user_id: int) -> list:
            # Function implementation
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Log error with context
                context = {
                    "function": func.__name__,
                    "args": args,
                    "kwargs": kwargs,
                }
                
                # Log at specified level
                log_func = getattr(logger, log_level.lower(), logger.error)
                log_func(
                    f"Error in {func.__name__}: {type(e).__name__}: {str(e)}",
                    extra=context,
                    exc_info=True,
                )
                
                # Optionally notify user (if message object is in args)
                if notify_user:
                    try:
                        # Try to find message object in args
                        from aiogram.types import Message
                        message = None
                        for arg in args:
                            if isinstance(arg, Message):
                                message = arg
                                break
                        
                        if message:
                            error_msg = format_error_for_user(e)
                            await message.answer(error_msg)
                    except Exception as notify_error:
                        logger.warning(f"Failed to notify user about error: {notify_error}")
                
                return default_return
        
        return wrapper
    return decorator


def format_error_for_user(error: Exception) -> str:
    """Convert technical errors to user-friendly Russian messages.
    
    Handles specific error types and provides appropriate user-facing messages.
    
    Args:
        error: Exception to format
        
    Returns:
        User-friendly error message in Russian
    """
    # Lazy import to avoid circular dependency
    try:
        from src.llm.client import GroqAPIError, GroqInsufficientFundsError, GroqTimeoutError
        
        # LLM API errors
        if isinstance(error, GroqInsufficientFundsError):
            return (
                "Произошла ошибка: недостаточно средств на счету LLM API. "
                "Пожалуйста, попробуйте позже."
            )
        
        if isinstance(error, GroqTimeoutError):
            return (
                "Произошла ошибка: превышено время ожидания ответа от LLM API. "
                "Попробуйте еще раз."
            )
        
        if isinstance(error, GroqAPIError):
            return f"Произошла ошибка при обработке команды: {str(error)}. Попробуйте еще раз."
    except ImportError:
        # If import fails, skip LLM error checks
        pass
    
    # Telegram API errors
    if isinstance(error, TelegramForbiddenError):
        return (
            "Бот не может отправить вам сообщение. "
            "Пожалуйста, проверьте, что вы не заблокировали бота."
        )
    
    if isinstance(error, TelegramBadRequest):
        return "Произошла ошибка при обработке запроса. Попробуйте еще раз."
    
    if isinstance(error, TelegramNetworkError):
        return (
            "Произошла ошибка сети. Проверьте подключение к интернету "
            "и попробуйте еще раз."
        )
    
    if isinstance(error, TelegramAPIError):
        return "Произошла ошибка Telegram API. Попробуйте еще раз."
    
    # Value errors (validation)
    if isinstance(error, ValueError):
        return f"Ошибка валидации: {str(error)}"
    
    # File/data errors
    if isinstance(error, (FileNotFoundError, IOError)):
        return "Произошла ошибка при работе с данными. Попробуйте еще раз."
    
    # JSON errors
    if isinstance(error, (ValueError, KeyError)) and "json" in str(error).lower():
        return "Произошла ошибка при обработке данных. Попробуйте еще раз."
    
    # Generic error
    return "Произошла внутренняя ошибка. Попробуйте еще раз."


def log_operation(
    operation_name: str,
    user_id: Optional[int] = None,
    medication_id: Optional[int] = None,
    **extra_context,
) -> None:
    """Log an operation with structured context.
    
    Args:
        operation_name: Name of the operation being performed
        user_id: User ID (if applicable)
        medication_id: Medication ID (if applicable)
        **extra_context: Additional context to include in log
    """
    context = {
        "operation": operation_name,
    }
    
    if user_id is not None:
        context["user_id"] = user_id
    
    if medication_id is not None:
        context["medication_id"] = medication_id
    
    context.update(extra_context)
    
    logger.info(f"Operation: {operation_name}", extra=context)


def log_performance(
    operation_name: str,
    duration_ms: float,
    user_id: Optional[int] = None,
    **extra_context,
) -> None:
    """Log performance metrics for an operation.
    
    Args:
        operation_name: Name of the operation
        duration_ms: Duration in milliseconds
        user_id: User ID (if applicable)
        **extra_context: Additional context to include in log
    """
    context = {
        "operation": operation_name,
        "duration_ms": duration_ms,
    }
    
    if user_id is not None:
        context["user_id"] = user_id
    
    context.update(extra_context)
    
    # Log as warning if operation is slow
    if duration_ms > 1000:  # More than 1 second
        logger.warning(
            f"Slow operation: {operation_name} took {duration_ms:.2f}ms",
            extra=context,
        )
    else:
        logger.debug(
            f"Performance: {operation_name} took {duration_ms:.2f}ms",
            extra=context,
        )


def sanitize_log_data(data: dict) -> dict:
    """Remove sensitive data from log entries.
    
    Ensures no tokens, API keys, or other sensitive information is logged.
    
    Args:
        data: Dictionary that may contain sensitive data
        
    Returns:
        Sanitized dictionary safe for logging
    """
    sensitive_keys = {
        "token",
        "api_key",
        "password",
        "secret",
        "authorization",
        "bearer",
    }
    
    sanitized = {}
    for key, value in data.items():
        # Check if key contains sensitive information
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_log_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    
    return sanitized


__all__ = [
    "handle_errors",
    "format_error_for_user",
    "log_operation",
    "log_performance",
    "sanitize_log_data",
]
