"""Database operations for medication bot."""

import aiosqlite
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
    
    async def init(self):
        """Initialize database with schema."""
        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for better concurrency
            await db.execute("PRAGMA journal_mode=WAL")
            
            # Create tables
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    timezone_offset TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS medications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    dosage TEXT,
                    time TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    UNIQUE(user_id, name, time),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS intake_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    medication_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    taken_at INTEGER,
                    reminder_message_id INTEGER,
                    reminder_sent_at INTEGER,
                    UNIQUE(user_id, medication_id, date),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (medication_id) REFERENCES medications(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_medications_user_time "
                "ON medications(user_id, time)"
            )
            
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_intake_status_user_date "
                "ON intake_status(user_id, date)"
            )
            
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_intake_status_reminder "
                "ON intake_status(reminder_message_id) "
                "WHERE reminder_message_id IS NOT NULL"
            )
            
            await db.commit()
    
    async def create_user(self, user_id: int, timezone_offset: str):
        """Create new user.
        
        Args:
            user_id: Telegram user ID
            timezone_offset: User's timezone offset like '+03:00'
        """
        now = int(datetime.utcnow().timestamp())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, timezone_offset, created_at, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (user_id, timezone_offset, now, now)
            )
            await db.commit()
    
    async def update_user_timezone(self, user_id: int, timezone_offset: str) -> bool:
        """Update user's timezone.
        
        Args:
            user_id: Telegram user ID
            timezone_offset: New timezone offset like '+03:00'
            
        Returns:
            True if updated successfully, False otherwise
        """
        now = int(datetime.utcnow().timestamp())
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE users SET timezone_offset = ?, updated_at = ? WHERE user_id = ?",
                (timezone_offset, now, user_id)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user data.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User data dictionary or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def add_medication(
        self, 
        user_id: int, 
        name: str, 
        time: str, 
        dosage: Optional[str] = None
    ) -> Optional[int]:
        """Add medication. Returns medication_id or None if duplicate.
        
        Args:
            user_id: Telegram user ID
            name: Medication name
            time: Medication time in HH:MM format
            dosage: Optional dosage information
            
        Returns:
            Medication ID if added, None if duplicate
        """
        now = int(datetime.utcnow().timestamp())
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute(
                    "INSERT INTO medications (user_id, name, dosage, time, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user_id, name.lower(), dosage, time, now)
                )
                await db.commit()
                return cursor.lastrowid
            except aiosqlite.IntegrityError:
                # Duplicate (user_id, name, time)
                return None
    
    async def check_duplicate(self, user_id: int, name: str, time: str) -> bool:
        """Check if medication already exists.
        
        Args:
            user_id: Telegram user ID
            name: Medication name
            time: Medication time in HH:MM format
            
        Returns:
            True if duplicate exists, False otherwise
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM medications "
                "WHERE user_id = ? AND name = ? AND time = ?",
                (user_id, name.lower(), time)
            )
            count = (await cursor.fetchone())[0]
            return count > 0
    
    async def get_medications(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all user medications.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of medication dictionaries
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM medications WHERE user_id = ? ORDER BY time",
                (user_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_medication(self, medication_id: int) -> Optional[Dict[str, Any]]:
        """Get specific medication.
        
        Args:
            medication_id: Medication ID
            
        Returns:
            Medication dictionary or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM medications WHERE id = ?",
                (medication_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def delete_medication(self, medication_id: int) -> bool:
        """Delete medication.
        
        Args:
            medication_id: Medication ID
            
        Returns:
            True if deleted, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM medications WHERE id = ?",
                (medication_id,)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def delete_medications(self, medication_ids: List[int]) -> int:
        """Delete multiple medications.
        
        Args:
            medication_ids: List of medication IDs
            
        Returns:
            Number of medications deleted
        """
        if not medication_ids:
            return 0
            
        placeholders = ','.join('?' * len(medication_ids))
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"DELETE FROM medications WHERE id IN ({placeholders})",
                medication_ids
            )
            await db.commit()
            return cursor.rowcount
    
    async def update_medication_time(self, medication_id: int, new_time: str) -> bool:
        """Update medication time.
        
        Args:
            medication_id: Medication ID
            new_time: New time in HH:MM format
            
        Returns:
            True if updated, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE medications SET time = ? WHERE id = ?",
                (new_time, medication_id)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def update_medication_dosage(self, medication_id: int, new_dosage: str) -> bool:
        """Update medication dosage.
        
        Args:
            medication_id: Medication ID
            new_dosage: New dosage
            
        Returns:
            True if updated, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE medications SET dosage = ? WHERE id = ?",
                (new_dosage, medication_id)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def get_intake_status(
        self, 
        user_id: int, 
        medication_id: int, 
        date: str
    ) -> Optional[Dict[str, Any]]:
        """Get intake status for medication on specific date.
        
        Args:
            user_id: Telegram user ID
            medication_id: Medication ID
            date: Date in YYYY-MM-DD format
            
        Returns:
            Intake status dictionary or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM intake_status WHERE user_id = ? AND medication_id = ? AND date = ?",
                (user_id, medication_id, date)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def create_intake_status(
        self,
        user_id: int,
        medication_id: int,
        date: str,
        reminder_message_id: Optional[int] = None
    ) -> int:
        """Create intake status record.
        
        Args:
            user_id: Telegram user ID
            medication_id: Medication ID
            date: Date in YYYY-MM-DD format
            reminder_message_id: Optional Telegram message ID
            
        Returns:
            ID of created intake status record
        """
        now = int(datetime.utcnow().timestamp())
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO intake_status "
                "(user_id, medication_id, date, reminder_message_id, reminder_sent_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, medication_id, date, reminder_message_id, now)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def mark_as_taken(
        self, 
        user_id: int, 
        medication_id: int, 
        date: str, 
        taken_at: int
    ) -> bool:
        """Mark medication as taken.
        
        Args:
            user_id: Telegram user ID
            medication_id: Medication ID
            date: Date in YYYY-MM-DD format
            taken_at: Unix timestamp when taken
            
        Returns:
            True if updated, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE intake_status SET taken_at = ? WHERE user_id = ? AND medication_id = ? AND date = ?",
                (taken_at, user_id, medication_id, date)
            )
            await db.commit()
            # If no rows were updated, try to insert
            if cursor.rowcount == 0:
                try:
                    await db.execute(
                        "INSERT INTO intake_status (user_id, medication_id, date, taken_at) "
                        "VALUES (?, ?, ?, ?)",
                        (user_id, medication_id, date, taken_at)
                    )
                    await db.commit()
                    return True
                except aiosqlite.IntegrityError:
                    # Race condition - another process inserted first
                    # Try update again
                    cursor = await db.execute(
                        "UPDATE intake_status SET taken_at = ? WHERE user_id = ? AND medication_id = ? AND date = ?",
                        (taken_at, user_id, medication_id, date)
                    )
                    await db.commit()
                    return cursor.rowcount > 0
            return cursor.rowcount > 0
    
    async def set_reminder_message_id(
        self,
        user_id: int,
        medication_id: int,
        date: str,
        message_id: int
    ) -> bool:
        """Set reminder message ID.
        
        Args:
            user_id: Telegram user ID
            medication_id: Medication ID
            date: Date in YYYY-MM-DD format
            message_id: Telegram message ID
            
        Returns:
            True if updated, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE intake_status SET reminder_message_id = ? "
                "WHERE user_id = ? AND medication_id = ? AND date = ?",
                (message_id, user_id, medication_id, date)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def update_reminder_sent_at(
        self,
        intake_status_id: int,
        sent_at: int
    ) -> bool:
        """Update when reminder was sent.
        
        Args:
            intake_status_id: Intake status ID
            sent_at: Unix timestamp when sent
            
        Returns:
            True if updated, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE intake_status SET reminder_sent_at = ? WHERE id = ?",
                (sent_at, intake_status_id)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def get_pending_reminders(self, user_id: int, date: str) -> List[Dict[str, Any]]:
        """Get pending reminders for user.
        
        Args:
            user_id: Telegram user ID
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of pending reminder dictionaries
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT i.*, m.name, m.time, m.dosage "
                "FROM intake_status i "
                "JOIN medications m ON i.medication_id = m.id "
                "WHERE i.user_id = ? AND i.date = ? AND i.taken_at IS NULL",
                (user_id, date)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users.
        
        Returns:
            List of user dictionaries
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_missed_notifications(self, user_id: int, date: str) -> List[Dict[str, Any]]:
        """Get medications that should have had notifications but didn't.
        
        Args:
            user_id: Telegram user ID
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of medication dictionaries that missed notifications
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT m.*, i.taken_at, i.reminder_message_id
                FROM medications m
                LEFT JOIN intake_status i ON m.id = i.medication_id AND i.date = ?
                WHERE m.user_id = ?
                AND m.time <= time('now', 'localtime')
                AND (i.taken_at IS NULL OR i.taken_at = 0)
            """, (date, user_id))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]