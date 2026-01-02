"""LLM API client for medication bot."""

import httpx
import json
import asyncio
from typing import Dict, Optional
from loguru import logger


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
        json_mode: bool = False
    ) -> str:
        """Send completion request to Groq API.
        
        Args:
            system_prompt: System prompt for the LLM
            user_message: User's message
            temperature: Temperature for generation (default 0.7)
            max_tokens: Maximum tokens to generate (default 500)
            json_mode: Whether to request JSON response (default False)
            
        Returns:
            LLM response content
            
        Raises:
            Exception: If request fails after retries
        """
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
                    
                    logger.debug(f"LLM response: {content[:100]}...")
                    return content
                    
            except httpx.TimeoutException:
                logger.warning(f"LLM timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except httpx.HTTPStatusError as e:
                logger.error(f"LLM HTTP error: {e.response.status_code}")
                if e.response.status_code == 429:  # Rate limit
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
            except Exception as e:
                logger.error(f"LLM error: {e}")
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