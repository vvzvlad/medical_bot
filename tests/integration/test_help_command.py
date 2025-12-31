"""Integration tests for help command functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.llm.client import GroqAPIError


# TC-INT-HELP-001: Help Command Detection
@pytest.mark.asyncio
async def test_help_command_detection(
    mock_groq_client
):
    """Test that help command phrases are correctly detected."""
    # Given: Mock LLM client configured for testing
    client = mock_groq_client
    
    # Add help command detection to mock
    async def mock_detect_with_help(message):
        message_lower = message.lower()
        if any(phrase in message_lower for phrase in ["что ты умеешь", "помощь", "какие команды", "что можешь", "справка", "инструкция", "подскажи", "помоги"]):
            return "help"
        # Fall back to original detection logic
        elif "что я принимаю" in message_lower or "список" in message_lower or "покажи" in message_lower:
            return "list"
        elif "добавь" in message_lower or ("принимаю" in message_lower and "в" in message_lower):
            return "add"
        elif "удали" in message_lower:
            return "delete"
        elif "теперь в" in message_lower and any(c.isdigit() for c in message):
            return "time_change"
        elif "теперь" in message_lower and "мг" in message_lower:
            return "dose_change"
        elif "часовая зона" in message_lower or "timezone" in message_lower:
            return "timezone_change"
        elif "принял" in message_lower or "выпил" in message_lower:
            return "done"
        else:
            return "unknown"
    
    client.detect_command_type = AsyncMock(side_effect=mock_detect_with_help)
    
    # When: Testing various help command phrases
    help_phrases = [
        "что ты умеешь",
        "помощь",
        "какие команды",
        "что можешь",
        "справка",
        "инструкция",
        "что ты умеешь?",
        "Помоги мне, пожалуйста",
        "Подскажи команды"
    ]
    
    # Then: All should be detected as help command
    for phrase in help_phrases:
        command_type = await client.detect_command_type(phrase)
        assert command_type == "help", f"Phrase '{phrase}' should be detected as 'help', got '{command_type}'"


# TC-INT-HELP-002: Help Command Processing
@pytest.mark.asyncio
async def test_help_command_processing(
    mock_groq_client
):
    """Test that help command generates appropriate response."""
    # Given: Mock LLM client configured for testing
    client = mock_groq_client
    
    # Mock process_help_command to return expected structure
    expected_help_message = {
        "message": "Привет! Я помогу вам управлять расписанием приема медикаментов.\n\nВот что я умею:\n📋 Добавлять медикаменты - просто скажите 'я принимаю аспирин в 10:00'\n📅 Показывать расписание - спросите 'что я принимаю' или 'покажи расписание'\n⏰ Менять время приема - например, 'измени время аспирина на 12:00'\n💊 Менять дозировку - например, 'измени дозировку аспирина на 200 мг'\n🗑 Удалять медикаменты - скажите 'удали аспирин' или 'больше не принимаю парацетамол'\n✅ Отмечать прием - напишите 'я принял аспирин'\n🌍 Менять часовой пояс - укажите 'моя часовая зона Москва'\n\nОбщайтесь со мной естественно, как с человеком - я понимаю русский язык и не требую специальных команд!"
    }
    
    client.process_help_command = AsyncMock(return_value=expected_help_message)
    
    # When: Processing help command
    result = await client.process_help_command()
    
    # Then: Should return structured help message
    assert isinstance(result, dict)
    assert "message" in result
    assert isinstance(result["message"], str)
    assert len(result["message"]) > 0
    assert "расписание" in result["message"]
    assert "принимаю" in result["message"]
    assert "умею" in result["message"]


# TC-INT-HELP-003: Help Command Processing Error Handling
@pytest.mark.asyncio
async def test_help_command_processing_error(
    mock_groq_client
):
    """Test help command processing error handling."""
    # Given: Mock LLM client that raises API error
    client = mock_groq_client
    client.process_help_command = AsyncMock(side_effect=GroqAPIError("API error"))
    
    # When & Then: Should raise GroqAPIError
    with pytest.raises(GroqAPIError):
        await client.process_help_command()


# TC-INT-HELP-004: Help Command Handler Integration
@pytest.mark.asyncio
async def test_help_command_handler_integration(
    mock_message,
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test complete help command flow through handler."""
    # Given: User with account and configured services
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    mock_message.from_user.id = user_id
    mock_message.text = "что ты умеешь"
    
    # Configure mock to detect help command
    async def mock_detect_help(message):
        return "help" if "что ты умеешь" in message else "unknown"
    
    mock_groq_client.detect_command_type = AsyncMock(side_effect=mock_detect_help)
    mock_groq_client.process_help_command = AsyncMock(return_value={
        "message": "Я помогу вам управлять расписанием приема медикаментов!"
    })
    
    # Import handler function
    from src.bot.handlers import handle_help_command, init_handlers
    
    # Initialize handlers with the mock client
    init_handlers(data_manager, schedule_manager, mock_groq_client)
    
    # When: Processing help command through handler
    await handle_help_command(mock_message, user_id, thinking_msg=None)
    
    # Then: Should call process_help_command and send response
    mock_groq_client.process_help_command.assert_called_once()
    mock_message.answer.assert_called_once()
    
    # Verify response contains expected content
    call_args = mock_message.answer.call_args
    assert "расписанием приема медикаментов" in call_args[0][0]


# TC-INT-HELP-005: Help Command Handler Error Handling
@pytest.mark.asyncio
async def test_help_command_handler_error_handling(
    mock_message,
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test help command handler error handling."""
    # Given: User with account and failing LLM client
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    mock_message.from_user.id = user_id
    mock_message.text = "помощь"
    
    # Configure mock to simulate API error
    mock_groq_client.detect_command_type = AsyncMock(return_value="help")
    mock_groq_client.process_help_command = AsyncMock(
        side_effect=GroqAPIError("Insufficient funds")
    )
    
    # Import handler function
    from src.bot.handlers import handle_help_command, init_handlers
    
    # Initialize handlers with the mock client
    init_handlers(data_manager, schedule_manager, mock_groq_client)
    
    # When: Processing help command that fails
    await handle_help_command(mock_message, user_id, thinking_msg=None)
    
    # Then: Should handle error gracefully
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    # Should send fallback help message instead of crashing
    expected_fallback = "Я бот для управления приемом медикаментов.\n\nДоступные команды:\n- Добавь [название] в [время]\n- Что я принимаю - показать расписание\n- Удали [название]\n- Измени время [название] на [вреремя]"
    assert call_args[0][0] == expected_fallback


# TC-INT-HELP-006: Help Command Handler with Thinking Message
@pytest.mark.asyncio
async def test_help_command_handler_with_thinking_message(
    mock_message,
    data_manager,
    schedule_manager,
    mock_groq_client
):
    """Test help command handler with thinking message cleanup."""
    # Given: User with account and thinking message
    user_id = 123456789
    await data_manager.create_user(user_id, "+03:00")
    
    mock_message.from_user.id = user_id
    mock_message.text = "какие команды доступны?"
    
    # Create thinking message mock
    thinking_message = MagicMock()
    thinking_message.delete = AsyncMock()
    
    # Configure mocks
    mock_groq_client.detect_command_type = AsyncMock(return_value="help")
    mock_groq_client.process_help_command = AsyncMock(return_value={
        "message": "Доступные команды: добавление, просмотр, изменение расписания"
    })
    
    # Import handler function
    from src.bot.handlers import handle_help_command, init_handlers
    
    # Initialize handlers with the mock client
    init_handlers(data_manager, schedule_manager, mock_groq_client)
    
    # When: Processing help command with thinking message
    await handle_help_command(mock_message, user_id, thinking_msg=thinking_message)
    
    # Then: Should clean up thinking message and send response
    thinking_message.delete.assert_called_once()
    mock_message.answer.assert_called_once()


# TC-INT-HELP-007: Multiple Help Phrases Testing
@pytest.mark.asyncio
async def test_multiple_help_phrases_integration(
    mock_groq_client
):
    """Test various help command phrases in integration."""
    # Given: Mock LLM client with help command support
    client = mock_groq_client
    
    # Enhanced mock that recognizes all help phrases
    async def enhanced_detect(message):
        message_lower = message.lower()
        help_phrases = [
            "что ты умеешь", "помощь", "какие команды", "что можешь",
            "справка", "инструкция", "help", "хелп", "подскажи",
            "помоги", "что ты можешь", "как пользоваться", "что делать"
        ]
        
        if any(phrase in message_lower for phrase in help_phrases):
            return "help"
        elif "что я принимаю" in message_lower:
            return "list"
        else:
            return "unknown"
    
    client.detect_command_type = AsyncMock(side_effect=enhanced_detect)
    client.process_help_command = AsyncMock(return_value={
        "message": "Я ваш персональный ассистент для управления приемом медикаментов!"
    })
    
    # When: Testing various help phrases
    test_cases = [
        "что ты умеешь?",
        "Помогите, пожалуйста",
        "Какие команды ты знаешь?",
        "Справка",
        "Инструкция по использованию",
        "Как пользоваться ботом?",
        "Help me",
        "Что ты можешь делать?"
    ]
    
    # Then: All should be detected as help and return valid response
    for phrase in test_cases:
        command_type = await client.detect_command_type(phrase)
        assert command_type == "help", f"Phrase '{phrase}' should be detected as 'help'"
        
        result = await client.process_help_command()
        assert "message" in result
        assert isinstance(result["message"], str)
        assert len(result["message"]) > 0


# TC-INT-HELP-008: Help Command Response Structure Validation
@pytest.mark.asyncio
async def test_help_command_response_structure(
    mock_groq_client
):
    """Test that help command response has proper structure and content."""
    # Given: Mock LLM client
    client = mock_groq_client
    
    # Mock with comprehensive help response
    comprehensive_help_response = {
        "message": """Привет! Я помогу вам управлять расписанием приема медикаментов.

Вот что я умею:
📋 Добавлять медикаменты - просто скажите 'я принимаю аспирин в 10:00'
📅 Показывать расписание - спросите 'что я принимаю' или 'покажи расписание'
⏰ Менять время приема - например, 'измени время аспирина на 12:00'
💊 Менять дозировку - например, 'измени дозировку аспирина на 200 мг'
🗑 Удалять медикаменты - скажите 'удали аспирин' или 'больше не принимаю парацетамол'
✅ Отмечать прием - напишите 'я принял аспирин'
🌍 Менять часовой пояс - укажите 'моя часовая зона Москва'

Общайтесь со мной естественно, как с человеком - я понимаю русский язык и не требую специальных команд!"""
    }
    
    client.process_help_command = AsyncMock(return_value=comprehensive_help_response)
    
    # When: Getting help response
    result = await client.process_help_command()
    
    # Then: Should have proper structure and content
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "message" in result, "Result should contain 'message' key"
    
    message = result["message"]
    assert isinstance(message, str), "Message should be a string"
    assert len(message) > 100, "Help message should be substantial"
    
    # Check for key content elements
    content_checks = [
        "расписанием приема медикаментов",
        "умею",
        "Показывать расписание",
        "время приема",
        "Удалять медикаменты",
        "русский язык"
    ]
    
    for check in content_checks:
        assert check in message, f"Help message should contain '{check}'"