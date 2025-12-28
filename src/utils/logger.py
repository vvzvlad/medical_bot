"""Logging configuration and utilities for medication bot."""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from src.config import settings


def setup_logger(
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    logs_dir: Optional[Path] = None,
) -> None:
    """Configure loguru logger with console and file outputs.
    
    Sets up structured logging with:
    - Console output with colors and proper formatting
    - File output with daily rotation, 30-day retention, and compression
    - Different log levels for console (INFO) and file (DEBUG)
    - Structured logging format with timestamps, levels, module names
    - Exception tracebacks in logs
    
    Args:
        console_level: Log level for console output (default: INFO)
        file_level: Log level for file output (default: DEBUG)
        logs_dir: Directory for log files (default: project_root/logs)
    """
    # Remove default handler
    logger.remove()
    
    # Console handler with colors and formatting
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
    )
    
    # Ensure logs directory exists
    if logs_dir is None:
        logs_dir = Path(__file__).parent.parent.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # File handler with rotation and compression
    logger.add(
        logs_dir / "bot_{time:YYYY-MM-DD}.log",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
        level=file_level,
        rotation="00:00",  # Rotate at midnight
        retention="30 days",  # Keep logs for 30 days
        compression="zip",  # Compress old logs
        backtrace=True,
        diagnose=True,
        enqueue=True,  # Thread-safe logging
    )
    
    logger.info("Logger configured successfully")
    logger.debug(f"Console log level: {console_level}")
    logger.debug(f"File log level: {file_level}")
    logger.debug(f"Logs directory: {logs_dir}")


def get_logger():
    """Get the configured logger instance.
    
    Returns:
        Configured loguru logger instance
    """
    return logger


# Export logger instance for use across the application
__all__ = ["setup_logger", "get_logger", "logger"]
