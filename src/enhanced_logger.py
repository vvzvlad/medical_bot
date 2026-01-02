"""Enhanced logging utilities for medication bot with detailed context tracking."""

import time
import sys
from contextlib import contextmanager
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from loguru import logger


class EnhancedLogger:
    """Enhanced logger with detailed context tracking and performance monitoring."""
    
    def __init__(self):
        self.user_contexts: Dict[int, Dict[str, Any]] = {}
        self.operation_timers: Dict[str, float] = {}
    
    def set_user_context(self, user_id: int, context: Dict[str, Any]):
        """Set user context for detailed logging."""
        self.user_contexts[user_id] = {
            'user_id': user_id,
            'username': context.get('username', 'unknown'),
            'first_name': context.get('first_name', ''),
            'last_name': context.get('last_name', ''),
            'timezone': context.get('timezone', 'unknown'),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_user_context(self, user_id: int) -> Dict[str, Any]:
        """Get user context for logging."""
        return self.user_contexts.get(user_id, {
            'user_id': user_id,
            'username': 'unknown',
            'first_name': '',
            'last_name': '',
            'timezone': 'unknown'
        })
    
    def clear_user_context(self, user_id: int):
        """Clear user context."""
        self.user_contexts.pop(user_id, None)
    
    @contextmanager
    def timer(self, operation: str, user_id: Optional[int] = None, **context):
        """Context manager for timing operations with detailed logging."""
        start_time = time.time()
        operation_id = f"{operation}_{user_id}_{start_time}"
        self.operation_timers[operation_id] = start_time
        
        user_info = ""
        if user_id:
            user_context = self.get_user_context(user_id)
            user_info = f"User: {user_context['first_name']} {user_context['last_name']} (ID: {user_id}, @{user_context['username']}) | "
        
        logger.info(f"🚀 START {operation} | {user_info}Context: {context}")
        
        try:
            yield
        finally:
            end_time = time.time()
            duration = end_time - start_time
            duration_ms = duration * 1000
            
            status = "✅ COMPLETED" if duration < 30 else "⚠️  SLOW"
            logger.info(f"{status} {operation} | {user_info}Duration: {duration_ms:.2f}ms | Context: {context}")
            
            self.operation_timers.pop(operation_id, None)
    
    def log_user_message(self, user_id: int, message_text: str, message_type: str = "incoming"):
        """Log user message with detailed context."""
        user_context = self.get_user_context(user_id)
        
        if message_type == "incoming":
            logger.info(f"📨 INCOMING MESSAGE | User: {user_context['first_name']} {user_context['last_name']} (ID: {user_id}, @{user_context['username']}) | Text: '{message_text}' | Timezone: {user_context['timezone']}")
        else:
            logger.info(f"📤 OUTGOING MESSAGE | User: {user_context['first_name']} {user_context['last_name']} (ID: {user_id}, @{user_context['username']}) | Text: '{message_text}'")
    
    def log_llm_classification(self, user_id: int, user_message: str, classification: str, confidence: Optional[float] = None, processing_time: Optional[float] = None):
        """Log LLM classification results."""
        user_context = self.get_user_context(user_id)
        time_info = f" | Processing time: {processing_time*1000:.2f}ms" if processing_time else ""
        confidence_info = f" | Confidence: {confidence:.2f}" if confidence else ""
        
        logger.info(f"🤖 LLM CLASSIFICATION | User: {user_context['first_name']} {user_context['last_name']} (ID: {user_id}){time_info}{confidence_info} | Message: '{user_message}' → Classified as: {classification}")
    
    def log_llm_parsing(self, operation: str, user_id: int, user_message: str, parsed_data: Any, processing_time: Optional[float] = None):
        """Log LLM parsing results."""
        user_context = self.get_user_context(user_id)
        time_info = f" | Processing time: {processing_time*1000:.2f}ms" if processing_time else ""
        
        logger.info(f"🔍 LLM PARSING {operation.upper()} | User: {user_context['first_name']} {user_context['last_name']} (ID: {user_id}){time_info} | Message: '{user_message}' → Parsed: {parsed_data}")
    
    def log_database_operation(self, operation: str, user_id: int, table: str, data: Any, affected_rows: Optional[int] = None, operation_time: Optional[float] = None):
        """Log database operations with detailed context."""
        user_context = self.get_user_context(user_id)
        time_info = f" | DB time: {operation_time*1000:.2f}ms" if operation_time else ""
        rows_info = f" | Affected rows: {affected_rows}" if affected_rows is not None else ""
        
        logger.info(f"💾 DATABASE {operation.upper()} | User: {user_context['first_name']} {user_context['last_name']} (ID: {user_id}){time_info}{rows_info} | Table: {table} | Data: {data}")
    
    def log_telegram_api_call(self, operation: str, user_id: int, message_data: Dict[str, Any], response_data: Any = None, api_time: Optional[float] = None):
        """Log Telegram API calls."""
        user_context = self.get_user_context(user_id)
        time_info = f" | API time: {api_time*1000:.2f}ms" if api_time else ""
        
        if response_data:
            logger.info(f"📱 TELEGRAM API {operation.upper()} | User: {user_context['first_name']} {user_context['last_name']} (ID: {user_id}){time_info} | Request: {message_data} → Response: {response_data}")
        else:
            logger.info(f"📱 TELEGRAM API {operation.upper()} | User: {user_context['first_name']} {user_context['last_name']} (ID: {user_id}){time_info} | Request: {message_data}")
    
    def log_scheduler_operation(self, operation: str, user_id: int, medication_data: Dict[str, Any], reason: str = "", scheduled_time: Optional[str] = None):
        """Log scheduler operations."""
        user_context = self.get_user_context(user_id)
        time_info = f" | Scheduled time: {scheduled_time}" if scheduled_time else ""
        
        logger.info(f"⏰ SCHEDULER {operation.upper()} | User: {user_context['first_name']} {user_context['last_name']} (ID: {user_id}){time_info} | Medication: {medication_data.get('name', 'unknown')} | Reason: {reason}")
    
    def log_error(self, error_type: str, user_id: Optional[int] = None, error_message: str = "", context: Optional[Dict[str, Any]] = None):
        """Log errors with detailed context."""
        user_info = ""
        if user_id:
            user_context = self.get_user_context(user_id)
            user_info = f"User: {user_context['first_name']} {user_context['last_name']} (ID: {user_id}, @{user_context['username']}) | "
        
        context_info = f"Context: {context}" if context else ""
        
        logger.error(f"❌ ERROR {error_type.upper()} | {user_info}{error_message} | {context_info}")
    
    def log_warning(self, warning_type: str, user_id: Optional[int] = None, warning_message: str = "", context: Optional[Dict[str, Any]] = None):
        """Log warnings with detailed context."""
        user_info = ""
        if user_id:
            user_context = self.get_user_context(user_id)
            user_info = f"User: {user_context['first_name']} {user_context['last_name']} (ID: {user_id}) | "
        
        context_info = f"Context: {context}" if context else ""
        
        logger.warning(f"⚠️  WARNING {warning_type.upper()} | {user_info}{warning_message} | {context_info}")
    
    def log_info(self, operation: str, user_id: Optional[int] = None, message: str = "", **kwargs):
        """General info logging with optional user context."""
        user_info = ""
        if user_id:
            user_context = self.get_user_context(user_id)
            user_info = f"User: {user_context['first_name']} {user_context['last_name']} (ID: {user_id}) | "
        
        extra_info = " | ".join([f"{k}: {v}" for k, v in kwargs.items() if v is not None])
        extra_info = f" | {extra_info}" if extra_info else ""
        
        logger.info(f"ℹ️  INFO {operation.upper()} | {user_info}{message}{extra_info}")


# Global enhanced logger instance
enhanced_logger = EnhancedLogger()


def setup_enhanced_logger(console_level: str = "INFO"):
    """Setup enhanced logger with detailed formatting."""
    # Remove default handler
    logger.remove()
    
    # Console handler with enhanced formatting
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level=console_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
        serialize=False
    )
    
    logger.info("Enhanced logger configured successfully")
    return enhanced_logger


def get_enhanced_logger():
    """Get the enhanced logger instance."""
    return enhanced_logger