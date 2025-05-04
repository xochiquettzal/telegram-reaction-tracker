document.addEventListener('DOMContentLoaded', function() {
    // SSE logic for the loading page
    // Use correct IDs from loading.html
    const scannedCountElement = document.getElementById('status-count'); 
    const progressTextElement = document.getElementById('loading-status'); 
    // const errorMessageElement = document.getElementById('error-message'); // Element does not exist
    // const cancelButtonElement = document.getElementById('cancel-button'); // Element does not exist
    const scanProgressStatusElement = document.getElementById('scan-progress-status'); 
    const mediaProgressStatusElement = document.getElementById('media-progress-status'); 
    const mediaCountElement = document.getElementById('media-count'); 
    const mediaTotalElement = document.getElementById('media-total'); 

    // Ensure the essential elements exist before proceeding
    if (!scannedCountElement || !progressTextElement || !scanProgressStatusElement || !mediaProgressStatusElement || !mediaCountElement || !mediaTotalElement) {
        console.error("One or more essential loading page elements not found. SSE script might not function correctly.");
        // Decide if we should return or try to continue partially
        // For now, let's log the error and continue, as some parts might still work.
    }

    // Only proceed if the core elements for displaying status are found
    if (progressTextElement) {
        progressTextElement.textContent = 'Connecting to server...';
    } else {
         console.error("Critical element 'loading-status' not found. Cannot display status.");
         return; // Stop if we can't show basic status
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
        // if (errorMessageElement) {
        //     errorMessageElement.textContent = 'Failed to connect to the progress stream. Please try again.';
        //     errorMessageElement.style.display = 'block';
        // }
         // Cannot show cancel button as element doesn't exist
        // if (cancelButtonElement) {
        //     cancelButtonElement.style.display = 'inline-block';
        // }
        eventSource.close(); // Close connection on error
    };
});

// Media navigation logic for results and history pages
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.media-container').forEach(container => {
        try {
            const mediaPaths = JSON.parse(container.dataset.mediaPaths);
            if (!mediaPaths || mediaPaths.length <= 1) {
                // No paths or only one path, no navigation needed.
                // Ensure arrows are hidden if they somehow exist (template should handle this)
                const leftArrow = container.querySelector('.left-arrow');
                const rightArrow = container.querySelector('.right-arrow');
                if(leftArrow) leftArrow.style.display = 'none';
                if(rightArrow) rightArrow.style.display = 'none';
                return; 
            }

            const leftArrow = container.querySelector('.left-arrow');
            const rightArrow = container.querySelector('.right-arrow');
            let currentIndex = 0; // Assume template shows the first item (index 0) initially

            // Function to update the displayed media
            function updateMediaDisplay(index) {
                const currentMediaElement = container.querySelector('img, video');
                const mediaPath = mediaPaths[index];
                const fileExtension = mediaPath.split('.').pop().toLowerCase();
                const mediaUrl = `/downloads/${mediaPath}`; // Construct the URL

                // Create the new element first
                let newMediaElement;
                if (['jpg', 'jpeg', 'png', 'gif'].includes(fileExtension)) {
                    newMediaElement = document.createElement('img');
                    newMediaElement.src = mediaUrl;
                    newMediaElement.alt = 'Downloaded media'; // Consider adding translation key/logic if needed
                    newMediaElement.style.maxWidth = '100%';
                    newMediaElement.style.height = 'auto';
                    newMediaElement.style.borderRadius = '8px';
                } else if (['mp4', 'mov', 'avi', 'mkv'].includes(fileExtension)) {
                    newMediaElement = document.createElement('video');
                    newMediaElement.controls = true;
                    // Setting width via style is better for responsiveness
                    newMediaElement.style.width = '100%'; 
                    newMediaElement.style.maxWidth = '100%';
                    newMediaElement.style.borderRadius = '8px';
                    const source = document.createElement('source');
                    source.src = mediaUrl;
                    // Attempt basic type detection, might need improvement
                    source.type = `video/${fileExtension === 'mov' ? 'quicktime' : fileExtension}`; 
                    newMediaElement.appendChild(source);
                    const fallbackText = document.createTextNode('Your browser does not support the video tag.');
                    newMediaElement.appendChild(fallbackText);
                } else {
                    // Silently ignore unsupported types or log minimally if needed
                    return; 
                }

                // Remove the old element if it exists
                if (currentMediaElement) {
                    container.removeChild(currentMediaElement);
                } 

                // Insert the new media element before the left arrow (or as the first child if no arrows)
                if (leftArrow) {
                    container.insertBefore(newMediaElement, leftArrow);
                } else {
                    // Fallback: insert as first child if arrows aren't there (shouldn't happen if length > 1)
                    container.insertBefore(newMediaElement, container.firstChild);
                }
            }

            // Attach event listeners
            if (leftArrow) {
                leftArrow.addEventListener('click', () => {
                    currentIndex = (currentIndex - 1 + mediaPaths.length) % mediaPaths.length;
                    updateMediaDisplay(currentIndex);
                });
            } 

            if (rightArrow) {
                rightArrow.addEventListener('click', () => {
                    currentIndex = (currentIndex + 1) % mediaPaths.length;
                    updateMediaDisplay(currentIndex);
                });
            } 

        } catch (e) {
            console.error("Error processing media container:", e); // Keep error log for actual errors
        }
    });
});
