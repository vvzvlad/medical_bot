"""Sample user data for testing."""

# Sample user with no medications
SAMPLE_USER_EMPTY = {
    "user_id": 123456789,
    "timezone_offset": "+03:00",
    "medications": []
}

# Sample user with single medication
SAMPLE_USER_SINGLE_MED = {
    "user_id": 123456789,
    "timezone_offset": "+03:00",
    "medications": [
        {
            "id": 1,
            "name": "аспирин",
            "dosage": "200 мг",
            "time": "10:00",
            "last_taken": None,
            "reminder_message_id": None
        }
    ]
}

# Sample user with multiple medications
SAMPLE_USER_WITH_MEDS = {
    "user_id": 123456789,
    "timezone_offset": "+03:00",
    "medications": [
        {
            "id": 1,
            "name": "аспирин",
            "dosage": "200 мг",
            "time": "10:00",
            "last_taken": None,
            "reminder_message_id": None
        },
        {
            "id": 2,
            "name": "парацетамол",
            "dosage": "400 мг",
            "time": "18:00",
            "last_taken": 1704110400,  # Some past timestamp
            "reminder_message_id": 12345
        }
    ]
}

# Sample user with medication taken today
SAMPLE_USER_MED_TAKEN = {
    "user_id": 123456789,
    "timezone_offset": "+03:00",
    "medications": [
        {
            "id": 1,
            "name": "аспирин",
            "dosage": "200 мг",
            "time": "10:00",
            "last_taken": 1704096000,  # Today's timestamp
            "reminder_message_id": None
        }
    ]
}

# Sample user with medication with reminder sent
SAMPLE_USER_WITH_REMINDER = {
    "user_id": 123456789,
    "timezone_offset": "+03:00",
    "medications": [
        {
            "id": 1,
            "name": "аспирин",
            "dosage": "200 мг",
            "time": "10:00",
            "last_taken": None,
            "reminder_message_id": 12345
        }
    ]
}

# Sample user with multiple medications at same time
SAMPLE_USER_SAME_TIME = {
    "user_id": 123456789,
    "timezone_offset": "+03:00",
    "medications": [
        {
            "id": 1,
            "name": "аспирин",
            "dosage": "200 мг",
            "time": "10:00",
            "last_taken": None,
            "reminder_message_id": None
        },
        {
            "id": 2,
            "name": "парацетамол",
            "dosage": "400 мг",
            "time": "10:00",
            "last_taken": None,
            "reminder_message_id": None
        }
    ]
}

# Sample user with same medication at different times
SAMPLE_USER_SAME_MED_DIFF_TIMES = {
    "user_id": 123456789,
    "timezone_offset": "+03:00",
    "medications": [
        {
            "id": 1,
            "name": "аспирин",
            "dosage": "200 мг",
            "time": "10:00",
            "last_taken": None,
            "reminder_message_id": 12345
        },
        {
            "id": 2,
            "name": "аспирин",
            "dosage": "200 мг",
            "time": "18:00",
            "last_taken": None,
            "reminder_message_id": None
        }
    ]
}
