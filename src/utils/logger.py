"""Logging configuration and utilities for medication bot."""

import sys

from loguru import logger


def setup_logger(
    console_level: str = "INFO",
) -> None:
    """Configure loguru logger with console output only.
    
    Sets up structured logging with:
    - Console output with colors and proper formatting
    - Structured logging format with timestamps, levels, module names
    - Exception tracebacks in logs
    
    Args:
        console_level: Log level for console output (default: INFO)
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
    
    logger.info("Logger configured successfully")
    logger.debug(f"Console log level: {console_level}")


def get_logger():
    """Get the configured logger instance.
    
    Returns:
        Configured loguru logger instance
    """
    return logger


# Export logger instance for use across the application
__all__ = ["setup_logger", "get_logger", "logger"]
