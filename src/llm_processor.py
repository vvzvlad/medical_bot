"""LLM processing logic for medication bot."""

import time
from typing import Dict, List, Optional
from loguru import logger
from src.enhanced_logger import get_enhanced_logger
from src.llm_client import LLMClient
from src.prompts import (
    get_command_detection_prompt,
    get_add_command_prompt,
    get_delete_command_prompt,
    get_done_command_prompt,
    get_time_change_command_prompt,
    get_dose_change_command_prompt,
    get_timezone_change_command_prompt,
    get_unknown_command_prompt,
    get_help_command_prompt,
    get_confirmation_message_prompt
)

# Initialize enhanced logger
enhanced_logger = get_enhanced_logger()


class LLMProcessor:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    async def classify_intent(self, user_message: str, user_id: Optional[int] = None) -> str:
        """Stage 1: Classify command type.
        
        Args:
            user_message: User's message text
            user_id: Optional user ID for context logging
            
        Returns:
            Command type string
        """
        start_time = time.time()
        
        prompt = get_command_detection_prompt(user_message)
        response = await self.llm.complete_json(prompt, user_message)
        
        processing_time = time.time() - start_time
        command_type = response.get("command_type", "unknown")
        
        # Log classification with detailed context
        enhanced_logger.log_llm_classification(
            user_id=user_id,
            user_message=user_message,
            classification=command_type,
            processing_time=processing_time
        )
        
        return command_type
    
    async def process_add(self, user_message: str, user_id: Optional[int] = None) -> List[Dict]:
        """Parse ADD command.
        
        Args:
            user_message: User's message text
            user_id: Optional user ID for context logging
            
        Returns:
            List of medication dictionaries with name, times, and optional dosage
        """
        start_time = time.time()
        
        prompt = get_add_command_prompt(user_message)
        response = await self.llm.complete_json(prompt, user_message)
        
        processing_time = time.time() - start_time
        
        # Expected: [{"medication_name": "...", "times": [...], "dosage": "..."}]
        medications = response if isinstance(response, list) else [response]
        
        # Log parsing results with detailed format information for debugging
        for i, med in enumerate(medications):
            if isinstance(med, dict) and 'times' in med:
                times_data = med['times']
                enhanced_logger.log_info(
                    "LLM_PARSING_DETAILS",
                    user_id=user_id,
                    message=f"Medication {i+1}: {med.get('medication_name', 'unknown')}",
                    times_count=len(times_data) if isinstance(times_data, list) else 0,
                    times_type=type(times_data).__name__,
                    first_time_sample=str(times_data[0]) if times_data and isinstance(times_data, list) else "empty",
                    first_time_type=type(times_data[0]).__name__ if times_data and isinstance(times_data, list) else "N/A"
                )
        
        # Log parsing results
        enhanced_logger.log_llm_parsing(
            operation="add",
            user_id=user_id,
            user_message=user_message,
            parsed_data=medications,
            processing_time=processing_time
        )
        
        return medications
    
    async def process_done(
        self, 
        user_message: str, 
        user_schedule: List[Dict]
    ) -> Dict:
        """Parse DONE command with schedule context.
        
        Args:
            user_message: User's message text
            user_schedule: User's current medication schedule
            
        Returns:
            Dictionary with medication_ids, name, and optional time
        """
        prompt = get_done_command_prompt(user_message, user_schedule)
        response = await self.llm.complete_json(prompt, user_message)
        
        # Expected: {"medication_name": "...", "time": "...", "medication_ids": [...]}
        return response
    
    async def process_delete(
        self,
        user_message: str,
        user_schedule: List[Dict]
    ) -> Dict:
        """Parse DELETE command.
        
        Args:
            user_message: User's message text
            user_schedule: User's current medication schedule
            
        Returns:
            Dictionary with status, medication_name, and medication_ids
        """
        prompt = get_delete_command_prompt(user_message, user_schedule)
        response = await self.llm.complete_json(prompt, user_message)
        
        # Expected: {"status": "...", "medication_name": "...", "medication_ids": [...]}
        return response
    
    async def process_time_change(
        self,
        user_message: str,
        user_schedule: List[Dict]
    ) -> Dict:
        """Parse TIME_CHANGE command.
        
        Args:
            user_message: User's message text
            user_schedule: User's current medication schedule
            
        Returns:
            Dictionary with status, medication_name, medication_id, and new_times
        """
        prompt = get_time_change_command_prompt(user_message, user_schedule)
        response = await self.llm.complete_json(prompt, user_message)
        return response
    
    async def process_dose_change(
        self,
        user_message: str,
        user_schedule: List[Dict]
    ) -> Dict:
        """Parse DOSE_CHANGE command.
        
        Args:
            user_message: User's message text
            user_schedule: User's current medication schedule
            
        Returns:
            Dictionary with status, medication_name, medication_id, and new_dosage
        """
        prompt = get_dose_change_command_prompt(user_message, user_schedule)
        response = await self.llm.complete_json(prompt, user_message)
        return response
    
    async def process_timezone_change(self, user_message: str) -> Dict:
        """Parse TIMEZONE_CHANGE command.
        
        Args:
            user_message: User's message text
            
        Returns:
            Dictionary with status and timezone_offset
        """
        prompt = get_timezone_change_command_prompt(user_message)
        response = await self.llm.complete_json(prompt, user_message)
        return response
    
    async def process_unknown(self, user_message: str) -> Dict:
        """Handle UNKNOWN command.
        
        Args:
            user_message: User's message text
            
        Returns:
            Dictionary with error message
        """
        prompt = get_unknown_command_prompt(user_message)
        response = await self.llm.complete_json(prompt, user_message)
        return response
    
    async def process_help(self) -> Dict:
        """Handle HELP command.
        
        Returns:
            Dictionary with help message
        """
        prompt = get_help_command_prompt()
        response = await self.llm.complete_json(prompt, "")
        return response
    
    async def generate_confirmation_message(
        self, 
        medication_name: str, 
        medication_time: Optional[str] = None, 
        dosage: Optional[str] = None
    ) -> Dict:
        """Generate personalized confirmation message.
        
        Args:
            medication_name: Name of medication taken
            medication_time: Time when taken (optional)
            dosage: Dosage information (optional)
            
        Returns:
            Dictionary with confirmation message
        """
        prompt = get_confirmation_message_prompt(medication_name, medication_time, dosage)
        response = await self.llm.complete_json(prompt, "")
        return response