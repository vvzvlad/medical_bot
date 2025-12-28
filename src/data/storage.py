"""Data storage manager for medication bot."""

import json
import os
from pathlib import Path
from typing import Optional

import aiofiles

from src.utils import log_operation, logger

from .models import UserData


class DataManager:
    """Manager for user data storage using JSON files.
    
    Each user has a separate JSON file stored in data/users/{user_id}.json.
    Uses atomic write pattern (write to temp file, then rename) for data integrity.
    """
    
    def __init__(self, data_dir: str = "data/users"):
        """Initialize data manager.
        
        Args:
            data_dir: Directory to store user data files
        """
        self.data_dir = Path(data_dir)
        self._ensure_data_dir()
    
    def _ensure_data_dir(self) -> None:
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Data directory ensured: {self.data_dir}")
    
    def _get_user_file_path(self, user_id: int) -> Path:
        """Get path to user's data file.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Path to user's JSON file
        """
        return self.data_dir / f"{user_id}.json"
    
    def _get_temp_file_path(self, user_id: int) -> Path:
        """Get path to temporary file for atomic writes.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Path to temporary file
        """
        return self.data_dir / f"{user_id}.json.tmp"
    
    def user_exists(self, user_id: int) -> bool:
        """Check if user file exists.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if user file exists, False otherwise
        """
        return self._get_user_file_path(user_id).exists()
    
    async def get_user_data(self, user_id: int) -> Optional[UserData]:
        """Load user data from JSON file.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            UserData instance or None if file doesn't exist
            
        Raises:
            Exception: If file is corrupted (logged and new file created)
        """
        file_path = self._get_user_file_path(user_id)
        
        if not file_path.exists():
            logger.debug(f"User file not found: {user_id}")
            return None
        
        try:
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                user_data = UserData.from_dict(data)
                logger.debug(f"Loaded user data: {user_id}")
                return user_data
                
        except json.JSONDecodeError as e:
            logger.error(
                f"Corrupted JSON file for user {user_id}: {type(e).__name__}: {e}. "
                "Creating new file.",
                exc_info=True,
                extra={"user_id": user_id, "file_path": str(file_path)}
            )
            # Remove corrupted file
            try:
                file_path.unlink()
                log_operation("corrupted_file_removed", user_id=user_id)
            except Exception as unlink_error:
                logger.error(
                    f"Failed to remove corrupted file for user {user_id}: {unlink_error}",
                    exc_info=True
                )
            return None
            
        except Exception as e:
            logger.error(
                f"Error loading user data for {user_id}: {type(e).__name__}: {e}",
                exc_info=True,
                extra={"user_id": user_id, "file_path": str(file_path)}
            )
            raise
    
    async def save_user_data(self, user_data: UserData) -> None:
        """Save user data to JSON file with atomic write.
        
        Uses atomic write pattern: write to temp file, then rename.
        This ensures data integrity even if write is interrupted.
        
        Args:
            user_data: UserData instance to save
            
        Raises:
            Exception: If save operation fails
        """
        user_id = user_data.user_id
        file_path = self._get_user_file_path(user_id)
        temp_path = self._get_temp_file_path(user_id)
        
        try:
            # Write to temporary file
            data = user_data.to_dict()
            json_content = json.dumps(data, ensure_ascii=False, indent=2)
            
            async with aiofiles.open(temp_path, mode="w", encoding="utf-8") as f:
                await f.write(json_content)
            
            # Atomic rename (replaces existing file)
            temp_path.replace(file_path)
            
            logger.debug(f"Saved user data: {user_id}")
            log_operation("user_data_saved", user_id=user_id, medications_count=len(user_data.medications))
            
        except Exception as e:
            logger.error(
                f"Error saving user data for {user_id}: {type(e).__name__}: {e}",
                exc_info=True,
                extra={"user_id": user_id, "file_path": str(file_path)}
            )
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as unlink_error:
                    logger.error(
                        f"Failed to remove temp file for user {user_id}: {unlink_error}",
                        exc_info=True
                    )
            raise
    
    async def create_user(
        self, 
        user_id: int, 
        timezone_offset: str
    ) -> UserData:
        """Create new user file with default data.
        
        Args:
            user_id: Telegram user ID
            timezone_offset: User's timezone offset (e.g., "+03:00")
            
        Returns:
            Created UserData instance
            
        Raises:
            Exception: If user already exists or save fails
        """
        if self.user_exists(user_id):
            logger.warning(f"Attempted to create existing user: {user_id}")
            raise ValueError(f"User {user_id} already exists")
        
        user_data = UserData(
            user_id=user_id,
            timezone_offset=timezone_offset,
            medications=[],
        )
        
        await self.save_user_data(user_data)
        logger.info(f"Created new user: {user_id} with timezone {timezone_offset}")
        
        return user_data
    
    def get_all_user_ids(self) -> list[int]:
        """Get list of all user IDs (for scheduler).
        
        Scans data directory for JSON files and extracts user IDs.
        
        Returns:
            List of user IDs
        """
        user_ids = []
        
        try:
            for file_path in self.data_dir.glob("*.json"):
                # Skip temporary files
                if file_path.suffix == ".tmp" or file_path.name.endswith(".json.tmp"):
                    continue
                
                try:
                    # Extract user_id from filename (e.g., "123456789.json")
                    user_id = int(file_path.stem)
                    user_ids.append(user_id)
                except ValueError:
                    logger.warning(f"Invalid user file name: {file_path.name}")
                    continue
            
            logger.debug(f"Found {len(user_ids)} users")
            return user_ids
            
        except Exception as e:
            logger.error(f"Error getting user IDs: {e}")
            return []
    
    async def delete_user(self, user_id: int) -> bool:
        """Delete user data file.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if file was deleted, False if file didn't exist
        """
        file_path = self._get_user_file_path(user_id)
        
        if not file_path.exists():
            logger.debug(f"User file not found for deletion: {user_id}")
            return False
        
        try:
            file_path.unlink()
            logger.info(f"Deleted user data: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting user data for {user_id}: {e}")
            raise
