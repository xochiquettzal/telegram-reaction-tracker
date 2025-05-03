import threading
import queue
from flask import render_template, request, redirect, url_for, Response, jsonify, session, flash, make_response

from telegramtracker.core import database
from telegramtracker.services.telegram_client import run_fetch_in_background, API_ID, API_HASH, build_message_link
from telegramtracker.utils.translations import get_text, LANGUAGES

# Global variable to store application state
# This is sufficient for a single-user application, should be reconsidered for a more scalable solution
task_data = {
    'progress_queue': queue.Queue(),
    'results': None,
    'error': None,
    'entity': None,
    'is_running': False,
    'original_identifier': None,
    'original_period': None
}

def register_routes(app):
    # Store language selection in session
    @app.before_request
    def before_request():
        # If user selects a language, store it in session
        lang = request.args.get('lang', None)
        if lang and lang in LANGUAGES:
            session['lang'] = lang
        
        # If no language in session, default to English
        if 'lang' not in session:
            session['lang'] = 'en'

    # Language selection route
    @app.route('/set_language/<lang>')
    def set_language(lang):
        """Sets the language choice for the user."""
        if lang in LANGUAGES:
            session['lang'] = lang
        
        # Redirect the user back to where they came from
        next_page = request.args.get('next') or request.referrer or url_for('index')
        return redirect(next_page)

    @app.route('/')
    def index():
        """Shows the main page."""
        lang = session.get('lang', 'tr')
        return render_template(
            'index.html',
            lang=lang,
            t=get_text,
            languages=LANGUAGES
        )

    @app.route('/fetch', methods=['POST'])
    def fetch():
        """Starts a process to fetch Telegram data."""
        global task_data
        
        if task_data['is_running']:
            # If a task is already running, redirect directly to loading page
            return redirect(url_for('loading'))

        chat_input = request.form.get('chat_id')
        period_choice = request.form.get('period')

        if not chat_input:
            # Error case: chat_id required
            return redirect(url_for('index'))

        # Process input for username or ID format
        try:
            # If it looks like a numeric ID, convert to int
            processed_identifier = int(chat_input)
            print(f"'{chat_input}' processed as ID: {processed_identifier}")
        except ValueError:
            # If conversion fails, treat as username
            processed_identifier = chat_input.strip()
            print(f"'{chat_input}' processed as username: {processed_identifier}")

        # Process time period selection
        mapping = {'7': 7, '30': 30, '90': 90, '180': 180, 'all': None}
        period = mapping.get(period_choice)

        # Store original inputs for database saving
        task_data['original_identifier'] = chat_input  # Store raw input
        task_data['original_period'] = period  # Store numeric period

        # Start fetch process in background
        thread = threading.Thread(
            target=run_fetch_in_background, 
            args=(processed_identifier, task_data['progress_queue'], task_data, period)
        )
        thread.daemon = True  # Allow app exit even if thread is running
        thread.start()

        return redirect(url_for('loading'))

    @app.route('/loading')
    def loading():
        """Shows the loading page."""
        lang = session.get('lang', 'tr')
        return render_template(
            'loading.html',
            lang=lang,
            t=get_text,
            languages=LANGUAGES
        )

    @app.route('/stream-progress')
    def stream_progress():
        """Server-Sent Events endpoint for progress updates."""
        def generate():
            global task_data
            q = task_data['progress_queue']
            last_scanned = 0
            
            while task_data['is_running'] or not q.empty():
                try:
                    update = q.get(timeout=1)  # Wait at most 1 second
                    
                    if update['type'] == 'progress':
                        last_scanned = update['scanned']
                        yield f"data: {{\"type\": \"progress\", \"scanned\": {last_scanned}}}\n\n"
                    elif update['type'] == 'media_phase':
                        # Forward media phase message to frontend
                        yield f"data: {{\"type\": \"media_phase\", \"total_media\": {update['total_media']}}}\n\n"
                    elif update['type'] == 'media_progress':
                        # Forward media progress message to frontend
                        yield f"data: {{\"type\": \"media_progress\", \"processed_count\": {update['processed_count']}, \"total_media\": {update['total_media']}}}\n\n"
                    elif update['type'] == 'error':
                        yield f"data: {{\"type\": \"error\", \"message\": \"{update['message']}\"}}\n\n"
                        break
                    elif update['type'] == 'complete':
                        yield f"data: {{\"type\": \"complete\", \"scanned\": {last_scanned}}}\n\n"
                        
                    q.task_done()
                except queue.Empty:
                    # No update on timeout, keep alive to keep connection open
                    yield f": keepalive\n\n"
                except Exception as e:
                    # Log error during streaming
                    print(f"Error in SSE stream: {e}")
                    yield f"data: {{\"type\": \"error\", \"message\": \"SSE stream error: {e}\"}}\n\n"
                    break

            # Final check after loop exit (task completed)
            if task_data['error']:
                yield f"data: {{\"type\": \"error\", \"message\": \"{task_data['error']}\"}}\n\n"
            elif task_data['results'] is not None:
                # Notify completion
                if 'update' not in locals() or update.get('type') != 'complete':
                    yield f"data: {{\"type\": \"complete\", \"scanned\": {last_scanned}}}\n\n"
            
            print("SSE stream closing.")

        return Response(generate(), mimetype='text/event-stream')

    @app.route('/results')
    def results():
        """Shows paginated results."""
        global task_data
        lang = session.get('lang', 'tr')
        
        if task_data['error']:
            # Show error message
            return render_template(
                'results.html',
                error=task_data['error'],
                lang=lang,
                t=get_text,
                languages=LANGUAGES
            )

        if task_data['results'] is None:
            # Task is still running or failed silently
            if task_data['is_running']:
                return redirect(url_for('loading'))
            else:
                # Not running and no result/error, something went wrong
                return redirect(url_for('index'))

        # Paginate results
        page = request.args.get('page', 1, type=int)
        per_page = 10
        max_pages = 10  # Limit to 10 pages as requested

        all_results = task_data['results']
        total_items = len(all_results)
        start_index = (page - 1) * per_page
        end_index = start_index + per_page

        # Ensure we don't exceed total items or 10 page limit
        if start_index >= total_items or page > max_pages:
            # Handle invalid page number - show page 1 or error?
            # For simplicity, let's redirect to page 1
            if page != 1:
                return redirect(url_for('results', page=1))
            else:  # Page 1 is requested but no results (shouldn't happen)
                paginated_results = []
        else:
            paginated_results = all_results[start_index:end_index]

        # Add links to results
        entity_info = task_data['entity']
        
        # Calculate pagination info
        total_pages = min(max_pages, (total_items + per_page - 1) // per_page)
        
        # Save to history if this is the first view of results (page 1)
        history_id = None
        if page == 1 and task_data.get('original_identifier') and not request.args.get('no_save'):
            # Save search metadata
            try:
                history_id = database.save_search_history(
                    task_data['original_identifier'],
                    task_data['entity'],
                    task_data['original_period'],
                    len(all_results),
                    task_data.get('scanned_count', 0)
                )
                
                # Save individual results
                if history_id:
                    # Create a function to build links for each message
                    def build_link(msg_id):
                        return build_message_link(entity_info, msg_id)
                        
                    database.save_search_results(history_id, all_results, build_link)
            except Exception as e:
                print(f"Error saving to history: {e}")
                # Continue showing results even if saving fails

        # Reset task_data after processing results to prevent re-saving
        task_data['results'] = None
        task_data['entity'] = None
        task_data['original_identifier'] = None
        task_data['original_period'] = None
        
        return render_template(
            'results.html',
            results=paginated_results,
            lang=lang,
            t=get_text,
            languages=LANGUAGES,
            build_link=lambda msg_id: build_message_link(entity_info, msg_id),
            page=page,
            total_pages=total_pages,
            total_items=total_items,
            history_id=history_id
        )

    @app.route('/history')
    def history():
        """Shows search history."""
        lang = session.get('lang', 'tr')
        history_entries = database.get_search_history()
        return render_template(
            'history.html',
            history=history_entries,
            lang=lang,
            t=get_text,
            languages=LANGUAGES
        )
        
    @app.route('/history/<int:history_id>')
    def view_history_results(history_id):
        """Shows results from a specific history entry."""
        lang = session.get('lang', 'tr')
        
        # Get history entry and results
        history_entry = database.get_history_entry(history_id)
        if not history_entry:
            # History entry not found
            return redirect(url_for('history'))
            
        results = database.get_history_results(history_id)
        
        # Paginate results
        page = request.args.get('page', 1, type=int)
        per_page = 24
        
        total_items = len(results)
        total_pages = (total_items + per_page - 1) // per_page
        
        start_index = (page - 1) * per_page
        end_index = min(start_index + per_page, total_items)
        
        paginated_results = results[start_index:end_index] if start_index < total_items else []
        
        return render_template(
            'history_results.html',
            history=history_entry,
            results=paginated_results,
            lang=lang,
            t=get_text,
            languages=LANGUAGES,
            page=page,
            total_pages=total_pages,
            total_items=total_items
        )
    
    @app.route('/delete_history/<int:history_id>', methods=['POST'])
    def delete_history(history_id):
        """Deletes a history entry and its results."""
        success = database.delete_history_entry(history_id)
        
        if success:
            flash('History entry deleted successfully.', 'success')
        else:
            flash('Failed to delete history entry.', 'error')
            
        return redirect(url_for('history'))
