import asyncio
import datetime
import os
from telethon import TelegramClient

# Telegram API Settings - Load from .env file
API_ID = int(os.getenv('API_ID', 0))  # Default value set to 0
API_HASH = os.getenv('API_HASH', '')  # Default value set to empty string
SESSION_NAME = 'session'  # Session file name

async def count_reactions(msg):
    """Return the total number of reactions in a message."""
    if not msg.reactions:
        return 0
    return sum(r.count for r in msg.reactions.results)

async def fetch_reaction_stats_async(chat_identifier, progress_queue, period_days=None):
    """Asynchronous function to fetch reaction statistics and report progress."""
    client = None  # Initialize client as None
    messages = []
    scanned = 0
    entity = None
    error_message = None
    
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        print("Connecting to Telegram...")
        await client.connect()
        
        if not await client.is_user_authorized():
            error_message = "User not authorized. Please run a script to login first."
            print(error_message)
            progress_queue.put({'type': 'error', 'message': error_message})
            return None, [], 0, error_message

        print(f"Getting chat info: {chat_identifier}")
        try:
            entity = await client.get_entity(chat_identifier)
            print(f"Chat found: {getattr(entity, 'title', chat_identifier)}")
        except ValueError as e:
            error_message = f"Chat not found: {chat_identifier}. Please check username or ID. Error: {e}"
            print(error_message)
            progress_queue.put({'type': 'error', 'message': error_message})
            return None, [], 0, error_message
        except Exception as e:
            error_message = f"Unexpected error getting chat: {e}"
            print(error_message)
            progress_queue.put({'type': 'error', 'message': error_message})
            return None, [], 0, error_message

        if period_days:
            since_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=period_days)
            print(f"Getting messages since: {since_date}")
        else:
            since_date = None
            print("Getting all messages.")

        # Move forward from specified date
        async for msg in client.iter_messages(entity, offset_date=since_date, reverse=True):
            scanned += 1
            reactions = await count_reactions(msg)
            if reactions > 0:
                # Store message ID and text preview with the count
                preview = (msg.message or msg.text or "[Media/Empty]")
                messages.append({
                    'id': msg.id, 
                    'reactions': reactions, 
                    'preview': preview.replace('\n', ' ')[:100]
                })

            if scanned % 50 == 0:  # Progress update every 50 messages
                progress_queue.put({'type': 'progress', 'scanned': scanned})
                await asyncio.sleep(0.1)  # Brief yield control

        print(f"Scan complete. Total scanned: {scanned}, Found with reactions: {len(messages)}")
        progress_queue.put({'type': 'progress', 'scanned': scanned})  # Final progress update
        progress_queue.put({'type': 'complete'})

    except Exception as e:
        error_message = f"Error retrieving messages: {e}"
        print(f"Error: {error_message}")
        progress_queue.put({'type': 'error', 'message': error_message})
    finally:
        if client and client.is_connected():
            print("Disconnecting client...")
            await client.disconnect()
        print("Fetch task completed.")

    return entity, messages, scanned, error_message

def build_message_link(chat, msg_id):
    """Create a t.me link for a message."""
    if not chat:
        return "#"  # No chat info
        
    # Public group or channel
    if getattr(chat, 'username', None):
        return f"https://t.me/{chat.username}/{msg_id}"
        
    # Private groups: Use internal ID
    cid = str(chat.id)
    
    # Handle different private chat ID formats if needed
    if cid.startswith('-100'):
        cid = cid[4:]  # Standard channel/supergroup format
    elif cid.startswith('-'):
         # Could be an older group, link format may be different or not work
         cid = cid[1:]  # Or handle differently if needed
         
    return f"https://t.me/c/{cid}/{msg_id}"

def run_fetch_in_background(chat_identifier, progress_queue, task_data, period_days=None):
    """Run async fetch function in background."""
    task_data['is_running'] = True
    task_data['results'] = None
    task_data['error'] = None
    task_data['entity'] = None
    
    # Clear queue for new task
    while not progress_queue.empty():
        try:
            progress_queue.get_nowait()
        except:
            break

    print("Starting background task...")
    try:
        # Create new loop for background thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        entity, messages, scanned, error = loop.run_until_complete(
            fetch_reaction_stats_async(chat_identifier, progress_queue, period_days)
        )
        loop.close()

        if error:
            task_data['error'] = error
        else:
            # Sort messages by reaction count in descending order
            sorted_messages = sorted(messages, key=lambda x: x['reactions'], reverse=True)
            task_data['results'] = sorted_messages
            task_data['entity'] = entity  # Store entity info for link building
            task_data['scanned_count'] = scanned
            print(f"Results saved: {len(sorted_messages)} messages.")
            
    except Exception as e:
        task_data['error'] = f"Error in background thread: {e}"
        print(task_data['error'])
        progress_queue.put({'type': 'error', 'message': task_data['error']})
    finally:
        task_data['is_running'] = False
        print("Background task ended.") 