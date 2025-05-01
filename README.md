# Teleforward

A Telegram bot that forwards messages from the owner to all groups where it's a member.

## Description

Teleforward is a Telegram bot that allows the owner to forward messages simultaneously to all groups where the bot is a member. The bot automatically tracks the groups it's in and provides convenient commands for managing them.

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
make install
# or
pip install -r requirements.txt
```

3. Create a `.env` file with your settings:
```
TELEGRAM_TOKEN=your_bot_token_from_botfather
OWNER_ID=your_telegram_id
```

## Usage

- Run the bot:
```bash
make run
# or
python main.py
```

- Run tests:
```bash
make test
```

- Run tests with coverage:
```bash
make test-cov
```

## Bot Commands

- `/start` - Start the bot
- `/help` - Show the list of available commands
- `/chats` - Display the list of all groups where the bot forwards messages
- `/refresh` - Update the list of groups
- `/deep_scan` - Perform a deep scan to find all groups
- `/scan` - Get instructions for helping the bot discover groups
- `/add_chat ID [force]` - Manually add a group to the forwarding list
- `/chatid` - Show the ID of the current chat

## How to Add a Group

1. **Automatic method**:
   - Add the bot to a group
   - Send any message in the group or make the bot an administrator
   - Use the `/refresh` or `/deep_scan` command in private chat with the bot

2. **Manual method**:
   - Find out the group ID by using the `/chatid` command in the desired group
   - In private chat with the bot, use `/add_chat GROUP_ID`
   - If you get an error about the group being inaccessible, use `/add_chat GROUP_ID force`

3. **Converting ID from the web version of Telegram**:
   - If the group URL looks like https://web.telegram.org/k/#-1234567890
   - Add the prefix `-100` to the number after `#`
   - Use the command `/add_chat -1001234567890 force`

## Forwarding Messages

Simply send a message to the bot in a private chat, and it will be forwarded to all groups in the list.