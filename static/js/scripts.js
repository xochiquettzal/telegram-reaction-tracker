document.addEventListener('DOMContentLoaded', function() {
    // Only run this script if we are on the loading page (identified by specific elements)
    const scannedCountElement = document.getElementById('scanned-count');
    const progressTextElement = document.getElementById('progress-text');
    const errorMessageElement = document.getElementById('error-message');
    const cancelButtonElement = document.getElementById('cancel-button'); // Button to show on error
    const scanProgressStatusElement = document.getElementById('scan-progress-status'); // New element
    const mediaProgressStatusElement = document.getElementById('media-progress-status'); // New element
    const mediaCountElement = document.getElementById('media-count'); // New element
    const mediaTotalElement = document.getElementById('media-total'); // New element


    if (scannedCountElement && progressTextElement) {
        console.log("Loading page script started. Connecting to SSE endpoint...");
        progressTextElement.textContent = 'Connecting to server...';

        const eventSource = new EventSource('/stream-progress');

        eventSource.onopen = function() {
            console.log("SSE connection opened.");
            progressTextElement.textContent = 'Scanning messages...';
        };

        eventSource.onmessage = function(event) {
            // Handle keepalive messages (ignore them)
            if (event.data.startsWith(':')) {
                console.log("Keepalive received");
                return;
            }

            console.log("SSE message received:", event.data);
            try {
                const data = JSON.parse(event.data);

                if (data.type === 'progress') {
                    scannedCountElement.textContent = data.scanned;
                    progressTextElement.textContent = 'Scanning messages...'; // Keep updating text
                     // Hide error message if previously shown
                    if (errorMessageElement) errorMessageElement.style.display = 'none';
                    if (cancelButtonElement) cancelButtonElement.style.display = 'none';
                    // Ensure scan progress is visible and media progress is hidden
                    if (scanProgressStatusElement) {
                        scanProgressStatusElement.style.display = 'block';
                    }
                    if (mediaProgressStatusElement) {
                        mediaProgressStatusElement.style.display = 'none';
                    }
                } else if (data.type === 'complete') {
                    console.log("Scan complete message received.");
                    progressTextElement.textContent = `Scan finished! Found messages with reactions. Redirecting...`;
                    scannedCountElement.textContent = data.scanned; // Final update
                    eventSource.close(); // Close the connection
                    // Redirect to results page after a short delay
                    setTimeout(() => {
                        window.location.href = '/results';
                    }, 1500); // Wait 1.5 seconds before redirect
                } else if (data.type === 'media_phase') {
                    console.log("Media phase message received:", data);
                    progressTextElement.textContent = `${data.total_media} media items found. Downloading...`; // Modified text
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
                    console.log("Media progress message received:", data);
                    // Update the media progress count
                    if (mediaCountElement) {
                        mediaCountElement.textContent = data.processed_count;
                    }
                } else if (data.type === 'error') {
                    console.error("Error message received:", data.message);
                    progressTextElement.textContent = 'An error occurred.';
                    if (errorMessageElement) {
                        errorMessageElement.textContent = `Error: ${data.message}`;
                        errorMessageElement.style.display = 'block';
                    }
                     if (cancelButtonElement) {
                        cancelButtonElement.style.display = 'inline-block'; // Show cancel/back button
                    }
                    eventSource.close(); // Close connection on error
                }
            } catch (e) {
                console.error("Failed to parse SSE message:", event.data, e);
                 progressTextElement.textContent = 'Error processing update.';
                 if (errorMessageElement) {
                     errorMessageElement.textContent = 'Error processing update from server.';
                     errorMessageElement.style.display = 'block';
                 }
                 if (cancelButtonElement) {
                    cancelButtonElement.style.display = 'inline-block';
                 }
                 eventSource.close();
            }
        };

        eventSource.onerror = function(err) {
            console.error("EventSource failed:", err);
            progressTextElement.textContent = 'Connection error. Unable to get progress.';
            if (errorMessageElement) {
                errorMessageElement.textContent = 'Failed to connect to the progress stream. Please try again.';
                errorMessageElement.style.display = 'block';
            }
             if (cancelButtonElement) {
                cancelButtonElement.style.display = 'inline-block';
             }
            eventSource.close(); // Close connection on error
        };

    } else {
        console.log("Not on the loading page, script inactive.");
    }
});
