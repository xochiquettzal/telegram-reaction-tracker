import asyncio
import datetime
import os
import re # Added import for sanitization
import time # Added import for download speed calculation
from telethon import TelegramClient
from telethon.tl.types import Message, DocumentAttributeAnimated # Added import

# Telegram API Settings - Load from .env file
API_ID = int(os.getenv('API_ID', 0))  # Default value set to 0
API_HASH = os.getenv('API_HASH', '')  # Default value set to empty string
SESSION_NAME = 'session'  # Session file name

# Helper function to sanitize filenames
def sanitize_filename(name):
    """Sanitizes a string to be safe for use as a filename or directory name."""
    # Replace invalid characters with underscores
    s = re.sub(r'[^\w.-]', '_', name)
    # Remove leading/trailing whitespace
    s = s.strip()
    # Limit length (optional, but good practice)
    s = s[:200] # Limit to 200 characters
    return s

# Dictionary to store download progress info per message ID
download_progress = {}

async def download_progress_callback(current, total, message_id):
    """Callback function to show download progress and speed."""
    if message_id not in download_progress:
        download_progress[message_id] = {'start_time': time.time(), 'last_downloaded': 0}

    elapsed_time = time.time() - download_progress[message_id]['start_time']
    downloaded_since_last = current - download_progress[message_id]['last_downloaded']
    download_progress[message_id]['last_downloaded'] = current

    speed_bytes_per_sec = downloaded_since_last / (elapsed_time if elapsed_time > 0 else 1e-9) # Avoid division by zero

    # Convert to human-readable format
    if speed_bytes_per_sec < 1024:
        speed_str = f"{speed_bytes_per_sec:.2f} B/s"
    elif speed_bytes_per_sec < 1024 * 1024:
        speed_str = f"{speed_bytes_per_sec / 1024:.2f} KB/s"
    else:
        speed_str = f"{speed_bytes_per_sec / (1024 * 1024):.2f} MB/s"

    # Calculate percentage
    percent = (current / total) * 100 if total > 0 else 0

    print(f"Downloading message {message_id}: {current}/{total} bytes ({percent:.2f}%) Speed: {speed_str}")

    # Clean up when download is complete
    if current == total and message_id in download_progress:
        del download_progress[message_id]

# --- New Helper Function for Concurrent Download ---
async def download_single_media(client, message, folder_path, message_id, progress_queue, total_media_to_process, allowed_extensions, size_limit_bytes, large_media_links, entity):
    """Downloads media for a single message and updates progress."""
    media_processed_count = 0 # Local counter for this task
    try:
        if message.media:
            file_size = None
            file_extension = None
            is_supported_media = False

            if hasattr(message.media, 'document') and message.media.document:
                if hasattr(message.media.document, 'size'):
                    file_size = message.media.document.size

                # Check for video/mp4 documents, which can include GIFs
                if message.media.document.mime_type == 'video/mp4':
                    file_extension = 'mp4' # Save video/mp4 as MP4
                    is_supported_media = True
                elif hasattr(message.media.document, 'attributes'):
                    for attr in message.media.document.attributes:
                        if hasattr(attr, 'file_name'):
                            _, ext = os.path.splitext(attr.file_name)
                            if ext:
                                file_extension = ext.lower().lstrip('.')
                                if file_extension in allowed_extensions:
                                    is_supported_media = True
                                break

            elif hasattr(message.media, 'photo') and message.media.photo:
                file_extension = 'jpg'
                is_supported_media = True
                if hasattr(message.media.photo, 'sizes') and message.media.photo.sizes:
                    largest_size = max(message.media.photo.sizes, key=lambda s: getattr(s, 'size', 0))
                    file_size = getattr(largest_size, 'size', None)

            if is_supported_media:
                if file_size is not None and file_size > size_limit_bytes:
                    link = build_message_link(entity, message_id)
                    large_media_links.append(f"Message ID: {message_id}, Link: {link}, Size: {file_size} bytes")
                    print(f"Skipping large media for message {message_id} ({file_size} bytes). Link added to list.")
                    # Even if skipped, count it as processed for the overall progress
                    media_processed_count = 1
                else:
                    print(f"Downloading media for message {message_id}...")
                    try:
                        if not file_extension:
                            file_extension = 'bin' # Fallback extension
                        file_name = f"{message_id}.{file_extension}"
                        await client.download_media(
                            message,
                            file=os.path.join(folder_path, file_name),
                            progress_callback=lambda current, total: download_progress_callback(current, total, message_id)
                        )
                        print(f"Downloaded media for message {message_id}.")
                        media_processed_count = 1 # Mark as processed after successful download
                    except Exception as download_e:
                        print(f"Error downloading media for message {message_id}: {download_e}")
                        # Still count as processed even if download failed, to advance progress bar
                        media_processed_count = 1
            else:
                print(f"Message {message_id} has media but not a supported type or extension: {file_extension}")
                media_processed_count = 1 # Count as processed
        else:
            print(f"Message {message_id} has no media.")
            media_processed_count = 1 # Count as processed

    except Exception as e:
        print(f"Error processing message {message_id} for download: {e}")
        media_processed_count = 1 # Count as processed on error

    # Send progress update ONLY if this message was actually processed (downloaded, skipped, or errored)
    # This requires careful management of the counter across tasks.
    # A better approach might be to update progress after asyncio.gather finishes.
    # Let's stick to updating progress after gather for simplicity and accuracy.
    # Return True if processed (download attempted/skipped), False otherwise.
    return media_processed_count > 0 # Return True if this message was handled

# --- End Helper Function ---


async def count_reactions(msg):
    """Return the total number of reactions in a message."""
    if not msg.reactions:
        return 0
    return sum(r.count for r in msg.reactions.results)

async def fetch_reaction_stats_async(chat_identifier, progress_queue, task_data, period_days=None, reaction_filter=False, download_limit=None):
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

            # Apply reaction filter if enabled
            if reaction_filter and reactions == 0:
                continue # Skip messages with no reactions if filtering

            if reactions > 0 or not reaction_filter: # Include if reactions > 0 or filter is off
                # Store message ID and text preview with the count
                preview = (msg.message or msg.text or "[Media/Empty]")
                messages.append({
                    'id': msg.id,
                    'reactions': reactions,
                    'preview': preview.replace('\n', ' ')[:100],
                    'link': build_message_link(entity, msg.id) # Add the link
                })

            if scanned % 50 == 0:  # Progress update every 50 messages
                progress_queue.put({'type': 'progress', 'scanned': scanned})
                await asyncio.sleep(0.1)  # Brief yield control

        print(f"Scan complete. Total scanned: {scanned}, Found matching criteria: {len(messages)}")
        progress_queue.put({'type': 'progress', 'scanned': scanned})  # Final progress update

        # Sort messages by reaction count in descending order
        sorted_messages = sorted(messages, key=lambda x: x['reactions'], reverse=True)

        # Apply download limit after sorting
        if download_limit is not None:
            sorted_messages = sorted_messages[:download_limit]
            print(f"Applied download limit. Processing top {len(sorted_messages)} messages.")

        # Send a message to the frontend indicating the start of media processing
        total_media_to_process = len(sorted_messages) # Process all messages after limit
        # Only proceed with media processing if reaction filter is enabled
        if reaction_filter:
            print(f"Starting media processing for {total_media_to_process} messages.")
            progress_queue.put({'type': 'media_phase', 'total_media': total_media_to_process})

            # --- Start Media Download and Link Logging ---
            download_dir = "downloads"
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
            # Sanitize chat_identifier for use in folder name
            # Use sanitized chat title if available, otherwise use sanitized chat_identifier
            folder_name = f"{sanitize_filename(getattr(entity, 'title', str(chat_identifier)))}_{timestamp}" # Modified line
            folder_path = os.path.join(download_dir, folder_name) # Path relative to CWD, will create in CWD/downloads

            # Ensure the downloads directory exists and the specific search subfolder
            os.makedirs(folder_path, exist_ok=True)

            large_media_links = []
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi', 'mkv']
            size_limit_bytes = 250 * 1024 * 1024

            print(f"Preparing to process top {total_media_to_process} messages for media download...")

            download_tasks = []
            media_processed_count = 0 # Initialize counter for progress updates

            # Fetch message objects first (can also be concurrent, but let's keep it simple for now)
            message_ids_to_process = [msg_data['id'] for msg_data in sorted_messages[:total_media_to_process]]
            fetched_message_objects = {}
            if message_ids_to_process:
                try:
                    # Fetch messages in batches if needed, but Telethon handles lists well
                    messages_list = await client.get_messages(entity, ids=message_ids_to_process)
                    if messages_list:
                        for msg_obj in messages_list:
                            if msg_obj: # Ensure message object is not None
                               fetched_message_objects[msg_obj.id] = msg_obj
                except Exception as fetch_err:
                    print(f"Error fetching message batch: {fetch_err}")
                    # Decide how to handle partial fetch failure, maybe proceed with fetched ones

            print(f"Fetched {len(fetched_message_objects)} message objects out of {total_media_to_process}.")

            # Create download tasks for fetched messages
            for message_id in message_ids_to_process:
                message = fetched_message_objects.get(message_id)
                if message:
                     # Create a task for each message download attempt
                     task = asyncio.create_task(
                         download_single_media(
                             client, message, folder_path, message_id,
                             progress_queue, total_media_to_process, # Pass queue and total
                             allowed_extensions, size_limit_bytes, large_media_links, entity
                         )
                     )
                     download_tasks.append(task)
                else:
                     print(f"Skipping message ID {message_id} as it could not be fetched.")
                     # Increment processed count even if skipped/failed fetch
                     media_processed_count += 1
                     progress_queue.put({'type': 'media_progress', 'processed_count': media_processed_count, 'total_media': total_media_to_process})


            # Run download tasks sequentially
            if download_tasks:
                print(f"Starting sequential download of {len(download_tasks)} media items...")
                media_processed_count = 0 # Reset counter for sequential processing
                for task in download_tasks:
                    try:
                        result = await task
                        if result is True: # Our helper function returns True if processed
                            media_processed_count += 1
                    except Exception as e:
                        print(f"A download task failed: {e}")
                        media_processed_count += 1 # Count errors as processed for progress bar completion

                    # Update progress after each task completes
                    progress_queue.put({'type': 'media_progress', 'processed_count': media_processed_count, 'total_media': total_media_to_process})
                    await asyncio.sleep(0.1) # Brief yield control between downloads

                print(f"Finished processing {media_processed_count}/{total_media_to_process} media messages.")

            else:
                print("No media download tasks were created.")


            if large_media_links:
                # Save links file in the specific search subfolder
                links_file_path = os.path.join(folder_path, "large_media_links.txt")
                with open(links_file_path, "w") as f:
                    for link_info in large_media_links:
                        f.write(link_info + "\n")
                print(f"Large media links saved to {links_file_path}")

            print("Media download and link logging complete for top messages.")
            # --- End Media Download and Link Logging ---
        else:
            print("Reaction filter is off. Skipping media download.")
            # Send a media phase complete message even if skipping download
            progress_queue.put({'type': 'media_phase', 'total_media': 0}) # Indicate 0 media to process

        # Send complete message after all processing is done
        progress_queue.put({'type': 'complete'})

        task_data['results'] = sorted_messages # Keep the sorted results for the original purpose
        task_data['entity'] = entity  # Store entity info for link building
        task_data['scanned_count'] = scanned
        print(f"Results saved: {len(sorted_messages)} messages.")


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

def run_fetch_in_background(chat_identifier, progress_queue, task_data, period_days=None, reaction_filter=False, download_limit=None):
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
            fetch_reaction_stats_async(chat_identifier, progress_queue, task_data, period_days, reaction_filter, download_limit)
        )
        loop.close()

        if error:
            task_data['error'] = error
        else:
            # fetch_reaction_stats_async now handles sorting and limiting
            task_data['results'] = messages # messages is already sorted and limited
            task_data['entity'] = entity  # Store entity info for link building
            task_data['scanned_count'] = scanned
            print(f"Results saved: {len(messages)} messages.")

    except Exception as e:
        task_data['error'] = f"Error in background thread: {e}"
        print(task_data['error'])
        progress_queue.put({'type': 'error', 'message': task_data['error']})
    finally:
        task_data['is_running'] = False
        print("Background task ended.")
