document.addEventListener('DOMContentLoaded', function() {
    // --- SSE logic for the loading page ---
    // Check if we are on the loading page by looking for a specific element
    const progressTextElement = document.getElementById('loading-status'); 

    // Only run SSE logic if the loading status element exists
    if (progressTextElement) {
        console.log("Loading page detected, initializing SSE."); // Add log for confirmation
        const scannedCountElement = document.getElementById('status-count'); 
        // const errorMessageElement = document.getElementById('error-message'); // Element does not exist
        // const cancelButtonElement = document.getElementById('cancel-button'); // Element does not exist
        const scanProgressStatusElement = document.getElementById('scan-progress-status'); 
        const mediaProgressStatusElement = document.getElementById('media-progress-status'); 
        const mediaCountElement = document.getElementById('media-count'); 
        const mediaTotalElement = document.getElementById('media-total'); 

        // We already know progressTextElement exists due to the outer 'if'
        progressTextElement.textContent = 'Connecting to server...';

        // Check for other elements existence inside this block
        if (!scannedCountElement || !scanProgressStatusElement || !mediaProgressStatusElement || !mediaCountElement || !mediaTotalElement) {
            console.warn("One or more non-critical loading page elements not found. SSE script might have reduced functionality.");
        }

        const eventSource = new EventSource('/stream-progress');

        eventSource.onopen = function() {
        if (progressTextElement) {
            progressTextElement.textContent = 'Scanning messages...';
        }
    };

    eventSource.onmessage = function(event) {
        // Handle keepalive messages (ignore them)
        if (event.data.startsWith(':')) {
            return;
        }

        try {
            const data = JSON.parse(event.data);

            if (data.type === 'progress') {
                if (scannedCountElement) scannedCountElement.textContent = data.scanned;
                if (progressTextElement) progressTextElement.textContent = 'Scanning messages...'; // Keep updating text
                // Hide error message if previously shown - Elements don't exist
                // if (errorMessageElement) errorMessageElement.style.display = 'none';
                // if (cancelButtonElement) cancelButtonElement.style.display = 'none';
                // Ensure scan progress is visible and media progress is hidden
                if (scanProgressStatusElement) {
                    scanProgressStatusElement.style.display = 'block';
                }
                if (mediaProgressStatusElement) {
                    mediaProgressStatusElement.style.display = 'none';
                }
            } else if (data.type === 'complete') {
                if (progressTextElement) progressTextElement.textContent = `Scan finished! Found messages with reactions. Redirecting...`;
                if (scannedCountElement) scannedCountElement.textContent = data.scanned; // Final update
                eventSource.close(); // Close the connection
                // Redirect to results page after a short delay
                setTimeout(() => {
                    window.location.href = '/results';
                }, 1500); // Wait 1.5 seconds before redirect
            } else if (data.type === 'media_phase') {
                if (progressTextElement) progressTextElement.textContent = `${data.total_media} media items found. Downloading...`; // Modified text
                // Hide scan progress and show media progress
                if (scanProgressStatusElement) {
                    scanProgressStatusElement.style.display = 'none';
                }
                if (mediaProgressStatusElement) {
                    mediaProgressStatusElement.style.display = 'block';
                }
                if (mediaTotalElement) {
                    mediaTotalElement.textContent = data.total_media;
                }
            } else if (data.type === 'media_progress') {
                // Update the media progress count
                if (mediaCountElement) {
                    mediaCountElement.textContent = data.processed_count;
                }
            } else if (data.type === 'error') {
                console.error("Error message received:", data.message); // Keep error log
                if (progressTextElement) progressTextElement.textContent = 'An error occurred.';
                // Cannot display detailed error message as element doesn't exist
                // if (errorMessageElement) {
                //     errorMessageElement.textContent = `Error: ${data.message}`;
                //     errorMessageElement.style.display = 'block';
                // }
                // Cannot show cancel button as element doesn't exist
                // if (cancelButtonElement) {
                //     cancelButtonElement.style.display = 'inline-block'; 
                // }
                eventSource.close(); // Close connection on error
            }
        } catch (e) {
            console.error("Failed to parse SSE message:", event.data, e);
            if (progressTextElement) progressTextElement.textContent = 'Error processing update.';
            // Cannot display detailed error message as element doesn't exist
            // if (errorMessageElement) {
            //     errorMessageElement.textContent = 'Error processing update from server.';
            //     errorMessageElement.style.display = 'block';
            // }
            // Cannot show cancel button as element doesn't exist
            // if (cancelButtonElement) {
            //     cancelButtonElement.style.display = 'inline-block';
            // }
            eventSource.close();
        }
    };

    eventSource.onerror = function(err) {
        console.error("EventSource failed:", err); // Keep error log
        if (progressTextElement) progressTextElement.textContent = 'Connection error. Unable to get progress.';
         // Cannot display detailed error message as element doesn't exist
        // if (errorMessageElement) { // Element doesn't exist
        //     errorMessageElement.textContent = 'Failed to connect to the progress stream. Please try again.';
        //     errorMessageElement.style.display = 'block';
        // }
         // Cannot show cancel button as element doesn't exist
        // if (cancelButtonElement) { // Element doesn't exist
        //     cancelButtonElement.style.display = 'inline-block';
        // }
        eventSource.close(); // Close connection on error
        };

    } else {
        // Log that SSE is not initialized because it's not the loading page
        // console.log("Not on loading page, SSE not initialized."); // Optional log
    }
    // --- End of SSE logic ---

}); // End of DOMContentLoaded listener
