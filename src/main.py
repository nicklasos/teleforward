#!/usr/bin/env python
# Improved Telegram Message Forwarding Bot

import logging
import os
from telegram import Update, Chat
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.ext import ChatMemberHandler
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.ERROR  # Changed to INFO to help with debugging
)
logger = logging.getLogger(__name__)

# Get the Telegram bot token from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("No TELEGRAM_TOKEN found in .env file")

# Get owner ID from environment variables if available
OWNER_ID = os.getenv("OWNER_ID")
if OWNER_ID:
    try:
        OWNER_ID = int(OWNER_ID)
        logger.info(f"Owner ID loaded from .env: {OWNER_ID}")
    except ValueError:
        logger.error("Invalid OWNER_ID in .env file, must be an integer")
        OWNER_ID = None
else:
    OWNER_ID = None

# Store target chats where messages should be forwarded
TARGET_CHATS = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    global OWNER_ID
    user_id = update.effective_user.id
    
    # If OWNER_ID is None (not set in .env), set it to the first user who interacts
    if OWNER_ID is None:
        OWNER_ID = user_id
        logger.info(f"Owner ID set to: {OWNER_ID}")
        await update.message.reply_text(
            f'Hi! I am your message forwarding bot. You are now set as the bot owner (ID: {user_id}).\n'
            'Send me any message, and I will forward it to all groups I am a member of.'
        )
    elif user_id == OWNER_ID:
        await update.message.reply_text(
            'Hi! I am your message forwarding bot. Send me any message to forward it to all groups I am a member of.'
        )
    else:
        await update.message.reply_text('This bot is private and can only be used by its owner.')
        logger.info(f"User {user_id} is not the owner, access denied")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        logger.info(f"User {user_id} is not the owner, skipping help command")
        return
    
    help_text = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/chats - List all chats where the bot is forwarding messages\n"
        "/refresh - Refresh the list of groups (use this if you add the bot to new groups)\n"
        "/deep_scan - Perform a deeper scan to find all groups the bot is in\n"
        "/scan - Get instructions for making the bot discover groups\n"
        "/add_chat CHAT_ID [force] - Manually add a chat ID to the forwarding list\n"
        "/chatid - Show the ID of the current chat\n\n"
        "Any other message you send will be forwarded to all groups where I am a member."
    )
    await update.message.reply_text(help_text)

async def list_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all target chats"""
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        logger.info(f"User {user_id} is not the owner, skipping list chats")
        return
    
    if not TARGET_CHATS:
        await update.message.reply_text("No chats configured yet. Add me to groups where you want to forward messages.")
    else:
        chat_info = []
        for chat_id in TARGET_CHATS:
            try:
                chat = await context.bot.get_chat(chat_id)
                chat_name = chat.title if chat.type != Chat.PRIVATE else "Private chat"
                chat_info.append(f"- {chat_name} (ID: {chat_id})")
            except Exception as e:
                chat_info.append(f"- Unknown chat (ID: {chat_id}) - Error: {str(e)}")
        
        targets = "\n".join(chat_info)
        await update.message.reply_text(f"Messages are being forwarded to these chats:\n{targets}")

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the chat ID of the current chat"""
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    chat_title = update.effective_chat.title if hasattr(update.effective_chat, 'title') else "Приватний чат"
    
    await update.message.reply_text(
        f"Інформація про чат:\n"
        f"- Назва: {chat_title}\n"
        f"- Тип: {chat_type}\n"
        f"- ID: {chat_id}"
    )

async def refresh_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually refresh the list of chats and try to discover new ones"""
    global TARGET_CHATS  # Declare global at the beginning of the function
    
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        logger.info(f"User {user_id} is not the owner ({OWNER_ID}), skipping refresh")
        return
    
    await update.message.reply_text("Attempting to refresh the list of groups...")
    
    # First verify existing chats
    valid_chats = []
    for chat_id in TARGET_CHATS:
        try:
            chat = await context.bot.get_chat(chat_id)
            # Verify the bot is still a member
            member = await context.bot.get_chat_member(chat_id, context.bot.id)
            if member.status not in ['left', 'kicked']:
                valid_chats.append(chat_id)
                logger.info(f"Verified membership in: {chat.title} ({chat_id})")
        except Exception as e:
            logger.error(f"Failed to verify chat {chat_id}: {e}")
            # Keep the chat in the list even if we can't verify it
            valid_chats.append(chat_id)
            logger.info(f"Keeping unverifiable chat: {chat_id} in the list")
    
    # Try to discover chats from the updates
    try:
        # Get updates to see recent chats
        updates = await context.bot.get_updates(limit=100, timeout=1)
        
        # Look through updates for chats
        for update in updates:
            if update.message and update.message.chat.type in ['group', 'supergroup']:
                chat_id = update.message.chat.id
                if chat_id not in valid_chats:
                    try:
                        # Check if bot is a member
                        member = await context.bot.get_chat_member(chat_id, context.bot.id)
                        if member.status not in ['left', 'kicked']:
                            valid_chats.append(chat_id)
                            chat = await context.bot.get_chat(chat_id)
                            logger.info(f"Discovered group from updates: {chat.title} ({chat_id})")
                    except Exception as e:
                        logger.error(f"Failed to check bot membership in discovered chat {chat_id}: {e}")
    except Exception as e:
        logger.error(f"Error during chat discovery: {e}")
    
    # If we found any valid chats, update TARGET_CHATS
    if valid_chats:
        # Calculate statistics
        original_count = len(TARGET_CHATS)
        new_count = len(valid_chats)
        removed = max(0, original_count - new_count)  # Adjusted to prevent negative values
        discovered = max(0, new_count - original_count)  # Adjusted to prevent negative values
        
        TARGET_CHATS.clear()
        TARGET_CHATS.extend(valid_chats)
        
        # Save updated chat list
        save_chats()
        
        result_msg = f"Refresh complete. Now forwarding to {len(valid_chats)} groups."
        if removed > 0:
            result_msg += f" Removed {removed} invalid groups."
        if discovered > 0:
            result_msg += f" Discovered {discovered} new groups."
        
        await update.message.reply_text(result_msg)
    else:
        # If no groups found, ask user to add the bot to groups
        await update.message.reply_text(
            "No groups found. Please make sure the bot is added to groups and has permission to access messages.\n"
            "You might need to:\n"
            "1. Add the bot to groups manually\n"
            "2. Send some messages in those groups so the bot can detect them\n"
            "3. Give the bot admin rights in the groups\n\n"
            "Try using /deep_scan for a more thorough search."
        )

async def deep_scan_for_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Perform a deep scan to find all groups the bot is a member of"""
    global TARGET_CHATS  # Declare global at the beginning of the function
    
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        logger.info(f"User {user_id} is not the owner ({OWNER_ID}), skipping deep scan")
        return
        
    await update.message.reply_text("Starting deep scan for groups. This may take a moment...")
    
    # Store the original list for comparison
    original_chats = set(TARGET_CHATS)
    discovered_chats = []
    
    # First, verify existing chats but keep them even if verification fails
    valid_chats = list(TARGET_CHATS)  # Start with all existing chats
    
    # Get a broad range of updates to find all chats
    try:
        # Get as many updates as possible
        updates = await context.bot.get_updates(limit=100, timeout=1, offset=-1)
        
        # Process all updates to find chats
        for update in updates:
            chat_id = None
            chat_type = None
            
            # Check different update types for chat info
            if update.message:
                chat_id = update.message.chat.id
                chat_type = update.message.chat.type
            elif update.edited_message:
                chat_id = update.edited_message.chat.id
                chat_type = update.edited_message.chat.type
            elif update.channel_post:
                chat_id = update.channel_post.chat.id
                chat_type = update.channel_post.chat.type
            elif update.edited_channel_post:
                chat_id = update.edited_channel_post.chat.id
                chat_type = update.edited_channel_post.chat.type
            elif update.callback_query and update.callback_query.message:
                chat_id = update.callback_query.message.chat.id
                chat_type = update.callback_query.message.chat.type
            
            # Add group chats not already in the list
            if chat_id and chat_type in ['group', 'supergroup'] and chat_id not in valid_chats:
                try:
                    # Try to verify the bot is actually a member
                    try:
                        member = await context.bot.get_chat_member(chat_id, context.bot.id)
                        if member.status not in ['left', 'kicked']:
                            valid_chats.append(chat_id)
                            
                            # If this is a newly discovered chat, add to discovered list
                            if chat_id not in original_chats:
                                chat = await context.bot.get_chat(chat_id)
                                discovered_chats.append(f"{chat.title} ({chat_id})")
                                logger.info(f"Deep scan discovered group: {chat.title} ({chat_id})")
                    except Exception:
                        # Still add the chat even if verification fails
                        valid_chats.append(chat_id)
                        if chat_id not in original_chats:
                            discovered_chats.append(f"Unknown group ({chat_id})")
                            logger.info(f"Deep scan added unverifiable group: {chat_id}")
                except Exception as e:
                    logger.error(f"Error processing chat {chat_id}: {e}")
    except Exception as e:
        logger.error(f"Error during deep scan: {e}")
    
    # Update TARGET_CHATS with our findings
    if valid_chats:
        TARGET_CHATS.clear()
        TARGET_CHATS.extend(valid_chats)
        save_chats()
        
        # Generate result message
        if discovered_chats:
            msg = f"Deep scan complete. Found {len(valid_chats)} total groups. Newly discovered groups:\n"
            msg += "\n".join([f"- {chat}" for chat in discovered_chats])
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(f"Deep scan complete. Verified {len(valid_chats)} groups. No new groups discovered.")
    else:
        await update.message.reply_text(
            "No groups found during deep scan. Please make sure I'm a member of at least one group.\n"
            "You can manually add groups using the /add_chat command if you know the group ID."
        )

async def active_scan_for_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Actively scan for groups by asking user to invite the bot to a group chat"""
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        logger.info(f"User {user_id} is not the owner, skipping scan request")
        return
        
    await update.message.reply_text(
        "I'll help you find all the groups I'm a member of. Please follow these steps:\n\n"
        "1. Add me to any groups where I'm not already a member\n"
        "2. If I'm already in groups but not detecting them, make me an admin in those groups\n"
        "3. Send a message in each group that mentions me (using @YourBotUsername)\n"
        "4. After doing this, run the /deep_scan command\n\n"
        "This should help me discover all the groups I'm in.\n\n"
        "If you know the group ID already, you can use:\n"
        "/add_chat GROUP_ID force"
    )

async def manual_add_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually add a chat ID to the TARGET_CHATS list"""
    global TARGET_CHATS  # Declare global at the beginning of the function
    
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        logger.info(f"User {user_id} is not the owner, skipping manual add")
        return
    
    # Check if there's a chat ID in the command
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "Please provide a chat ID.\n"
            "Usage: /add_chat CHAT_ID [force]\n"
            "Example: /add_chat -1001234567890\n\n"
            "Add 'force' after the ID to skip verification and add the group even if it appears inaccessible."
        )
        return
    
    try:
        # Try to parse the chat ID
        chat_id = int(context.args[0])
        force_add = False
        
        # Check if we should force add without verification
        if len(context.args) > 1 and context.args[1].lower() == 'force':
            force_add = True
        
        # Check if the chat ID is already in the list
        if chat_id in TARGET_CHATS:
            await update.message.reply_text(f"Chat ID {chat_id} is already in the list.")
            return
        
        # Try to get information about the chat
        try:
            if not force_add:
                # Try to verify the chat exists and bot has access
                chat = await context.bot.get_chat(chat_id)
                chat_title = chat.title if hasattr(chat, 'title') else "Private Chat"
                
                # Add the chat ID to the list
                TARGET_CHATS.append(chat_id)
                save_chats()
                
                await update.message.reply_text(f"Added chat: {chat_title} ({chat_id}) to the forwarding list.")
                logger.info(f"Manually added chat: {chat_title} ({chat_id})")
            else:
                # Force add without verification
                TARGET_CHATS.append(chat_id)
                save_chats()
                
                await update.message.reply_text(
                    f"Force-added chat ID: {chat_id} to the forwarding list without verification.\n"
                    f"Note: If the bot is not actually a member of this chat, messages won't be forwarded."
                )
                logger.info(f"Force-added chat ID: {chat_id} without verification")
        except Exception as e:
            if force_add:
                # If force add was requested but we still tried to verify first
                TARGET_CHATS.append(chat_id)
                save_chats()
                
                await update.message.reply_text(
                    f"Chat {chat_id} appears inaccessible (Error: {str(e)}), but was added anyway as requested.\n"
                    f"Note: If the bot is not actually a member of this chat, messages won't be forwarded."
                )
                logger.info(f"Force-added inaccessible chat: {chat_id}")
            else:
                # Suggest using the force option
                await update.message.reply_text(
                    f"Failed to get information about chat {chat_id}. "
                    f"The chat may not exist or the bot may not have access to it.\n"
                    f"Error: {str(e)}\n\n"
                    f"If you're sure the bot is in this group, try adding 'force' to skip verification:\n"
                    f"/add_chat {chat_id} force"
                )
                logger.error(f"Failed to get information about chat {chat_id}: {e}")
    except ValueError:
        await update.message.reply_text("Invalid chat ID. Please provide a valid integer ID.")

async def track_chat_member_updates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Track when the bot is added to or removed from a chat"""
    global TARGET_CHATS  # Declare global at the beginning of the function
    
    chat = update.effective_chat
    if not chat:
        return
    
    if chat.type in [Chat.GROUP, Chat.SUPERGROUP, Chat.CHANNEL]:
        # Get the updated status for the bot
        my_chat_member = update.my_chat_member
        if not my_chat_member:
            return
        
        # Check if the bot was the user whose status changed
        if my_chat_member.new_chat_member.user.id == context.bot.id:
            new_status = my_chat_member.new_chat_member.status
            chat_id = chat.id
            
            if new_status in ['member', 'administrator']:
                # Bot was added to a group
                if chat_id not in TARGET_CHATS:
                    TARGET_CHATS.append(chat_id)
                    logger.info(f"Bot was added to group: {chat.title} ({chat_id})")
                    
                    # Save updated chat list
                    save_chats()
                    
                    # Notify owner if set
                    if OWNER_ID:
                        try:
                            await context.bot.send_message(
                                chat_id=OWNER_ID,
                                text=f"I was added to a new group: {chat.title} ({chat_id})"
                            )
                        except Exception as e:
                            logger.error(f"Failed to notify owner: {e}")
            
            elif new_status in ['left', 'kicked']:
                # Bot was removed from a group
                if chat_id in TARGET_CHATS:
                    TARGET_CHATS.remove(chat_id)
                    logger.info(f"Bot was removed from group: {chat.title} ({chat_id})")
                    
                    # Save updated chat list
                    save_chats()
                    
                    # Notify owner if set
                    if OWNER_ID:
                        try:
                            await context.bot.send_message(
                                chat_id=OWNER_ID,
                                text=f"I was removed from group: {chat.title} ({chat_id})"
                            )
                        except Exception as e:
                            logger.error(f"Failed to notify owner: {e}")

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward a message to all target chats"""
    global TARGET_CHATS  # Declare global at the beginning of the function
    
    user_id = update.effective_user.id
    message = update.message
    chat_id = update.effective_chat.id
    
    # Add the current chat to TARGET_CHATS if it's a group and not already there
    if chat_id != user_id and chat_id not in TARGET_CHATS:  # If it's not a private chat
        TARGET_CHATS.append(chat_id)
        if user_id == OWNER_ID:
            logger.info(f"Added new chat to forward list: {chat_id}")
            # Save the updated chat list
            save_chats()
    
    # Only forward messages from the owner in private chat
    if user_id != OWNER_ID or chat_id != user_id:
        return
    
    if not TARGET_CHATS:
        await update.message.reply_text("I'm not in any groups yet. Add me to the groups where you want to forward messages.")
        return
    
    success_count = 0
    failed_chats = []
    list_changed = False
    
    for target_chat_id in list(TARGET_CHATS):  # Use a copy of the list since we might modify it
        try:
            # Forward the message to the target chat
            await context.bot.copy_message(
                chat_id=target_chat_id,
                from_chat_id=chat_id,
                message_id=message.message_id
            )
            success_count += 1
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"Failed to forward message to {target_chat_id}: {e}")
            
            # Remove the chat if we can't send messages to it anymore
            if any(reason in error_msg for reason in ["blocked", "not found", "chat not found", "kicked", "left"]):
                TARGET_CHATS.remove(target_chat_id)
                failed_chats.append(f"{target_chat_id} (removed)")
                list_changed = True
            else:
                failed_chats.append(f"{target_chat_id}")
    
    # Save chat list if it was changed
    if list_changed:
        save_chats()
    
    status_msg = f"Message forwarded to {success_count}/{len(TARGET_CHATS) + (len(failed_chats) if list_changed else 0)} chats."
    if failed_chats:
        status_msg += f"\nFailed to send to: {', '.join(failed_chats)}"
    
    await update.message.reply_text(status_msg)

def save_chats():
    """Save current chat list to file for persistence"""
    chat_file = "bot_chats.txt"
    try:
        with open(chat_file, "w") as f:
            for chat_id in TARGET_CHATS:
                f.write(f"{chat_id}\n")
        logger.info(f"Saved {len(TARGET_CHATS)} chats to {chat_file}")
    except Exception as e:
        logger.error(f"Error saving chats: {e}")

async def startup_scan(application: Application) -> None:
    """Scan for groups when the bot starts"""
    global TARGET_CHATS  # Declare global at the very beginning of the function
    
    bot = application.bot
    logger.info("Starting initial group scan...")
    
    # Unfortunately, Telegram doesn't provide an API to get all chats a bot is in
    # We'll store chat IDs in a simple file for persistence between restarts
    chat_file = "bot_chats.txt"
    stored_chats = set()
    
    # Load stored chat IDs if available
    if os.path.exists(chat_file):
        try:
            with open(chat_file, "r") as f:
                for line in f:
                    try:
                        chat_id = int(line.strip())
                        stored_chats.add(chat_id)
                    except ValueError:
                        continue
            
            logger.info(f"Loaded {len(stored_chats)} stored chat IDs")
        except Exception as e:
            logger.error(f"Error loading stored chats: {e}")
    
    # Clear the current target chats list
    TARGET_CHATS.clear()
    
    # Check each stored chat if the bot is still a member
    for chat_id in stored_chats:
        try:
            # Verify the bot is still a member of this chat
            chat = await bot.get_chat(chat_id)
            member = await bot.get_chat_member(chat_id, bot.id)
            
            if member.status not in ['left', 'kicked']:
                TARGET_CHATS.append(chat_id)
                chat_name = chat.title if chat.type != Chat.PRIVATE else "Private chat"
                logger.info(f"Verified membership in: {chat_name} ({chat_id})")
        except Exception as e:
            # Keep the chat in the list even if verification fails
            TARGET_CHATS.append(chat_id)
            logger.error(f"Failed to verify chat {chat_id}, but keeping it: {e}")
    
    logger.info(f"Initial scan complete. Bot is a member of {len(TARGET_CHATS)} groups.")
    
    # If there's an owner ID set, send a notification
    if OWNER_ID:
        try:
            await bot.send_message(
                chat_id=OWNER_ID,
                text=f"Bot started and initialized with {len(TARGET_CHATS)} groups."
            )
        except Exception as e:
            logger.error(f"Failed to notify owner on startup: {e}")

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("chats", list_chats))
    application.add_handler(CommandHandler("refresh", refresh_chats))
    application.add_handler(CommandHandler("scan", active_scan_for_groups))
    application.add_handler(CommandHandler("add_chat", manual_add_chat))
    application.add_handler(CommandHandler("deep_scan", deep_scan_for_groups))
    application.add_handler(CommandHandler("chatid", get_chat_id))

    # Track chat member updates (when bot is added to or removed from groups)
    application.add_handler(ChatMemberHandler(track_chat_member_updates))

    # Message handler for forwarding messages
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_message))

    # Run startup scan when the bot starts
    application.post_init = startup_scan
    
    # Log the owner ID at startup for debugging
    logger.info(f"Starting bot with owner ID: {OWNER_ID}")
    
    # Run the bot until the user presses Ctrl-C
    try:
        application.run_polling()
    finally:
        # Save chat list when the bot shuts down
        save_chats()

if __name__ == "__main__":
    main()