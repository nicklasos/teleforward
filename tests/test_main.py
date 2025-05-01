# test_telegram_forwarder_bot.py
# Pytest tests for Telegram Forwarding Bot

import pytest
import os
import sys
import logging
from unittest.mock import AsyncMock, patch, MagicMock

# Disable logging for tests
logging.disable(logging.CRITICAL)

# Add the src directory to the path so we can import the bot script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create a fixture to set up environment and import the bot for each test
@pytest.fixture
def bot_module():
    # Set up test environment variables
    with patch.dict('os.environ', {'TELEGRAM_TOKEN': 'test_token'}):
        # Mock dotenv loading
        with patch('dotenv.load_dotenv'):
            # Import the module
            import src.main as bot
            
            # Reset module globals before each test
            bot.OWNER_ID = None
            bot.TARGET_CHATS = []
            
            yield bot

# Test environment variable loading
def test_env_loading(bot_module):
    """Test that the bot properly loads environment variables"""
    assert bot_module.TELEGRAM_TOKEN == 'test_token'

# Test error handling for missing token
def test_missing_token():
    """Test error handling when token is missing"""
    with patch.dict('os.environ', clear=True):
        with pytest.raises(ValueError):
            # Re-import to trigger the check
            with patch('dotenv.load_dotenv'):
                import importlib
                import src.main
                importlib.reload(src.main)

# Test /start command for first user (becoming owner)
@pytest.mark.asyncio
async def test_start_command_first_user(bot_module):
    """Test that the first user to use /start becomes owner"""
    # Create mock update
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_update.effective_user = mock_user
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context
    mock_context = MagicMock()
    
    # Call start function
    await bot_module.start(mock_update, mock_context)
    
    # Check owner is set
    assert bot_module.OWNER_ID == 12345
    
    # Verify appropriate message was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "You are now set as the bot owner" in call_args

# Test /start command for existing owner
@pytest.mark.asyncio
async def test_start_command_owner(bot_module):
    """Test owner using /start after already being set"""
    # Set owner
    bot_module.OWNER_ID = 12345
    
    # Create mock update
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_update.effective_user = mock_user
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context
    mock_context = MagicMock()
    
    # Call start function
    await bot_module.start(mock_update, mock_context)
    
    # Owner should remain the same
    assert bot_module.OWNER_ID == 12345
    
    # Verify greeting message (not "now set as owner")
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "Hi! I am your message forwarding bot" in call_args
    assert "You are now set as the bot owner" not in call_args

# Test /start command for non-owner
@pytest.mark.asyncio
async def test_start_command_other_user(bot_module):
    """Test another user using /start after owner is set"""
    # Set owner
    bot_module.OWNER_ID = 12345
    
    # Create mock update with different user
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 67890  # Different user ID
    mock_update.effective_user = mock_user
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context
    mock_context = MagicMock()
    
    # Call start function
    await bot_module.start(mock_update, mock_context)
    
    # Owner should remain the same
    assert bot_module.OWNER_ID == 12345
    
    # Verify private bot message
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "This bot is private" in call_args

# Test /help command for owner
@pytest.mark.asyncio
async def test_help_command_owner(bot_module):
    """Test owner using /help command"""
    # Set owner
    bot_module.OWNER_ID = 12345
    
    # Create mock update
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_update.effective_user = mock_user
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context
    mock_context = MagicMock()
    
    # Call help function
    await bot_module.help_command(mock_update, mock_context)
    
    # Verify help text was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "Available commands" in call_args

# Test /help command for non-owner
@pytest.mark.asyncio
async def test_help_command_other_user(bot_module):
    """Test non-owner using /help command"""
    # Set owner
    bot_module.OWNER_ID = 12345
    
    # Create mock update with different user
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 67890  # Different user ID
    mock_update.effective_user = mock_user
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context
    mock_context = MagicMock()
    
    # Call help function
    await bot_module.help_command(mock_update, mock_context)
    
    # Verify no message was sent (function returns early)
    mock_update.message.reply_text.assert_not_called()

# Test /chats command with no target chats
@pytest.mark.asyncio
async def test_list_chats_empty(bot_module):
    """Test /chats command when no target chats exist"""
    # Set owner
    bot_module.OWNER_ID = 12345
    
    # Create mock update
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_update.effective_user = mock_user
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context
    mock_context = MagicMock()
    
    # Call list_chats function
    await bot_module.list_chats(mock_update, mock_context)
    
    # Verify appropriate message was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "No chats configured yet" in call_args

# Test /chats command with existing target chats
@pytest.mark.asyncio
async def test_list_chats_with_targets(bot_module):
    """Test /chats command when target chats exist"""
    # Set owner and add some target chats
    bot_module.OWNER_ID = 12345
    bot_module.TARGET_CHATS = [-100123, -100456]
    
    # Create mock update
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_update.effective_user = mock_user
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context
    mock_context = MagicMock()
    
    # Call list_chats function
    await bot_module.list_chats(mock_update, mock_context)
    
    # Verify list was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "Messages are being forwarded" in call_args
    assert "-100123" in call_args
    assert "-100456" in call_args

# Test message handling from a group chat
@pytest.mark.asyncio
async def test_forward_message_from_group(bot_module):
    """Test message handling from a group chat"""
    # Set owner
    bot_module.OWNER_ID = 12345
    
    # Create mock update simulating a group message
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 67890  # Not the owner
    mock_update.effective_user = mock_user
    mock_update.effective_chat.id = -100789  # Group chat ID (negative)
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    
    # Call forward_message function
    await bot_module.forward_message(mock_update, mock_context)
    
    # Check that the group was added to TARGET_CHATS
    assert -100789 in bot_module.TARGET_CHATS
    
    # Verify no forwarding attempted (since message not from owner in private chat)
    mock_update.message.reply_text.assert_not_called()
    if hasattr(mock_context.bot, 'copy_message'):
        mock_context.bot.copy_message.assert_not_called()

# Test forwarding message from owner in private chat
@pytest.mark.asyncio
async def test_forward_message_from_owner(bot_module):
    """Test forwarding message from owner in private chat"""
    # Set owner and add target chat
    bot_module.OWNER_ID = 12345
    bot_module.TARGET_CHATS = [-100123]
    
    # Create mock update simulating owner in private chat
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 12345  # Owner
    mock_update.effective_user = mock_user
    mock_update.effective_chat.id = 12345  # Private chat (same as user ID)
    mock_update.message.message_id = 42
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context with bot that has copy_message method
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_context.bot.copy_message = AsyncMock()
    
    # Call forward_message function
    await bot_module.forward_message(mock_update, mock_context)
    
    # Verify forwarding was attempted
    mock_context.bot.copy_message.assert_called_once_with(
        chat_id=-100123,
        from_chat_id=12345,
        message_id=42
    )
    
    # Verify success message was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "Message forwarded to 1/1 chats" in call_args

# Test forwarding when no target groups exist
@pytest.mark.asyncio
async def test_forward_message_no_groups(bot_module):
    """Test forwarding when no target groups exist"""
    # Set owner but no target chats
    bot_module.OWNER_ID = 12345
    bot_module.TARGET_CHATS = []
    
    # Create mock update simulating owner in private chat
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 12345  # Owner
    mock_update.effective_user = mock_user
    mock_update.effective_chat.id = 12345  # Private chat
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context
    mock_context = MagicMock()
    
    # Call forward_message function
    await bot_module.forward_message(mock_update, mock_context)
    
    # Verify appropriate message was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "I'm not in any groups yet" in call_args

# Test forwarding with some failed chats
@pytest.mark.asyncio
async def test_forward_message_with_errors(bot_module):
    """Test forwarding with some failed chats"""
    # Set owner and add some target chats
    bot_module.OWNER_ID = 12345
    bot_module.TARGET_CHATS = [-100123, -100456, -100789]
    
    # Create mock update simulating owner in private chat
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 12345  # Owner
    mock_update.effective_user = mock_user
    mock_update.effective_chat.id = 12345  # Private chat
    mock_update.message.message_id = 42
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context with bot that has copy_message method that fails for some chats
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    
    async def mock_copy_message(chat_id, from_chat_id, message_id):
        if chat_id == -100456:
            raise Exception("Forbidden: bot was blocked by the user")
        if chat_id == -100789:
            raise Exception("Bad Request: chat not found")
    
    mock_context.bot.copy_message = AsyncMock(side_effect=mock_copy_message)
    
    # Call forward_message function
    await bot_module.forward_message(mock_update, mock_context)
    
    # Verify unsuccessful chats were removed
    assert -100123 in bot_module.TARGET_CHATS
    assert -100456 not in bot_module.TARGET_CHATS
    assert -100789 not in bot_module.TARGET_CHATS
    
    # Verify partial success message
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "Message forwarded to 1/3 chats" in call_args

# Test main function sets up the application correctly
def test_main_function(bot_module):
    """Test that the main function sets up the application correctly"""
    with patch('telegram.ext.Application.builder') as mock_builder:
        mock_application = MagicMock()
        mock_builder.return_value.token.return_value.build.return_value = mock_application
        
        # Call main function
        bot_module.main()
        
        # Verify handlers were added
        assert mock_application.add_handler.call_count == 4
        
        # Check that polling was started
        mock_application.run_polling.assert_called_once()