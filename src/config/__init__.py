"""Configuration module for the medication bot."""

from .settings import Settings

# Create a singleton settings instance
settings = Settings()

__all__ = ["settings", "Settings"]
