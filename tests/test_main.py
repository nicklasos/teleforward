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
    with patch.dict('os.environ', {'TELEGRAM_TOKEN': 'test_token', 'OWNER_ID': '12345'}):
        # Mock dotenv loading
        with patch('dotenv.load_dotenv'):
            # Import the module
            import src.main as bot
            
            # Reset module globals before each test
            bot.OWNER_ID = 12345  # Now set from .env
            bot.TARGET_CHATS = []
            
            yield bot

# Test environment variable loading
def test_env_loading(bot_module):
    """Test that the bot properly loads environment variables"""
    assert bot_module.TELEGRAM_TOKEN == 'test_token'
    assert bot_module.OWNER_ID == 12345  # Now tests owner ID loaded from env

# Test error handling for missing token
def test_missing_token():
    """Test error handling when token is missing"""
    with patch.dict('os.environ', {'OWNER_ID': '12345'}, clear=True):
        with pytest.raises(ValueError):
            # Re-import to trigger the check
            with patch('dotenv.load_dotenv'):
                import importlib
                import src.main
                importlib.reload(src.main)

# Test loading an invalid owner ID from environment
def test_invalid_owner_id():
    """Test error handling when owner ID is invalid"""
    with patch.dict('os.environ', {'TELEGRAM_TOKEN': 'test_token', 'OWNER_ID': 'not_a_number'}, clear=True):
        with patch('dotenv.load_dotenv'):
            import importlib
            import src.main
            importlib.reload(src.main)
            # Should log an error but not crash, and set OWNER_ID to None
            assert src.main.OWNER_ID is None

# Test /start command for first user (becoming owner)
@pytest.mark.asyncio
async def test_start_command_first_user(bot_module):
    """Test that the first user to use /start becomes owner when not set in env"""
    # Set owner to None to simulate not set in env
    bot_module.OWNER_ID = None
    
    # Create mock update
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 67890
    mock_update.effective_user = mock_user
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context
    mock_context = MagicMock()
    
    # Call start function
    await bot_module.start(mock_update, mock_context)
    
    # Check owner is set
    assert bot_module.OWNER_ID == 67890
    
    # Verify appropriate message was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "You are now set as the bot owner" in call_args

# Test /start command for existing owner
@pytest.mark.asyncio
async def test_start_command_owner(bot_module):
    """Test owner using /start after already being set"""
    # Owner is already set to 12345 in fixture
    
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
    # Owner is already set to 12345 in fixture
    
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
    # Owner is already set to 12345 in fixture
    
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
    # Verify new commands are included in help text
    assert "/deep_scan" in call_args
    assert "/add_chat" in call_args
    assert "/chatid" in call_args

# Test /help command for non-owner
@pytest.mark.asyncio
async def test_help_command_other_user(bot_module):
    """Test non-owner using /help command"""
    # Owner is already set to 12345 in fixture
    
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
    # Owner is already set to 12345 in fixture
    
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
    # Owner is already set to 12345 in fixture
    # Add some target chats
    bot_module.TARGET_CHATS = [-100123, -100456]
    
    # Create mock update
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_update.effective_user = mock_user
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context with mock bot
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_context.bot.get_chat = AsyncMock()
    
    # Mock the Chat object returned by get_chat
    mock_chat = MagicMock()
    mock_chat.title = "Test Group"
    mock_chat.type = "supergroup"
    mock_context.bot.get_chat.return_value = mock_chat
    
    # Call list_chats function
    await bot_module.list_chats(mock_update, mock_context)
    
    # Verify list was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "Messages are being forwarded" in call_args
    assert "Test Group" in call_args

# Test /chatid command
@pytest.mark.asyncio
async def test_chatid_command(bot_module):
    """Test /chatid command"""
    # Create mock update
    mock_update = AsyncMock()
    mock_update.effective_chat.id = -100123
    mock_update.effective_chat.type = "supergroup"
    mock_update.effective_chat.title = "Test Group"
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context
    mock_context = MagicMock()
    
    # Call chatid function
    await bot_module.get_chat_id(mock_update, mock_context)
    
    # Verify chat info was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "Інформація про чат" in call_args
    assert "Test Group" in call_args
    assert "-100123" in call_args
    assert "supergroup" in call_args

# Test /add_chat command with normal verification
@pytest.mark.asyncio
async def test_add_chat_command_normal(bot_module):
    """Test /add_chat command with normal verification"""
    # Owner is already set to 12345 in fixture
    
    # Create mock update
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_update.effective_user = mock_user
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context with args
    mock_context = MagicMock()
    mock_context.args = ["-100123"]
    mock_context.bot = AsyncMock()
    
    # Mock the Chat object returned by get_chat
    mock_chat = MagicMock()
    mock_chat.title = "Test Group"
    mock_chat.type = "supergroup"
    mock_context.bot.get_chat.return_value = mock_chat
    
    # Call add_chat function
    await bot_module.manual_add_chat(mock_update, mock_context)
    
    # Verify chat was added
    assert -100123 in bot_module.TARGET_CHATS
    
    # Verify confirmation message
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "Added chat" in call_args
    assert "Test Group" in call_args

# Test /add_chat command with force option
@pytest.mark.asyncio
async def test_add_chat_command_force(bot_module):
    """Test /add_chat command with force option"""
    # Owner is already set to 12345 in fixture
    
    # Create mock update
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_update.effective_user = mock_user
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context with args including force
    mock_context = MagicMock()
    mock_context.args = ["-100456", "force"]
    
    # Call add_chat function
    await bot_module.manual_add_chat(mock_update, mock_context)
    
    # Verify chat was added even without verification
    assert -100456 in bot_module.TARGET_CHATS
    
    # Verify confirmation message
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "Force-added chat ID" in call_args

# Test /add_chat command when verification fails but force option used
@pytest.mark.asyncio
async def test_add_chat_command_force_after_failure(bot_module):
    """Test /add_chat command when verification fails but force option is used"""
    # Owner is already set to 12345 in fixture
    
    # Create mock update
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_update.effective_user = mock_user
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context with args including force
    mock_context = MagicMock()
    mock_context.args = ["-100789", "force"]
    mock_context.bot = AsyncMock()
    
    # Mock get_chat to raise an exception
    mock_context.bot.get_chat = AsyncMock(side_effect=Exception("Chat not found"))
    
    # Call add_chat function
    await bot_module.manual_add_chat(mock_update, mock_context)
    
    # Verify chat was added despite verification failure
    assert -100789 in bot_module.TARGET_CHATS
    
    # Verify confirmation message
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "added anyway as requested" in call_args

# Test /refresh command keeping unverifiable chats
@pytest.mark.asyncio
async def test_refresh_keeps_unverifiable_chats(bot_module):
    """Test /refresh command keeps chats that can't be verified"""
    # Owner is already set to 12345 in fixture
    # Add some target chats
    bot_module.TARGET_CHATS = [-100123, -100456]
    
    # Create mock update
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_update.effective_user = mock_user
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    
    # Make get_chat succeed for one chat and fail for the other
    async def mock_get_chat(chat_id):
        if chat_id == -100123:
            mock_chat = MagicMock()
            mock_chat.title = "Good Group"
            return mock_chat
        else:
            raise Exception("Chat not found")
    
    mock_context.bot.get_chat = AsyncMock(side_effect=mock_get_chat)
    
    # Mock get_chat_member to avoid further errors
    mock_member = MagicMock()
    mock_member.status = "member"
    mock_context.bot.get_chat_member = AsyncMock(return_value=mock_member)
    
    # Call refresh function
    await bot_module.refresh_chats(mock_update, mock_context)
    
    # Verify both chats are still in the list (even the one that failed verification)
    assert -100123 in bot_module.TARGET_CHATS
    assert -100456 in bot_module.TARGET_CHATS
    
    # Verify success message
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "Now forwarding to" in call_args

# Test message handling from a group chat
@pytest.mark.asyncio
async def test_forward_message_from_group(bot_module):
    """Test message handling from a group chat"""
    # Owner is already set to 12345 in fixture
    
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
    # Owner is already set to 12345 in fixture
    # Add target chat
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
    # Owner is already set to 12345 in fixture
    # No target chats
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
    # Owner is already set to 12345 in fixture
    # Add some target chats
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

# Test deep scan for groups
@pytest.mark.asyncio
async def test_deep_scan_for_groups(bot_module):
    """Test deep scan for finding groups"""
    # Owner is already set to 12345 in fixture
    
    # Create mock update
    mock_update = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_update.effective_user = mock_user
    mock_update.message.reply_text = AsyncMock()
    
    # Create mock context
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    
    # Mock get_updates to return mock updates
    mock_update1 = MagicMock()
    mock_update1.message = MagicMock()
    mock_update1.message.chat.id = -100123
    mock_update1.message.chat.type = "supergroup"
    
    mock_update2 = MagicMock()
    mock_update2.edited_message = MagicMock()
    mock_update2.edited_message.chat.id = -100456
    mock_update2.edited_message.chat.type = "group"
    mock_update2.message = None
    
    mock_context.bot.get_updates = AsyncMock(return_value=[mock_update1, mock_update2])
    
    # Mock get_chat and get_chat_member to make membership verification succeed
    mock_chat = MagicMock()
    mock_chat.title = "Test Group"
    mock_context.bot.get_chat = AsyncMock(return_value=mock_chat)
    
    mock_member = MagicMock()
    mock_member.status = "member"
    mock_context.bot.get_chat_member = AsyncMock(return_value=mock_member)
    
    # Call deep_scan function
    await bot_module.deep_scan_for_groups(mock_update, mock_context)
    
    # Verify groups were discovered
    assert -100123 in bot_module.TARGET_CHATS
    assert -100456 in bot_module.TARGET_CHATS
    
    # Verify success message
    mock_update.message.reply_text.assert_called()
    call_args = mock_update.message.reply_text.call_args_list[-1][0][0]  # Get last call
    assert "Deep scan complete" in call_args
    assert "Test Group" in call_args

# Test main function sets up the application correctly with all handlers
def test_main_function(bot_module):
    """Test that the main function sets up the application correctly with all new handlers"""
    with patch('telegram.ext.Application.builder') as mock_builder:
        mock_application = MagicMock()
        mock_builder.return_value.token.return_value.build.return_value = mock_application
        
        # Call main function
        bot_module.main()
        
        # Verify handlers were added
        assert mock_application.add_handler.call_count == 9  # Check we have all handlers, including new ones
        
        # Check that polling was started
        mock_application.run_polling.assert_called_once()