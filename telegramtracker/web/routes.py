import threading
import queue
import os
from flask import render_template, request, redirect, url_for, Response, jsonify, session, flash, make_response, send_from_directory

from telegramtracker.core import database
from telegramtracker.services.telegram_client import run_fetch_in_background, API_ID, API_HASH, build_message_link
from telegramtracker.utils.translations import get_text, LANGUAGES

# Task Management
class TaskManager:
    def __init__(self):
        self.progress_queue = queue.Queue()
        self.results = None
        self.error = None
        self.entity = None  # Telegram entity object
        self.is_running = False
        self.original_identifier = None # Raw input from user for history
        self.original_period = None     # Numeric period for history
        self.scanned_count = 0          # Total messages scanned in the task
        self.download_folder_path = None # Path to folder where media is saved

    def start_new_task(self, identifier_to_process, raw_identifier_for_history, period_for_history, reaction_filter_enabled, download_limit_count):
        """Initializes state for a new background task and starts it."""
        if self.is_running:
            print("Warning: Attempted to start a new task while another is already running.")
            return False

        # Reset all task-specific fields
        self.progress_queue = queue.Queue()
        self.results = None
        self.error = None
        self.entity = None
        self.is_running = True
        self.original_identifier = raw_identifier_for_history
        self.original_period = period_for_history
        self.scanned_count = 0
        self.download_folder_path = None

        # The run_fetch_in_background function will need to be adapted
        # to accept this TaskManager instance and update its attributes.
        # For now, we pass 'self' (the task_manager instance) instead of task_data dict.
        thread = threading.Thread(
            target=run_fetch_in_background,
            args=(identifier_to_process, self, period_for_history, reaction_filter_enabled, download_limit_count)
            # Original args: (processed_identifier, task_data['progress_queue'], task_data, period, reaction_filter, download_limit)
        )
        thread.daemon = True
        thread.start()
        return True

    def set_task_error(self, error_message):
        """Sets error information for the current task and marks it as not running."""
        self.error = error_message
        self.is_running = False
        # Ensure the queue is signaled if the background task errored out early
        # Use a dictionary format consistent with other queue messages
        self.progress_queue.put({'type': 'error', 'message': error_message})


    def clear_task_data_after_processing(self):
        """Resets fields that should not persist after results are viewed/saved or an error is handled."""
        self.results = None
        self.error = None
        self.entity = None
        self.original_identifier = None
        self.original_period = None
        self.scanned_count = 0
        self.download_folder_path = None
        # self.is_running should already be False at this point.

# Global instance of the TaskManager
task_manager = TaskManager()

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
        # No longer need 'global task_data'
        
        if task_manager.is_running: # Use task_manager instance
            # If a task is already running, redirect directly to loading page
            return redirect(url_for('loading'))

        chat_input = request.form.get('chat_id')
        period_choice = request.form.get('period')
        reaction_filter = request.form.get('reaction_filter') == 'true' # Checkbox value is 'true' if checked
        download_limit_str = request.form.get('download_limit')

        if not chat_input:
            # Error case: chat_id required
            flash(get_text('chat_id_required_error', session.get('lang', 'tr')), 'error') # Need to add this translation
            return redirect(url_for('index'))

        # Convert download_limit to integer, handle empty string
        download_limit = None
        if download_limit_str:
            try:
                limit_value = int(download_limit_str)
                if limit_value > 0:
                    download_limit = limit_value
                else:
                    flash(get_text('download_limit_validation_error', session.get('lang', 'tr')), 'error') # Use existing translation
                    return redirect(url_for('index'))
            except ValueError:
                flash(get_text('download_limit_validation_error', session.get('lang', 'tr')), 'error') # Use existing translation
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
        mapping = {'7': 7, '30': 30, '90': 90, '180': 180, 'all': None, '1': 1}
        period = mapping.get(period_choice)

        # Process period for history saving (it's the same as 'period' used for fetching)

        # Attempt to start the new task using the TaskManager instance
        # The args passed to start_new_task now include all necessary info.
        # The run_fetch_in_background function (called within start_new_task)
        # will need to be updated separately to accept the task_manager instance.
        if not task_manager.start_new_task(processed_identifier, chat_input, period, reaction_filter, download_limit):
            # This case (task already running) is handled by the check at the beginning.
            # If start_new_task had other failure modes, they could be handled here.
            flash(get_text('task_already_running_error', session.get('lang', 'tr')), 'error') # Example error
            return redirect(url_for('index'))

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
            # No longer need 'global task_data'
            q = task_manager.progress_queue # Use queue from task_manager
            last_scanned_count_for_stream = 0 # Keep track of the last count sent

            # Loop while the task is running OR there are still items in the queue
            while task_manager.is_running or not q.empty():
                try:
                    update = q.get(timeout=1)  # Wait for an update

                    if update['type'] == 'progress':
                        last_scanned_count_for_stream = update['scanned']
                        yield f"data: {{\"type\": \"progress\", \"scanned\": {last_scanned_count_for_stream}}}\n\n"
                    elif update['type'] == 'media_phase':
                        yield f"data: {{\"type\": \"media_phase\", \"total_media\": {update['total_media']}}}\n\n"
                    elif update['type'] == 'media_progress':
                        yield f"data: {{\"type\": \"media_progress\", \"processed_count\": {update['processed_count']}, \"total_media\": {update['total_media']}}}\n\n"
                    elif update['type'] == 'error':
                        # Error message put in queue by background task or set_task_error
                        yield f"data: {{\"type\": \"error\", \"message\": \"{update['message']}\"}}\n\n"
                        # No need to break here, let the loop condition (is_running) handle termination
                    elif update['type'] == 'complete':
                        # Task completion message put in queue by background task
                        # Use the scanned count from the message if available, otherwise use the last known
                        final_scanned_count = update.get('scanned', last_scanned_count_for_stream)
                        yield f"data: {{\"type\": \"complete\", \"scanned\": {final_scanned_count}}}\n\n"
                        # No need to break here, let the loop condition handle termination

                    q.task_done() # Mark task as done in the queue

                except queue.Empty:
                    # No update received within the timeout.
                    # Send a keepalive comment to prevent the connection from closing.
                    yield ": keepalive\n\n"
                except Exception as e:
                    # Handle unexpected errors during streaming
                    print(f"Error in SSE stream processing queue item: {e}")
                    # Send a generic error to the client
                    yield f"data: {{\"type\": \"error\", \"message\": \"An internal error occurred during streaming.\"}}\n\n"
                    # Consider breaking or letting the loop condition handle it based on task_manager.is_running
                    # If the error is critical, ensure task_manager.is_running is set to False elsewhere.

            # After the loop finishes (task is no longer running AND queue is empty)
            # Perform final checks if needed, although most states should be handled within the loop.
            # For example, if an error occurred and was set directly on task_manager without going through the queue:
            if task_manager.error and update.get('type') != 'error': # Avoid sending duplicate error
                 yield f"data: {{\"type\": \"error\", \"message\": \"{task_manager.error}\"}}\n\n"

            print("SSE stream closing.")

        return Response(generate(), mimetype='text/event-stream')

    @app.route('/results')
    def results():
        """Shows paginated results."""
        # No longer need 'global task_data'
        lang = session.get('lang', 'tr')
        
        if task_manager.error:
            error_message = task_manager.error
            # Important: Clear task data AFTER retrieving the error message
            # and before rendering, so the error isn't shown again on refresh.
            task_manager.clear_task_data_after_processing()
            return render_template(
                'results.html',
                error=error_message, # Pass the retrieved error message
                lang=lang,
                t=get_text,
                languages=LANGUAGES
            )

        if task_manager.results is None:
            if task_manager.is_running:
                return redirect(url_for('loading'))
            else:
                # Not running and no results/error, implies an issue or direct access without task
                # Consider flashing a message or just redirecting
                # Clearing data here might be premature if it's a direct access attempt
                # but if it's an unexpected state, clearing might be safer.
                # For now, let's assume it's an invalid state and clear.
                task_manager.clear_task_data_after_processing()
                return redirect(url_for('index'))

        # Paginate results
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Items per page
        max_pages = 10 # Max number of pages to show in pagination

        all_task_results = task_manager.results # Use results from task_manager
        total_items = len(all_task_results)
        
        # Calculate total pages, respecting max_pages limit for display
        actual_total_pages = (total_items + per_page - 1) // per_page
        display_total_pages = min(max_pages, actual_total_pages)


        # Ensure current page is within valid range
        if page < 1:
            page = 1
        elif page > display_total_pages and display_total_pages > 0 : # if display_total_pages is 0, page 1 is fine
             return redirect(url_for('results', page=display_total_pages))
        elif page > 1 and total_items == 0: # No items, but requested page > 1
             return redirect(url_for('results', page=1))


        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        
        # Slice results for the current page
        # Ensure results are dicts if they need modification (e.g. adding links directly)
        # If results are already in the desired format (e.g. from database.py), direct slicing is fine.
        # The original code converted to dicts: paginated_results = [dict(row) for row in all_task_results[start_index:end_index]]
        # Assuming all_task_results are already list of dicts or similar.
        paginated_results = all_task_results[start_index:end_index]


        # Save to history if this is the first view of results (page 1)
        # and the task has original identifier (meaning it was a new search)
        history_id = None
        if page == 1 and task_manager.original_identifier and not request.args.get('no_save'):
            try:
                history_id = database.save_search_history(
                    task_manager.original_identifier,
                    task_manager.entity, # Entity object from task_manager
                    task_manager.original_period,
                    len(all_task_results), # Total results from this task
                    task_manager.scanned_count, # Scanned count from task_manager
                    task_manager.download_folder_path # download_folder_path from task_manager
                )

                if history_id:
                    # The build_link function now uses the entity from task_manager
                    def build_link_for_history(msg_id):
                        return build_message_link(task_manager.entity, msg_id)
                    
                    database.save_search_results(history_id, all_task_results, build_link_for_history)
            except Exception as e:
                print(f"Error saving to history: {e}")
                # Optionally flash a message to the user about history saving failure
                flash(get_text('history_save_error', lang), 'warning')


        # Data for the current task has been processed (either displayed or saved to history).
        # Clear it now, but only if it was a new search that just completed.
        # If we are just browsing pages of an already completed task (e.g. via direct URL with page > 1),
        # we should not clear it, as it might be needed if the user navigates back to page 1.
        # However, the current logic re-fetches task_data for each page, so this might be complex.
        # A safer approach: clear if page == 1 and history_id was processed (or attempted).
        if page == 1 and task_manager.original_identifier:
            task_manager.clear_task_data_after_processing()


        # Function to build links for the current view (might be different from history saving if entity changes)
        current_task_entity_for_links = task_manager.entity # Or re-fetch if necessary for paged views
        
        return render_template(
            'results.html',
            results=paginated_results,
            lang=lang,
            t=get_text,
            languages=LANGUAGES,
            # Pass entity for link building; ensure it's available if task_manager was cleared
            build_link=lambda msg_id: build_message_link(current_task_entity_for_links, msg_id),
            page=page,
            total_pages=display_total_pages,
            total_messages=total_items, # Renamed from total_items for clarity in template
            history_id=history_id # Pass history_id if created
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
            
        # get_history_results now returns results with media_paths
        processed_results = database.get_history_results(history_id)

        # Paginate results
        page = request.args.get('page', 1, type=int)
        per_page = 24
        
        total_items = len(processed_results)
        total_pages = (total_items + per_page - 1) // per_page
        
        start_index = (page - 1) * per_page
        end_index = min(start_index + per_page, total_items)
        
        paginated_results = processed_results[start_index:end_index] if start_index < total_items else []
        
        return render_template(
            'history_results.html',
            history=history_entry,
            results=paginated_results, # Pass results with media_paths
            lang=lang,
            t=get_text,
            languages=LANGUAGES,
            page=page,
            total_pages=total_pages,
            total_items=total_items
        )

    # Route to serve downloaded files
    @app.route('/downloads/<path:subpath>')
    def serve_downloaded_file(subpath):
        """Serves files from the downloads directory."""
        # Construct the absolute path to the downloads directory
        # Assumes 'downloads' is in the CWD where Flask is run
        download_dir = os.path.abspath('downloads')
        # Prevent accessing files outside the download_dir using safe_join (implicitly handled by send_from_directory)
        print(f"Attempting to serve: {subpath} from {download_dir}")
        try:
            # send_from_directory handles security (path traversal)
            return send_from_directory(download_dir, subpath)
        except Exception as e:
            print(f"Error serving file {subpath}: {e}")
            return "File not found", 404

    @app.route('/delete_history/<int:history_id>', methods=['POST'])
    def delete_history(history_id):
        """Deletes a history entry and its results."""
        success = database.delete_history_entry(history_id)
        
        if success:
            flash('History entry deleted successfully.', 'success')
        else:
            flash('Failed to delete history entry.', 'error')
            
        return redirect(url_for('history'))

    @app.route('/delete_selected_history', methods=['POST'])
    def delete_selected_history():
        """Deletes selected history entries."""
        selected_ids = request.json.get('history_ids', [])
        if not selected_ids:
            return jsonify({'success': False, 'message': 'No history IDs provided.'}), 400

        try:
            deleted_count = database.delete_history_entries_by_ids(selected_ids)
            return jsonify({'success': True, 'deleted_count': deleted_count}), 200
        except Exception as e:
            print(f"Error deleting selected history entries: {e}")
            return jsonify({'success': False, 'message': 'An error occurred during deletion.'}), 500
