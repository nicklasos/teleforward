#!/usr/bin/env python
# Simple Telegram Message Forwarding Bot

import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the Telegram bot token from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("No TELEGRAM_TOKEN found in .env file")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.ERROR
)
logger = logging.getLogger(__name__)

# Store the user ID that is allowed to use the bot (the owner)
# Will be set when the owner first interacts with the bot
OWNER_ID = None
# Store target chats where messages should be forwarded
TARGET_CHATS = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    global OWNER_ID
    user_id = update.effective_user.id
    
    # Set the first user who interacts with the bot as the owner
    if OWNER_ID is None:
        OWNER_ID = user_id
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        return
    
    help_text = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/chats - List all chats where the bot is forwarding messages\n\n"
        "Any other message you send will be forwarded to all groups where I am a member."
    )
    await update.message.reply_text(help_text)

async def list_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all target chats"""
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        return
    
    if not TARGET_CHATS:
        await update.message.reply_text("No chats configured yet. Add me to groups where you want to forward messages.")
    else:
        targets = "\n".join([f"- {chat_id}" for chat_id in TARGET_CHATS])
        await update.message.reply_text(f"Messages are being forwarded to these chats:\n{targets}")

async def scan_chats(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get list of chats where bot is a member"""
    global TARGET_CHATS
    # We can't directly get a list of chats, so this is populated when the bot receives messages
    # or when /scan_chats is called from groups
    pass

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward a message to all target chats"""
    user_id = update.effective_user.id
    message = update.message
    chat_id = update.effective_chat.id
    
    # Add the current chat to TARGET_CHATS if it's a group and not already there
    if chat_id != user_id and chat_id not in TARGET_CHATS:  # If it's not a private chat
        TARGET_CHATS.append(chat_id)
        if user_id == OWNER_ID:
            logger.info(f"Added new chat to forward list: {chat_id}")
    
    # Only forward messages from the owner in private chat
    if user_id != OWNER_ID or chat_id != user_id:
        return
    
    if not TARGET_CHATS:
        await update.message.reply_text("I'm not in any groups yet. Add me to the groups where you want to forward messages.")
        return
    
    success_count = 0
    
    for target_chat_id in TARGET_CHATS:
        try:
            # Forward the message to the target chat
            await context.bot.copy_message(
                chat_id=target_chat_id,
                from_chat_id=chat_id,
                message_id=message.message_id
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to forward message to {target_chat_id}: {e}")
            # Remove the chat if we can't send messages to it anymore
            if "blocked" in str(e) or "not found" in str(e) or "chat not found" in str(e):
                TARGET_CHATS.remove(target_chat_id)
    
    await update.message.reply_text(f"Message forwarded to {success_count}/{len(TARGET_CHATS)} chats.")

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("chats", list_chats))

    # Message handler for forwarding messages
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()