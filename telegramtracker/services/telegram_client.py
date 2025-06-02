import asyncio
import datetime
import os
import re
import time
from telethon import TelegramClient
from telethon.tl.types import Message, DocumentAttributeAnimated

# Telegram API Settings - Load from .env file
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
SESSION_NAME = 'session'

# Helper function to sanitize filenames
def sanitize_filename(name):
    """Sanitizes a string to be safe for use as a filename or directory name."""
    s = re.sub(r'[^\w.-]+', '_', name)
    s = s.strip('_.')
    s = s[:200]
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

    speed_bytes_per_sec = downloaded_since_last / (elapsed_time if elapsed_time > 0 else 1e-9)

    if speed_bytes_per_sec < 1024:
        speed_str = f"{speed_bytes_per_sec:.2f} B/s"
    elif speed_bytes_per_sec < 1024 * 1024:
        speed_str = f"{speed_bytes_per_sec / 1024:.2f} KB/s"
    else:
        speed_str = f"{speed_bytes_per_sec / (1024 * 1024):.2f} MB/s"

    percent = (current / total) * 100 if total > 0 else 0

    print(f"Downloading message {message_id}: {current}/{total} bytes ({percent:.2f}%) Speed: {speed_str}")

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
        return [original_post] if original_post.media is not None else []

    search_ids = list(range(original_post.id - max_amp, original_post.id + max_amp + 1))
    
    posts = await client.get_messages(chat, ids=search_ids)
    
    media_posts = []
    for post in posts:
        if post is not None and post.grouped_id == original_post.grouped_id and post.media is not None:
            media_posts.append(post)
            
    found_original = any(p.id == original_post.id for p in media_posts)
    if not found_original and original_post.media is not None:
         original_in_group = await client.get_messages(chat, ids=original_post.id)
         if original_in_group and original_in_group.grouped_id == original_post.grouped_id:
              media_posts.append(original_in_group)

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

async def fetch_reaction_stats_async(chat_identifier, task_manager, period_days=None, reaction_filter=False, download_limit=None):
    """Asynchronous function to fetch reaction statistics and report progress via task_manager."""
    client = None
    messages = []
    scanned = 0

    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        print("Connecting to Telegram...")
        await client.connect()

        if not await client.is_user_authorized():
            task_manager.set_task_error("User not authorized. Please run a script to login first.")
            print(task_manager.error)
            return

        print(f"Getting chat info: {chat_identifier}")
        try:
            task_manager.entity = await client.get_entity(chat_identifier)
            print(f"Chat found: {getattr(task_manager.entity, 'title', chat_identifier)}")
        except ValueError as e:
            error_msg = f"Chat not found: {chat_identifier}. Please check username or ID. Error: {e}"
            task_manager.set_task_error(error_msg)
            print(error_msg)
            return
        except Exception as e:
            error_msg = f"Unexpected error getting chat: {e}"
            task_manager.set_task_error(error_msg)
            print(error_msg)
            return

        if period_days:
            since_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=period_days)
            print(f"Getting messages since: {since_date}")
        else:
            since_date = None
            print("Getting all messages.")

        async for msg in client.iter_messages(task_manager.entity, offset_date=since_date, reverse=True):
            scanned += 1
            reactions = await count_reactions(msg)

            if reaction_filter and reactions == 0:
                continue

            if reactions > 0 or not reaction_filter:
                preview = (msg.message or msg.text or "[Media/Empty]")
                messages.append({
                    'id': msg.id,
                    'reactions': reactions,
                    'preview': preview.replace('\n', ' ')[:100],
                    'link': build_message_link(task_manager.entity, msg.id)
                })

            if scanned % 50 == 0:
                task_manager.progress_queue.put({'type': 'progress', 'scanned': scanned})
                await asyncio.sleep(0.1)

        print(f"Scan complete. Total scanned: {scanned}, Found matching criteria: {len(messages)}")
        task_manager.progress_queue.put({'type': 'progress', 'scanned': scanned})

        sorted_messages = sorted(messages, key=lambda x: x['reactions'], reverse=True)

        final_message_ids_to_process = set()
        if download_limit is not None:
            print(f"Applying download limit: {download_limit}")
            selected_entries_count = 0
            processed_group_ids = set()
            processed_message_ids = set()

            for msg_data in sorted_messages:
                if selected_entries_count >= download_limit:
                    print(f"Download limit of {download_limit} reached.")
                    break

                message_id = msg_data['id']
                if message_id in processed_message_ids:
                    continue

                message_obj = None
                try:
                    # Use task_manager.entity here
                    message_obj = await client.get_messages(task_manager.entity, ids=message_id)
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
                        try:
                            # Use task_manager.entity here
                            media_posts_in_group = await _get_media_posts_in_group(client, task_manager.entity, message_obj)
                            group_message_ids = {post.id for post in media_posts_in_group}
                            final_message_ids_to_process.update(group_message_ids)
                            processed_message_ids.update(group_message_ids)
                            print(f"  Added {len(group_message_ids)} messages from group {group_id} to download list.")
                        except Exception as group_fetch_err:
                             print(f"  Warning: Error fetching full group {group_id}: {group_fetch_err}. Adding only original message {message_id}.")
                             final_message_ids_to_process.add(message_id)
                             processed_message_ids.add(message_id)
                else:
                    print(f"Selecting standalone message {message_id} (Entry {selected_entries_count + 1}/{download_limit})")
                    final_message_ids_to_process.add(message_id)
                    processed_message_ids.add(message_id)
                    selected_entries_count += 1

            print(f"Final list of message IDs to process for media: {len(final_message_ids_to_process)}")
        else:
            final_message_ids_to_process = {msg['id'] for msg in sorted_messages}
            print(f"No download limit applied. Processing all {len(final_message_ids_to_process)} messages for media.")

        # --- Media Processing Section ---
        total_media_items = 0
        media_paths_map = {}
        folder_name = None

        # Media download only happens if reaction_filter is TRUE
        if reaction_filter and final_message_ids_to_process:
            # --- Start Media Download and Link Logging ---
            download_dir = "downloads"
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
            # Use task_manager.entity here for folder name
            folder_name = f"{sanitize_filename(getattr(task_manager.entity, 'title', str(chat_identifier)))}_{timestamp}"
            folder_path = os.path.join(download_dir, folder_name)
            os.makedirs(folder_path, exist_ok=True)

            large_media_links = []
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi', 'mkv']
            size_limit_bytes = 250 * 1024 * 1024

            message_ids_to_fetch_media = list(final_message_ids_to_process)
            fetched_message_objects = {}
            if message_ids_to_fetch_media:
                print(f"Fetching {len(message_ids_to_fetch_media)} message objects for media download...")
                batch_size = 100
                for i in range(0, len(message_ids_to_fetch_media), batch_size):
                    batch_ids = message_ids_to_fetch_media[i:i + batch_size]
                    try:
                        # Use task_manager.entity here
                        messages_list = await client.get_messages(task_manager.entity, ids=batch_ids)
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

            message_groups = {}
            processed_ids_for_grouping = set()
            
            print("Identifying media groups...")
            for message_id in message_ids_to_fetch_media:
                if message_id not in fetched_message_objects:
                    print(f"Skipping message ID {message_id} for grouping: Not fetched.")
                    continue
                
                if message_id in processed_ids_for_grouping:
                    continue

                message_obj = fetched_message_objects[message_id]
                
                try:
                    # Use task_manager.entity here
                    media_posts = await _get_media_posts_in_group(client, task_manager.entity, message_obj)
                    
                    if media_posts:
                        group_key = media_posts[0].id if not getattr(message_obj, 'grouped_id', None) else getattr(message_obj, 'grouped_id')

                        if group_key not in message_groups:
                             message_groups[group_key] = media_posts
                             print(f"  Group {group_key}: Identified {len(media_posts)} media items.")
                             for post in media_posts:
                                 processed_ids_for_grouping.add(post.id)
                    else:
                        print(f"  Message {message_id}: No downloadable media found by _get_media_posts_in_group.")
                        processed_ids_for_grouping.add(message_id)

                except Exception as e:
                    print(f"Error processing message {message_id} for grouping: {e}")
                    processed_ids_for_grouping.add(message_id)

            total_media_items = sum(len(msgs) for msgs in message_groups.values())
            print(f"Identified {len(message_groups)} groups/messages with a total of {total_media_items} media items to download.")
            task_manager.progress_queue.put({'type': 'media_phase', 'total_media': total_media_items})

            download_tasks = []
            media_paths_map = {}

            for group_key, messages_in_group in message_groups.items():
                messages_in_group.sort(key=lambda msg: msg.id)
                message_ids_in_group = [msg.id for msg in messages_in_group]
                
                for msg_id in message_ids_in_group:
                     if msg_id not in media_paths_map: media_paths_map[msg_id] = []

                for i, message in enumerate(messages_in_group):
                    message_id = message.id
                    try:
                        is_supported_media, file_extension, file_size = detect_media_type_and_size(message)

                        if is_supported_media:
                            if file_size is not None and file_size > size_limit_bytes:
                                link = build_message_link(task_manager.entity, message_id)
                                large_media_links.append(f"Message ID: {message_id}, Link: {link}, Size: {file_size} bytes")
                                print(f"Skipping large media for message {message_id} ({file_size} bytes).")
                            else:
                                print(f"Creating download task for media {i+1}/{len(messages_in_group)} in group {group_key} (Msg ID: {message_id})...")
                                if not file_extension: file_extension = 'bin'
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
                                download_tasks.append((task, message_ids_in_group, relative_path))
                        else:
                            if message.media:
                                 print(f"Message {message_id} has unsupported media type.")

                    except Exception as e:
                        print(f"Error processing message {message_id} for download task creation: {e}")

            if download_tasks:
                print(f"Starting concurrent download of {len(download_tasks)} media items...")
                results = await asyncio.gather(*[task for task, _, _ in download_tasks], return_exceptions=True)

                successful_downloads = 0; failed_downloads = 0
                temp_group_paths = {}

                for i, result in enumerate(results):
                    task, message_ids_in_group, relative_path = download_tasks[i]
                    group_identifier = tuple(sorted(message_ids_in_group))

                    if group_identifier not in temp_group_paths: temp_group_paths[group_identifier] = []

                    if isinstance(result, Exception):
                        print(f"Download task for media {relative_path} failed: {result}")
                        failed_downloads += 1
                    else:
                        if result is not None:
                             print(f"Download task for media {relative_path} completed.")
                             successful_downloads += 1
                             temp_group_paths[group_identifier].append(relative_path)
                        else:
                             print(f"Download task for media {relative_path} returned None (likely skipped or internal issue).")
                             failed_downloads += 1

                    task_manager.progress_queue.put({'type': 'media_progress', 'processed_count': successful_downloads + failed_downloads, 'total_media': total_media_items})

                for group_identifier, paths in temp_group_paths.items():
                    paths.sort()
                    for msg_id in group_identifier:
                         media_paths_map[msg_id] = paths

                print(f"Finished processing media. Successful: {successful_downloads}, Failed/Skipped: {failed_downloads}, Total Tasks: {len(download_tasks)}")
                final_processed_count = successful_downloads + failed_downloads
                task_manager.progress_queue.put({'type': 'media_progress', 'processed_count': final_processed_count, 'total_media': total_media_items})
            else:
                print("No media download tasks were created.")
                task_manager.progress_queue.put({'type': 'media_phase', 'total_media': total_media_items})
                task_manager.progress_queue.put({'type': 'media_progress', 'processed_count': 0, 'total_media': 0})

            for msg_data in sorted_messages:
                message_id = msg_data['id']
                msg_data['media_paths'] = media_paths_map.get(message_id, [])

            if large_media_links:
                links_file_path = os.path.join(folder_path, "large_media_links.txt")
                with open(links_file_path, "w") as f:
                    for link_info in large_media_links: f.write(link_info + "\n")
                print(f"Large media links saved to {links_file_path}")

            print("Media download and link logging complete.")
            # Set the download folder path on the task manager
            task_manager.download_folder_path = folder_name
        else:
            # If reaction_filter is off or no messages to process, skip media download
            print("Reaction filter is off or no messages selected for media processing. Skipping media download.")
            task_manager.progress_queue.put({'type': 'media_phase', 'total_media': 0})
            task_manager.progress_queue.put({'type': 'media_progress', 'processed_count': 0, 'total_media': 0})
            for msg_data in sorted_messages:
                msg_data['media_paths'] = []
            task_manager.download_folder_path = None # Ensure path is None if no downloads


        task_manager.progress_queue.put({'type': 'complete', 'scanned': scanned})

        task_manager.results = sorted_messages
        task_manager.scanned_count = scanned
        # download_folder_path is already set above
        print(f"Results prepared: {len(sorted_messages)} messages. Download path: {task_manager.download_folder_path}")


    except Exception as e:
        error_msg = f"Error retrieving messages: {e}"
        print(f"Error: {error_msg}")
        task_manager.set_task_error(error_msg)
    finally:
        if client and client.is_connected():
            print("Disconnecting client...")
            await client.disconnect()
        print("Async fetch task completed processing.")

def build_message_link(chat, msg_id):
    """Create a t.me link for a message."""
    if not chat:
        return "#"

    if getattr(chat, 'username', None):
        return f"https://t.me/{chat.username}/{msg_id}"

    cid = str(chat.id)

    if cid.startswith('-100'):
        cid = cid[4:]
    elif cid.startswith('-'):
         cid = cid[1:]

    return f"https://t.me/c/{cid}/{msg_id}"

def run_fetch_in_background(chat_identifier, task_manager, period_days=None, reaction_filter=False, download_limit=None):
    """Run async fetch function in background, using the TaskManager instance."""
    print("Starting background task...")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        loop.run_until_complete(
            fetch_reaction_stats_async(chat_identifier, task_manager, period_days, reaction_filter, download_limit)
        )
        loop.close()

        if task_manager.error:
            print(f"Background task completed with error: {task_manager.error}")
        else:
            print(f"Background task finished processing. Results count: {len(task_manager.results if task_manager.results else [])}")

    except Exception as e:
        error_msg = f"Critical error in background thread execution: {e}"
        print(error_msg)
        if not task_manager.error:
            task_manager.set_task_error(error_msg)
    finally:
        task_manager.is_running = False
        # Check if the queue is empty and no error occurred, but no 'complete' message was sent
        # This might indicate an unexpected exit in the async function
        queue_empty = task_manager.progress_queue.empty()
        last_item_type = None
        if not queue_empty:
             # This is tricky without consuming the item. A simple check might be enough.
             # For robustness, the async function should guarantee a final message.
             pass 

        if not task_manager.error and queue_empty: # Simplified check: if no error and queue empty, assume completion or issue
             # If the async function guarantees putting 'complete' or 'error', this check might not be needed.
             # However, as a safeguard:
             print("Background task wrapper: No error and queue empty, ensuring 'complete' or 'error' was sent.")
             # We cannot reliably know the final state here without more complex queue inspection.
             # Relying on the async function's final queue message is preferred.
             pass

        print("Background task wrapper function ended.")

async def get_user_chats_async():
    """Asynchronous function to fetch all user chats (groups, channels, private chats)."""
    client = None
    chats_list = []
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        print("Connecting to Telegram for chat list...")
        await client.connect()

        if not await client.is_user_authorized():
            print("User not authorized. Please run a script to login first.")
            return []

        print("Fetching dialogs...")
        async for dialog in client.iter_dialogs():
            # Filter out private chats if only groups/channels are desired, or include all
            # For now, let's include all dialogs that have a title (i.e., not self-chat)
            if dialog.title:
                chat_info = {
                    'id': dialog.entity.id,
                    'title': dialog.title,
                    'username': getattr(dialog.entity, 'username', None),
                    'is_group_or_channel': dialog.is_group or dialog.is_channel
                }
                chats_list.append(chat_info)
        print(f"Found {len(chats_list)} chats.")
    except Exception as e:
        print(f"Error fetching user chats: {e}")
    finally:
        if client and client.is_connected():
            print("Disconnecting client after chat list fetch...")
            await client.disconnect()
    return chats_list
