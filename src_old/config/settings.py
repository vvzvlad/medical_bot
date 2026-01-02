"""Configuration settings for the medication bot."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        """Initialize settings by loading from .env file and environment variables."""
        # Load .env file if it exists
        env_path = Path(__file__).parent.parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)

        # Telegram Bot Configuration
        self.telegram_bot_token: str = self._get_required_env("TELEGRAM_BOT_TOKEN")

        # Groq LLM Configuration
        self.groq_api_key: str = self._get_required_env("GROQ_API_KEY")
        self.groq_model: str = self._get_env("GROQ_MODEL", "openai/gpt-oss-120b")
        self.groq_timeout: int = int(self._get_env("GROQ_TIMEOUT", "30"))
        self.groq_max_retries: int = int(self._get_env("GROQ_MAX_RETRIES", "3"))

        # Application Configuration
        self.log_level: str = self._get_env("LOG_LEVEL", "INFO")
        self.data_dir: Path = Path(self._get_env("DATA_DIR", "data/users"))
        self.scheduler_interval_seconds: int = int(
            self._get_env("SCHEDULER_INTERVAL_SECONDS", "60")
        )
        self.reminder_repeat_interval_hours: int = int(
            self._get_env("REMINDER_REPEAT_INTERVAL_HOURS", "1")
        )

        # Timezone Configuration
        self.default_timezone_offset: str = self._get_env(
            "DEFAULT_TIMEZONE_OFFSET", "+03:00"
        )

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_env(self, key: str, default: Optional[str] = None) -> str:
        """Get environment variable with optional default value.

        Args:
            key: Environment variable name
            default: Default value if variable is not set

        Returns:
            Environment variable value or default
        """
        return os.getenv(key, default)

    def _get_required_env(self, key: str) -> str:
        """Get required environment variable.

        Args:
            key: Environment variable name

        Returns:
            Environment variable value

        Raises:
            ValueError: If required environment variable is not set
        """
        value = os.getenv(key)
        if value is None:
            raise ValueError(
                f"Required environment variable '{key}' is not set. "
                f"Please set it in .env file or system environment."
            )
        return value

    def __repr__(self) -> str:
        """Return string representation of settings (without sensitive data)."""
        return (
            f"Settings("
            f"telegram_bot_token={'*' * 8}, "
            f"groq_api_key={'*' * 8}, "
            f"groq_model={self.groq_model}, "
            f"groq_timeout={self.groq_timeout}, "
            f"groq_max_retries={self.groq_max_retries}, "
            f"log_level={self.log_level}, "
            f"data_dir={self.data_dir}, "
            f"scheduler_interval_seconds={self.scheduler_interval_seconds}, "
            f"reminder_repeat_interval_hours={self.reminder_repeat_interval_hours}, "
            f"default_timezone_offset={self.default_timezone_offset}"
            f")"
        )
