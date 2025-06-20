import sqlite3
import os

# Database settings
DATABASE = 'history.db'

def init_db():
    """Initialize database and create necessary tables."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            chat_identifier TEXT NOT NULL,
            chat_title TEXT,
            chat_username TEXT,
            chat_numeric_id INTEGER,
            period_days INTEGER,
            messages_found INTEGER NOT NULL,
            scanned_count INTEGER NOT NULL,
            download_folder_path TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            reaction_count INTEGER NOT NULL,
            message_preview TEXT,
            message_link TEXT NOT NULL,
            FOREIGN KEY (history_id) REFERENCES search_history (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result_id INTEGER NOT NULL,
            media_path TEXT NOT NULL,
            FOREIGN KEY (result_id) REFERENCES search_results (id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized.")

def save_search_history(original_identifier, entity, period_days, message_count, scanned_count, download_folder_path=None):
    """Save search history to database and return history_id."""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        chat_title = getattr(entity, 'title', original_identifier)
        chat_username = getattr(entity, 'username', None)
        chat_numeric_id = getattr(entity, 'id', None)

        # Add to history table
        cursor.execute('''
            INSERT INTO search_history (chat_identifier, chat_title, chat_username, chat_numeric_id, period_days, messages_found, scanned_count, download_folder_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (str(original_identifier), chat_title, chat_username, chat_numeric_id, period_days, message_count, scanned_count, download_folder_path))

        history_id = cursor.lastrowid  # Get ID of inserted record
        conn.commit()
        
        print(f"Search metadata saved to history (ID: {history_id}).")
        return history_id
    except Exception as e:
        print(f"Error saving to database: {e}")
        if conn:
            conn.rollback()  # Rollback changes in case of error
        return None
    finally:
        if conn:
            conn.close()

def delete_history_entries_by_ids(history_ids):
    """Delete multiple history entries and their related results by a list of IDs."""
    if not history_ids:
        return 0

    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;") # Ensure FK constraints are enforced

        # Convert IDs to a format suitable for SQL IN clause
        # Ensure IDs are integers to prevent SQL injection
        safe_ids = [int(id) for id in history_ids]
        id_placeholders = ','.join('?' for _ in safe_ids)

        # First delete related results
        cursor.execute(f"DELETE FROM search_results WHERE history_id IN ({id_placeholders})", safe_ids)
        results_deleted = cursor.rowcount

        # Then delete the history entries
        cursor.execute(f"DELETE FROM search_history WHERE id IN ({id_placeholders})", safe_ids)
        history_deleted = cursor.rowcount

        conn.commit()
        print(f"Bulk history deletion: {history_deleted} history records and {results_deleted} results deleted.")
        return history_deleted
    except Exception as e:
        print(f"Error deleting multiple history entries: {e}")
        if conn:
            conn.rollback()
        return 0
    finally:
        if conn:
            conn.close()

def save_search_results(history_id, messages, build_link_func):
    """Save search results to database."""
    if not history_id:
        print("Cannot save results without a valid history_id")
        return False
        
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Prepare results
        results_to_insert = []
        for msg in messages:
            link = build_link_func(msg['id'])  # Create link
            results_to_insert.append((
                history_id,
                msg['id'],
                msg['reactions'],
                msg['preview'],
                link
            ))

        # Insert results one by one to get the result_id for media
        for msg in messages:
            link = build_link_func(msg['id'])  # Create link
            cursor.execute('''
                INSERT INTO search_results (history_id, message_id, reaction_count, message_preview, message_link)
                VALUES (?, ?, ?, ?, ?)
            ''', (history_id, msg['id'], msg['reactions'], msg['preview'], link))

            result_id = cursor.lastrowid # Get ID of the inserted search_results row

            # Save media paths if available
            if 'media_paths' in msg and msg['media_paths']:
                media_to_insert = [(result_id, media_path) for media_path in msg['media_paths']]
                cursor.executemany('''
                    INSERT INTO message_media (result_id, media_path)
                    VALUES (?, ?)
                ''', media_to_insert)

        conn.commit()
        print(f"{len(messages)} results and associated media saved to database (history_id: {history_id}).")
        return True
    except Exception as e:
        print(f"Error saving results: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_search_history():
    """Return all search history."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Return rows as dictionary-like objects
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM search_history ORDER BY timestamp DESC")
    history_entries = cursor.fetchall()
    conn.close()
    return history_entries

def get_history_entry(history_id):
    """Return a specific history entry."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM search_history WHERE id = ?", (history_id,))
    history_entry = cursor.fetchone()
    conn.close()
    return history_entry

def get_history_results(history_id):
    """Return results for a specific history entry."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            sr.message_id,
            sr.reaction_count,
            sr.message_preview,
            sr.message_link,
            GROUP_CONCAT(mm.media_path) AS media_paths
        FROM search_results sr
        LEFT JOIN message_media mm ON sr.id = mm.result_id
        WHERE sr.history_id = ?
        GROUP BY sr.id
        ORDER BY sr.reaction_count DESC
    """, (history_id,))
    results = cursor.fetchall()

    # Process results to convert comma-separated media_paths string to a list
    processed_results = []
    for row in results:
        result_dict = dict(row)
        media_paths_str = result_dict['media_paths'] # Get the concatenated string
        if media_paths_str:
            # Split by comma, strip whitespace from each path, and filter out any empty strings
            paths = [path.strip() for path in media_paths_str.split(',') if path.strip()]
            result_dict['media_paths'] = paths
        else:
            # If the string is None or empty, ensure it's an empty list
            result_dict['media_paths'] = []
        processed_results.append(result_dict)

    conn.close()
    return processed_results

def delete_history_entry(history_id):
    """Delete a history entry and all related results."""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;") # Ensure FK constraints are enforced
        
        # First delete related results (which should cascade to message_media)
        cursor.execute("DELETE FROM search_results WHERE history_id = ?", (history_id,))
        results_deleted = cursor.rowcount
        
        # Then delete the history entry
        cursor.execute("DELETE FROM search_history WHERE id = ?", (history_id,))
        history_deleted = cursor.rowcount
        
        conn.commit()
        print(f"History deleted: ID {history_id} - {results_deleted} results and {history_deleted} history records deleted.")
        return True
    except Exception as e:
        print(f"Error deleting history: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()
