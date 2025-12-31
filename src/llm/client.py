"""Groq LLM API client for command processing."""

import asyncio
import json
from typing import Any, Dict, List, Optional

import httpx

from src.config import settings
from src.llm import prompts
from src.utils import log_operation, log_performance, logger, sanitize_log_data


class GroqAPIError(Exception):
    """Base exception for Groq API errors."""
    pass


class GroqTimeoutError(GroqAPIError):
    """Raised when Groq API request times out."""
    pass


class GroqRateLimitError(GroqAPIError):
    """Raised when Groq API rate limit is exceeded."""
    pass


class GroqInsufficientFundsError(GroqAPIError):
    """Raised when Groq API account has insufficient funds."""
    pass


class GroqClient:
    """Client for interacting with Groq LLM API."""
    
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    def __init__(self):
        """Initialize Groq client with settings."""
        self.api_key = settings.groq_api_key
        self.model = settings.groq_model
        self.timeout = settings.groq_timeout
        self.max_retries = settings.groq_max_retries
        
    async def _make_request(
        self,
        prompt: str,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """Make request to Groq API with retry logic.
        
        Args:
            prompt: System prompt for the LLM
            retry_count: Current retry attempt number
            
        Returns:
            Parsed JSON response from LLM
            
        Raises:
            GroqTimeoutError: If request times out after all retries
            GroqRateLimitError: If rate limit is exceeded
            GroqInsufficientFundsError: If account has insufficient funds
            GroqAPIError: For other API errors
        """
        import time
        start_time = time.time()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Sanitize payload for logging (remove API key)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        try:
            async with httpx.AsyncClient() as client:
                logger.debug(
                    f"Making request to Groq API (attempt {retry_count + 1}/{self.max_retries + 1})",
                    extra={"model": self.model, "prompt_length": len(prompt)}
                )
                logger.debug(f"Prompt preview: {prompt[:200]}...")
                
                response = await client.post(
                    self.API_URL,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Handle HTTP errors
                if response.status_code == 429:
                    logger.warning(
                        "Groq API rate limit exceeded",
                        extra={"retry_count": retry_count, "duration_ms": duration_ms}
                    )
                    raise GroqRateLimitError("Rate limit exceeded")
                    
                elif response.status_code == 402:
                    logger.error(
                        "Groq API insufficient funds",
                        extra={"duration_ms": duration_ms}
                    )
                    raise GroqInsufficientFundsError("Insufficient funds on Groq account")
                    
                elif response.status_code >= 400:
                    error_text = response.text
                    logger.error(
                        f"Groq API error {response.status_code}: {error_text}",
                        extra={"status_code": response.status_code, "duration_ms": duration_ms}
                    )
                    raise GroqAPIError(f"API error {response.status_code}: {error_text}")
                
                # Parse response
                response_data = response.json()
                content = response_data["choices"][0]["message"]["content"]
                
                logger.debug(f"Groq API response: {content[:200]}...")
                log_performance("groq_api_request", duration_ms)
                
                # Parse JSON from content
                try:
                    result = json.loads(content)
                    return result
                except json.JSONDecodeError as e:
                    logger.error(
                        f"Failed to parse JSON from LLM response: {content}",
                        exc_info=True,
                        extra={"response_preview": content[:500]}
                    )
                    raise GroqAPIError(f"Invalid JSON response from LLM: {e}")
                    
        except httpx.TimeoutException as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.warning(
                f"Groq API timeout (attempt {retry_count + 1}/{self.max_retries + 1})",
                extra={"duration_ms": duration_ms, "timeout": self.timeout}
            )
            
            # Retry with exponential backoff
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count  # Exponential backoff: 1s, 2s, 4s
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                return await self._make_request(prompt, retry_count + 1)
            else:
                logger.error(
                    "Groq API timeout after all retries",
                    extra={"total_retries": self.max_retries, "total_duration_ms": duration_ms}
                )
                raise GroqTimeoutError("Request timed out after all retries")
                
        except httpx.RequestError as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Groq API request error: {type(e).__name__}: {e}",
                exc_info=True,
                extra={"duration_ms": duration_ms, "retry_count": retry_count}
            )
            
            # Retry on network errors
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                return await self._make_request(prompt, retry_count + 1)
            else:
                logger.error(
                    f"Request failed after all retries: {e}",
                    extra={"total_retries": self.max_retries}
                )
                raise GroqAPIError(f"Request failed after all retries: {e}")
    
    async def detect_command_type(self, user_message: str) -> str:
        """Detect command type from user message (first stage).
        
        Args:
            user_message: User's message text
            
        Returns:
            Command type string (add, delete, time_change, etc.)
            
        Raises:
            GroqAPIError: If API request fails
        """
        logger.info(f"Detecting command type for message: {user_message}")
        
        prompt = prompts.get_command_detection_prompt(user_message)
        result = await self._make_request(prompt)
        
        command_type = result.get("command_type", "unknown")
        logger.info(f"Detected command type: {command_type}")
        
        return command_type
    
    async def process_add_command(self, user_message: str) -> List[Dict[str, Any]]:
        """Parse add medication command (second stage).
        
        Args:
            user_message: User's message text
            
        Returns:
            List of dicts, each with medication_name, times, and optionally dosage
            Example single: [{"medication_name": "Аспирин", "times": ["19:00"], "dosage": "200 мг"}]
            Example multiple: [{"medication_name": "Аспирин", "times": ["12:00"]}, {"medication_name": "Лоперамид", "times": ["12:00"]}]
            
        Raises:
            GroqAPIError: If API request fails
        """
        logger.info(f"Processing add command: {user_message}")
        
        prompt = prompts.get_add_command_prompt(user_message)
        result = await self._make_request(prompt)
        
        logger.info(f"Add command result: {result}")
        return result
    
    async def process_delete_command(
        self,
        user_message: str,
        schedule: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Parse delete medication command (second stage).
        
        Args:
            user_message: User's message text
            schedule: Current medication schedule with IDs
            
        Returns:
            Dict with status and either medication_ids or clarification message
            Example success: {"status": "success", "medication_ids": [1, 3]}
            Example clarification: {"status": "clarification_needed", "message": "..."}
            
        Raises:
            GroqAPIError: If API request fails
        """
        logger.info(f"Processing delete command: {user_message}")
        
        prompt = prompts.get_delete_command_prompt(user_message, schedule)
        result = await self._make_request(prompt)
        
        logger.info(f"Delete command result: {result}")
        return result
    
    async def process_time_change_command(
        self,
        user_message: str,
        schedule: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Parse time change command (second stage).
        
        Args:
            user_message: User's message text
            schedule: Current medication schedule with IDs
            
        Returns:
            Dict with status and either medication_id/new_times or clarification message
            Example success: {"status": "success", "medication_id": 1, "new_times": ["19:00"]}
            Example clarification: {"status": "clarification_needed", "message": "..."}
            
        Raises:
            GroqAPIError: If API request fails
        """
        logger.info(f"Processing time change command: {user_message}")
        
        prompt = prompts.get_time_change_command_prompt(user_message, schedule)
        result = await self._make_request(prompt)
        
        logger.info(f"Time change command result: {result}")
        return result
    
    async def process_dose_change_command(
        self,
        user_message: str,
        schedule: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Parse dose change command (second stage).
        
        Args:
            user_message: User's message text
            schedule: Current medication schedule with IDs
            
        Returns:
            Dict with status and either medication_id/new_dosage or clarification message
            Example success: {"status": "success", "medication_id": 1, "new_dosage": "300 мг"}
            Example clarification: {"status": "clarification_needed", "message": "..."}
            
        Raises:
            GroqAPIError: If API request fails
        """
        logger.info(f"Processing dose change command: {user_message}")
        
        prompt = prompts.get_dose_change_command_prompt(user_message, schedule)
        result = await self._make_request(prompt)
        
        logger.info(f"Dose change command result: {result}")
        return result
    
    async def process_timezone_change_command(self, user_message: str) -> Dict[str, Any]:
        """Parse timezone change command (second stage).
        
        Args:
            user_message: User's message text
            
        Returns:
            Dict with status and either timezone_offset or clarification message
            Example success: {"status": "success", "timezone_offset": "+03:00"}
            Example clarification: {"status": "clarification_needed", "message": "..."}
            
        Raises:
            GroqAPIError: If API request fails
        """
        logger.info(f"Processing timezone change command: {user_message}")
        
        prompt = prompts.get_timezone_change_command_prompt(user_message)
        result = await self._make_request(prompt)
        
        logger.info(f"Timezone change command result: {result}")
        return result
    
    async def process_done_command(
        self,
        user_message: str,
        schedule: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Parse done (early medication intake) command (second stage).
        
        Args:
            user_message: User's message text
            schedule: Current medication schedule with IDs
            
        Returns:
            Dict with medication_ids list
            Example: {"medication_ids": [1, 3]}
            
        Raises:
            GroqAPIError: If API request fails
        """
        logger.info(f"Processing done command: {user_message}")
        
        prompt = prompts.get_done_command_prompt(user_message, schedule)
        result = await self._make_request(prompt)
        
        logger.info(f"Done command result: {result}")
        return result
    
    async def process_help_command(self) -> Dict[str, Any]:
        """Generate help message for user (second stage).
        
        Returns:
            Dict with help message
            Example: {"message": "Привет! Я помогу вам управлять расписанием..."}
            
        Raises:
            GroqAPIError: If API request fails
        """
        logger.info("Processing help command")
        
        prompt = prompts.get_help_command_prompt()
        result = await self._make_request(prompt)
        
        logger.info(f"Help command result: {result}")
        return result
    
    async def process_unknown_command(self, user_message: str) -> Dict[str, Any]:
        """Generate error message for unknown command (second stage).
        
        Args:
            user_message: User's message text
            
        Returns:
            Dict with error message
            Example: {"message": "Извините, я не понял вашу команду..."}
            
        Raises:
            GroqAPIError: If API request fails
        """
        logger.info(f"Processing unknown command: {user_message}")
        
        prompt = prompts.get_unknown_command_prompt(user_message)
        result = await self._make_request(prompt)
        
        logger.info(f"Unknown command result: {result}")
        return result
