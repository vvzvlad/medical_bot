"""Data models for medication bot."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Medication:
    """Medication data model.
    
    Attributes:
        id: Unique identifier for the medication (incremental)
        name: Name of the medication
        dosage: Dosage information (e.g., "200 мг", "2 таблетки") or None
        time: Time to take medication in HH:MM format (local timezone)
        last_taken: Unix timestamp of last intake or None
        reminder_message_id: ID of last reminder message or None
    """
    
    id: int
    name: str
    dosage: Optional[str]
    time: str
    last_taken: Optional[int] = None
    reminder_message_id: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Convert medication to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the medication
        """
        return {
            "id": self.id,
            "name": self.name,
            "dosage": self.dosage,
            "time": self.time,
            "last_taken": self.last_taken,
            "reminder_message_id": self.reminder_message_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Medication":
        """Create medication from dictionary.
        
        Args:
            data: Dictionary with medication data
            
        Returns:
            Medication instance
        """
        return cls(
            id=data["id"],
            name=data["name"],
            dosage=data.get("dosage"),
            time=data["time"],
            last_taken=data.get("last_taken"),
            reminder_message_id=data.get("reminder_message_id"),
        )


@dataclass
class UserData:
    """User data model.
    
    Attributes:
        user_id: Telegram user ID
        timezone_offset: Timezone offset from UTC (e.g., "+03:00", "-05:00")
        medications: List of user's medications
    """
    
    user_id: int
    timezone_offset: str
    medications: list[Medication] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert user data to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the user data
        """
        return {
            "user_id": self.user_id,
            "timezone_offset": self.timezone_offset,
            "medications": [med.to_dict() for med in self.medications],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserData":
        """Create user data from dictionary.
        
        Args:
            data: Dictionary with user data
            
        Returns:
            UserData instance
        """
        medications = [
            Medication.from_dict(med_data) 
            for med_data in data.get("medications", [])
        ]
        return cls(
            user_id=data["user_id"],
            timezone_offset=data["timezone_offset"],
            medications=medications,
        )
    
    def get_next_medication_id(self) -> int:
        """Get next available medication ID.
        
        Returns:
            Next medication ID (max existing ID + 1, or 1 if no medications)
        """
        if not self.medications:
            return 1
        return max(med.id for med in self.medications) + 1
    
    def add_medication(
        self,
        name: str,
        time: str,
        dosage: Optional[str] = None,
    ) -> Medication:
        """Add new medication to user's list.
        
        Args:
            name: Medication name
            time: Time to take medication (HH:MM format)
            dosage: Optional dosage information
            
        Returns:
            Created medication instance
        """
        medication = Medication(
            id=self.get_next_medication_id(),
            name=name,
            dosage=dosage,
            time=time,
        )
        self.medications.append(medication)
        return medication
    
    def get_medication_by_id(self, medication_id: int) -> Optional[Medication]:
        """Get medication by ID.
        
        Args:
            medication_id: Medication ID
            
        Returns:
            Medication instance or None if not found
        """
        for med in self.medications:
            if med.id == medication_id:
                return med
        return None
    
    def remove_medication(self, medication_id: int) -> bool:
        """Remove medication by ID.
        
        Args:
            medication_id: Medication ID to remove
            
        Returns:
            True if medication was removed, False if not found
        """
        for i, med in enumerate(self.medications):
            if med.id == medication_id:
                self.medications.pop(i)
                return True
        return False
    
    def remove_medications(self, medication_ids: list[int]) -> int:
        """Remove multiple medications by IDs.
        
        Args:
            medication_ids: List of medication IDs to remove
            
        Returns:
            Number of medications removed
        """
        removed_count = 0
        for med_id in medication_ids:
            if self.remove_medication(med_id):
                removed_count += 1
        return removed_count
