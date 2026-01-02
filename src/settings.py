"""Configuration settings for medication bot."""

import os
from pathlib import Path
from dotenv import load_dotenv


class Settings:
    """Application settings from environment variables."""
    
    def __init__(self):
        # Load .env
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)
        
        # Telegram
        self.telegram_bot_token = self._get_required("TELEGRAM_BOT_TOKEN")
        
        # Groq LLM
        self.groq_api_key = self._get_required("GROQ_API_KEY")
        self.groq_model = self._get("GROQ_MODEL", "openai/gpt-oss-120b")
        self.groq_timeout = int(self._get("GROQ_TIMEOUT", "30"))
        self.groq_max_retries = int(self._get("GROQ_MAX_RETRIES", "3"))
        
        # Application
        self.log_level = self._get("LOG_LEVEL", "INFO")
        self.database_path = Path(self._get("DATABASE_PATH", "data/medications.db"))
        self.scheduler_interval = int(self._get("SCHEDULER_INTERVAL_SECONDS", "60"))
        self.reminder_interval_hours = int(self._get("REMINDER_REPEAT_INTERVAL_HOURS", "1"))
        self.default_timezone = self._get("DEFAULT_TIMEZONE_OFFSET", "+03:00")
        
        # Ensure data directory exists
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _get(self, key: str, default: str) -> str:
        return os.getenv(key, default)
    
    def _get_required(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required env var {key} not set")
        return value


# Global settings instance
settings = Settings()