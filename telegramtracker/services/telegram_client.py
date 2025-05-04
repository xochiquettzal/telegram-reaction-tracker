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
    # Replace spaces and invalid characters with underscores
    s = re.sub(r'[^\w.-]+', '_', name) # Replace one or more non-word chars (including space) with single underscore
    # Remove leading/trailing underscores and dots
    s = s.strip('_.')
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

# --- Helper Function to Get Media Posts in a Group ---
async def _get_media_posts_in_group(client, chat, original_post, max_amp=10):
    """
    Searches for Telegram posts that are part of the same group of uploads.
    The search is conducted around the id of the original post with an amplitude
    of `max_amp` both ways.
    Returns a list of [post] where each post has media and is in the same grouped_id.
    """
    if original_post.grouped_id is None:
        # If no grouped_id, return the original post if it has media
        return [original_post] if original_post.media is not None else []

    # Generate IDs to search around the original post's ID
    search_ids = list(range(original_post.id - max_amp, original_post.id + max_amp + 1))
    
    # Fetch messages using the generated IDs
    posts = await client.get_messages(chat, ids=search_ids)
    
    media_posts = []
    # Filter posts to find those belonging to the same group
    for post in posts:
        if post is not None and post.grouped_id == original_post.grouped_id and post.media is not None:
            media_posts.append(post)
            
    # Ensure the original post is included if it wasn't fetched or was None initially
    found_original = any(p.id == original_post.id for p in media_posts)
    if not found_original and original_post.media is not None:
         # Check if original_post itself is valid and has media
         original_in_group = await client.get_messages(chat, ids=original_post.id)
         if original_in_group and original_in_group.grouped_id == original_post.grouped_id:
              media_posts.append(original_in_group) # Use the freshly fetched version

    # Sort by ID to maintain order
    media_posts.sort(key=lambda p: p.id)
    
    return media_posts

# --- Helper Function for Media Type Detection ---
def detect_media_type_and_size(message):
    """Detects media type, extension, and size from a message."""
    file_size = None
    file_extension = None
    is_supported_media = False
    allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi', 'mkv']

    if hasattr(message.media, 'document') and message.media.document:
        if hasattr(message.media.document, 'size'):
            file_size = message.media.document.size

        if message.media.document.mime_type == 'video/mp4':
            file_extension = 'mp4'
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

    return is_supported_media, file_extension, file_size

# --- End Helper Functions ---


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

        # Apply download limit based on top N message entries (groups count as 1)
        final_message_ids_to_process = set()
        if download_limit is not None:
            print(f"Applying download limit: {download_limit}")
            selected_entries_count = 0
            processed_group_ids = set()
            processed_message_ids = set() # Track all message IDs belonging to selected entries

            for msg_data in sorted_messages:
                if selected_entries_count >= download_limit:
                    print(f"Download limit of {download_limit} reached.")
                    break

                message_id = msg_data['id']
                if message_id in processed_message_ids: # Skip if already part of a selected group
                    # print(f"  Skipping message {message_id} (already processed in a group).") # Optional detailed log
                    continue

                # Fetch the single message object to check its group_id
                message_obj = None
                try:
                    # Fetch individually to avoid batch errors affecting the limit logic
                    message_obj = await client.get_messages(entity, ids=message_id)
                    if not message_obj:
                         print(f"Warning: Could not fetch message {message_id} for limit check. Skipping.")
                         continue
                except Exception as fetch_err:
                    print(f"Warning: Error fetching message {message_id} for limit check: {fetch_err}. Skipping.")
                    continue

                group_id = getattr(message_obj, 'grouped_id', None)

                if group_id:
                    if group_id not in processed_group_ids:
                        print(f"Selecting group {group_id} (Entry {selected_entries_count + 1}/{download_limit})")
                        processed_group_ids.add(group_id)
                        selected_entries_count += 1
                        # Find all messages belonging to this group using _get_media_posts_in_group
                        try:
                            # Use the already fetched message_obj for efficiency
                            media_posts_in_group = await _get_media_posts_in_group(client, entity, message_obj)
                            group_message_ids = {post.id for post in media_posts_in_group}
                            final_message_ids_to_process.update(group_message_ids)
                            processed_message_ids.update(group_message_ids) # Mark all as processed
                            print(f"  Added {len(group_message_ids)} messages from group {group_id} to download list.")
                        except Exception as group_fetch_err:
                             print(f"  Warning: Error fetching full group {group_id}: {group_fetch_err}. Adding only original message {message_id}.")
                             # Add the original message ID even if group fetch failed
                             final_message_ids_to_process.add(message_id)
                             processed_message_ids.add(message_id)

                    # else: group already processed, skip this message_id as it's part of it
                else:
                    # Standalone message
                    print(f"Selecting standalone message {message_id} (Entry {selected_entries_count + 1}/{download_limit})")
                    final_message_ids_to_process.add(message_id)
                    processed_message_ids.add(message_id)
                    selected_entries_count += 1
            
            print(f"Final list of message IDs to process for media: {len(final_message_ids_to_process)}")
        else:
            # No limit, process all sorted messages
            final_message_ids_to_process = {msg['id'] for msg in sorted_messages}
            print(f"No download limit applied. Processing all {len(final_message_ids_to_process)} messages for media.")

        # --- Media Processing Section ---
        total_media_items = 0 # Initialize total media items counter
        media_paths_map = {} # Initialize media paths map
        folder_name = None # Initialize folder name

        if reaction_filter and final_message_ids_to_process:
            # --- Start Media Download and Link Logging ---
            download_dir = "downloads"
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
            folder_name = f"{sanitize_filename(getattr(entity, 'title', str(chat_identifier)))}_{timestamp}"
            folder_path = os.path.join(download_dir, folder_name)
            os.makedirs(folder_path, exist_ok=True)

            large_media_links = []
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi', 'mkv']
            size_limit_bytes = 250 * 1024 * 1024

            # Fetch message objects for the final list of messages to process
            message_ids_to_fetch_media = list(final_message_ids_to_process)
            fetched_message_objects = {}
            if message_ids_to_fetch_media:
                print(f"Fetching {len(message_ids_to_fetch_media)} message objects for media download...")
                # Fetch in smaller batches to potentially reduce errors and improve logging
                batch_size = 100
                for i in range(0, len(message_ids_to_fetch_media), batch_size):
                    batch_ids = message_ids_to_fetch_media[i:i + batch_size]
                    try:
                        messages_list = await client.get_messages(entity, ids=batch_ids)
                        if messages_list:
                            fetched_count_in_batch = 0
                            for msg_obj in messages_list:
                                if msg_obj:
                                    fetched_message_objects[msg_obj.id] = msg_obj
                                    fetched_count_in_batch += 1
                                else:
                                    print(f"Warning: Received None for a message object in batch fetch (Batch {i//batch_size + 1}).")
                            print(f"Fetched batch {i//batch_size + 1} ({fetched_count_in_batch} valid objects). Total fetched so far: {len(fetched_message_objects)}")
                        else:
                             print(f"Warning: Received empty list for message batch {i//batch_size + 1}.")
                    except Exception as fetch_err:
                        print(f"Error fetching message batch {i//batch_size + 1} (IDs: {batch_ids}): {fetch_err}. Some media might not be downloaded.")
                print(f"Finished fetching. Total successfully fetched objects: {len(fetched_message_objects)} out of {len(message_ids_to_fetch_media)} requested.")

            # Identify groups and media posts from the fetched objects
            message_groups = {} # Stores {group_key: [media_post_objects]}
            processed_ids_for_grouping = set() # Track IDs processed during grouping
            
            print("Identifying media groups...")
            for message_id in message_ids_to_fetch_media: # Iterate based on the final list determined by the limit
                if message_id not in fetched_message_objects:
                    print(f"Skipping message ID {message_id} for grouping: Not fetched.")
                    continue
                
                if message_id in processed_ids_for_grouping:
                    # Already added as part of another group found via _get_media_posts_in_group
                    continue

                message_obj = fetched_message_objects[message_id]
                
                try:
                    # Use _get_media_posts_in_group to find all related media posts
                    # This function handles both grouped and single media messages
                    media_posts = await _get_media_posts_in_group(client, entity, message_obj)
                    
                    if media_posts:
                        # Determine the group key (grouped_id or message_id for single)
                        # Use the ID of the first post in the sorted list as the key for consistency
                        group_key = media_posts[0].id if not getattr(message_obj, 'grouped_id', None) else getattr(message_obj, 'grouped_id')

                        # Store the actual media post objects found
                        if group_key not in message_groups:
                             message_groups[group_key] = media_posts
                             print(f"  Group {group_key}: Identified {len(media_posts)} media items.")
                             # Mark all posts found by _get_media_posts_in_group as processed for grouping
                             for post in media_posts:
                                 processed_ids_for_grouping.add(post.id)
                        # else: Group already identified by another member message
                    else:
                        # Original message was in the list but _get_media_posts_in_group found nothing (e.g., no media)
                        print(f"  Message {message_id}: No downloadable media found by _get_media_posts_in_group.")
                        processed_ids_for_grouping.add(message_id) # Mark as processed

                except Exception as e:
                    print(f"Error processing message {message_id} for grouping: {e}")
                    processed_ids_for_grouping.add(message_id) # Mark as processed to avoid retries

            total_media_items = sum(len(msgs) for msgs in message_groups.values())
            print(f"Identified {len(message_groups)} groups/messages with a total of {total_media_items} media items to download.")
            # Update media phase progress with the actual count of media items
            progress_queue.put({'type': 'media_phase', 'total_media': total_media_items})

            download_tasks = []
            media_paths_map = {} # Map message ID to list of media paths

            # Iterate through identified message groups and create download tasks
            for group_key, messages_in_group in message_groups.items():
                messages_in_group.sort(key=lambda msg: msg.id) # Ensure consistent order for naming
                message_ids_in_group = [msg.id for msg in messages_in_group]
                
                # Initialize map entry for all messages in this group
                for msg_id in message_ids_in_group:
                     if msg_id not in media_paths_map: media_paths_map[msg_id] = []

                for i, message in enumerate(messages_in_group):
                    message_id = message.id
                    try:
                        is_supported_media, file_extension, file_size = detect_media_type_and_size(message)

                        if is_supported_media:
                            if file_size is not None and file_size > size_limit_bytes:
                                link = build_message_link(entity, message_id)
                                large_media_links.append(f"Message ID: {message_id}, Link: {link}, Size: {file_size} bytes")
                                print(f"Skipping large media for message {message_id} ({file_size} bytes).")
                            else:
                                print(f"Creating download task for media {i+1}/{len(messages_in_group)} in group {group_key} (Msg ID: {message_id})...")
                                if not file_extension: file_extension = 'bin'
                                # Use the ID of the *first* message in the sorted group as the base filename prefix
                                group_base_id = messages_in_group[0].id
                                file_name = f"{group_base_id}_{i+1}.{file_extension}"
                                full_file_path = os.path.join(folder_path, file_name)
                                relative_path = os.path.join(folder_name, file_name).replace('\\', '/')

                                task = asyncio.create_task(
                                    client.download_media(
                                        message,
                                        file=full_file_path,
                                        progress_callback=lambda current, total, mid=message_id: download_progress_callback(current, total, mid)
                                    )
                                )
                                # Store task, the list of all message IDs in this group, and the relative path
                                download_tasks.append((task, message_ids_in_group, relative_path))
                        else:
                            # Log only if the message object actually has media attached
                            if message.media:
                                 print(f"Message {message_id} has unsupported media type.")

                    except Exception as e:
                        print(f"Error processing message {message_id} for download task creation: {e}")

            # Run download tasks concurrently
            if download_tasks:
                print(f"Starting concurrent download of {len(download_tasks)} media items...")
                results = await asyncio.gather(*[task for task, _, _ in download_tasks], return_exceptions=True)

                successful_downloads = 0; failed_downloads = 0
                temp_group_paths = {} # Store paths per group {tuple(sorted_ids): [paths]}

                for i, result in enumerate(results):
                    task, message_ids_in_group, relative_path = download_tasks[i]
                    # Use a consistent identifier for the group (sorted tuple of IDs)
                    group_identifier = tuple(sorted(message_ids_in_group))

                    if group_identifier not in temp_group_paths: temp_group_paths[group_identifier] = []

                    if isinstance(result, Exception):
                        print(f"Download task for media {relative_path} failed: {result}")
                        failed_downloads += 1
                    else:
                        # Ensure result is not None before proceeding (download_media returns path on success)
                        if result is not None:
                             print(f"Download task for media {relative_path} completed.")
                             successful_downloads += 1
                             temp_group_paths[group_identifier].append(relative_path)
                        else:
                             # Handle cases where download_media might return None without exception
                             print(f"Download task for media {relative_path} returned None (likely skipped or internal issue).")
                             failed_downloads += 1 # Count as failed/skipped

                    # Update progress based on total media items identified earlier
                    progress_queue.put({'type': 'media_progress', 'processed_count': successful_downloads + failed_downloads, 'total_media': total_media_items})

                # Assign the final list of paths to all messages in the group map
                for group_identifier, paths in temp_group_paths.items():
                    paths.sort() # Ensure consistent order of paths
                    for msg_id in group_identifier: # Iterate through all message IDs associated with this group
                         media_paths_map[msg_id] = paths # Assign the complete list of paths for the group

                print(f"Finished processing media. Successful: {successful_downloads}, Failed/Skipped: {failed_downloads}, Total Tasks: {len(download_tasks)}")
                final_processed_count = successful_downloads + failed_downloads
                # Ensure final progress update reflects total items attempted
                progress_queue.put({'type': 'media_progress', 'processed_count': final_processed_count, 'total_media': total_media_items})
            else:
                print("No media download tasks were created.")
                # Send progress updates even if no tasks, using total_media_items
                progress_queue.put({'type': 'media_phase', 'total_media': total_media_items}) # Use actual count
                progress_queue.put({'type': 'media_progress', 'processed_count': 0, 'total_media': total_media_items})

            # Associate the collected media paths with ALL messages in the original sorted_messages list
            # This ensures even messages outside the limit but part of a selected group get the paths
            for msg_data in sorted_messages:
                message_id = msg_data['id']
                # Assign paths if found in the map, otherwise empty list
                msg_data['media_paths'] = media_paths_map.get(message_id, [])

            if large_media_links:
                links_file_path = os.path.join(folder_path, "large_media_links.txt")
                with open(links_file_path, "w") as f:
                    for link_info in large_media_links: f.write(link_info + "\n")
                print(f"Large media links saved to {links_file_path}")

            print("Media download and link logging complete.")
            # --- End Media Download and Link Logging ---
        else:
            # Reaction filter is off or no messages to process
            print("Reaction filter is off or no messages selected for media processing. Skipping media download.")
            progress_queue.put({'type': 'media_phase', 'total_media': 0})
            progress_queue.put({'type': 'media_progress', 'processed_count': 0, 'total_media': 0})
            # Ensure media_paths is initialized for all messages if skipping
            for msg_data in sorted_messages:
                msg_data['media_paths'] = []


        # Send complete message after all processing is done
        progress_queue.put({'type': 'complete'})

        # Return the original sorted_messages list, now potentially annotated with media_paths
        task_data['results'] = sorted_messages
        task_data['entity'] = entity
        task_data['scanned_count'] = scanned
        # Update folder_name based on whether downloads actually happened
        task_data['download_folder_path'] = folder_name if reaction_filter and total_media_items > 0 else None
        print(f"Results prepared: {len(sorted_messages)} messages. Download path: {task_data['download_folder_path']}")


    except Exception as e:
        error_message = f"Error retrieving messages: {e}"
        print(f"Error: {error_message}")
        progress_queue.put({'type': 'error', 'message': error_message})
    finally:
        if client and client.is_connected():
            print("Disconnecting client...")
            await client.disconnect()
        print("Fetch task completed.")

    # Return the original full list of messages found, not just the ones processed for media
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
    task_data['download_folder_path'] = None # Initialize download path for the task

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
            # fetch_reaction_stats_async now handles sorting and limiting
            # It also stores results, entity, scanned_count, and download_folder_path in task_data directly
            print(f"Background task finished processing. Results count: {len(task_data.get('results', []))}")

    except Exception as e:
        task_data['error'] = f"Error in background thread: {e}"
        print(task_data['error'])
        progress_queue.put({'type': 'error', 'message': task_data['error']})
    finally:
        task_data['is_running'] = False
        print("Background task ended.")
