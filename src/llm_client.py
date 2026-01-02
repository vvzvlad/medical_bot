"""LLM API client for medication bot."""

import httpx
import json
import asyncio
import time
from typing import Dict, Optional
from loguru import logger
from src.enhanced_logger import get_enhanced_logger

# Initialize enhanced logger
enhanced_logger = get_enhanced_logger()


class LLMClient:
    def __init__(self, api_key: str, model: str, timeout: int = 30, max_retries: int = 3):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
    
    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        json_mode: bool = False,
        user_id: Optional[int] = None
    ) -> str:
        """Send completion request to Groq API.
        
        Args:
            system_prompt: System prompt for the LLM
            user_message: User's message
            temperature: Temperature for generation (default 0.7)
            max_tokens: Maximum tokens to generate (default 500)
            json_mode: Whether to request JSON response (default False)
            user_id: Optional user ID for context logging
            
        Returns:
            LLM response content
            
        Raises:
            Exception: If request fails after retries
        """
        start_time = time.time()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.base_url,
                        headers=headers,
                        json=payload
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    api_time = time.time() - start_time
                    
                    # Log successful API call with essential debugging info
                    enhanced_logger.log_info(
                        "LLM_API_SUCCESS",
                        user_id=user_id,
                        message=f"Model: {self.model}, Attempt: {attempt + 1}",
                        api_time=f"{api_time:.2f}s"
                    )
                    
                    return content
                    
            except httpx.TimeoutException:
                enhanced_logger.log_warning(
                    "LLM_API_TIMEOUT",
                    user_id=user_id,
                    warning_message=f"Timeout on attempt {attempt + 1}/{self.max_retries}",
                    context={"model": self.model, "max_tokens": max_tokens}
                )
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except httpx.HTTPStatusError as e:
                enhanced_logger.log_error(
                    "LLM_API_HTTP_ERROR",
                    user_id=user_id,
                    error_message=f"HTTP {e.response.status_code} on attempt {attempt + 1}",
                    context={"model": self.model, "status_code": e.response.status_code}
                )
                if e.response.status_code == 429:  # Rate limit
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                elif e.response.status_code == 400:  # Bad request - likely prompt issue
                    if attempt < self.max_retries - 1:
                        enhanced_logger.log_warning(
                            "LLM_API_BAD_REQUEST_RETRY",
                            user_id=user_id,
                            warning_message=f"Retrying after 400 error on attempt {attempt + 1}"
                        )
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        raise
                else:
                    raise
            except Exception as e:
                enhanced_logger.log_error(
                    "LLM_API_ERROR",
                    user_id=user_id,
                    error_message=f"General error on attempt {attempt + 1}: {str(e)}",
                    context={"model": self.model, "error_type": type(e).__name__}
                )
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        raise Exception("LLM request failed after retries")
    
    async def complete_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Dict:
        """Request JSON response and parse it.
        
        Args:
            system_prompt: System prompt for the LLM
            user_message: User's message
            temperature: Temperature for generation (default 0.7)
            max_tokens: Maximum tokens to generate (default 500)
            
        Returns:
            Parsed JSON response
            
        Raises:
            json.JSONDecodeError: If response is not valid JSON
            Exception: If request fails
        """
        content = await self.complete(
            system_prompt, 
            user_message,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True
        )
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {content}")
            raise