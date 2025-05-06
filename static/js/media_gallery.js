// static/js/media_gallery.js

// Function to apply aspect ratio to a container
function applyAspectRatio(container, width, height) {
    if (container && width > 0 && height > 0) {
        // Ensure the container itself has a defined width or is a block element
        // so aspect-ratio can work effectively.
        container.style.aspectRatio = `${width} / ${height}`;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.media-container').forEach(container => {
        try {
            const mediaPathsData = container.dataset.mediaPaths;
            if (!mediaPathsData) {
                // console.warn("Media container found without media-paths data.", container);
                return;
            }
            const mediaPaths = JSON.parse(mediaPathsData);

            if (!mediaPaths || mediaPaths.length === 0) {
                // console.warn("No media paths found for container.", container);
                return; // No paths, nothing to display or navigate
            }

            const mediaItemWrapper = container.querySelector('.media-item'); // Expects a div.media-item
            const leftArrow = container.querySelector('.left-arrow');
            const rightArrow = container.querySelector('.right-arrow');
            let currentIndex = 0; // The first item is already rendered by the template

            // Hide arrows if only one item, even if template rendered them
            if (mediaPaths.length <= 1) {
                if(leftArrow) leftArrow.style.display = 'none';
                if(rightArrow) rightArrow.style.display = 'none';
                // If first item is an image, try to apply aspect ratio
                const firstImg = mediaItemWrapper ? mediaItemWrapper.querySelector('img') : null;
                if (firstImg) {
                    if (firstImg.complete) {
                         applyAspectRatio(mediaItemWrapper, firstImg.naturalWidth, firstImg.naturalHeight);
                    } else {
                        firstImg.addEventListener('load', () => {
                            applyAspectRatio(mediaItemWrapper, firstImg.naturalWidth, firstImg.naturalHeight);
                        });
                    }
                }
                // If first item is a video, try to apply aspect ratio
                const firstVid = mediaItemWrapper ? mediaItemWrapper.querySelector('video') : null;
                if (firstVid) {
                     if (firstVid.readyState >= 1) { // HAVE_METADATA
                        applyAspectRatio(mediaItemWrapper, firstVid.videoWidth, firstVid.videoHeight);
                    } else {
                        firstVid.addEventListener('loadedmetadata', () => {
                            applyAspectRatio(mediaItemWrapper, firstVid.videoWidth, firstVid.videoHeight);
                        });
                    }
                }
                return;
            }


            // Function to update the displayed media
            function updateMediaDisplay(index) {
                if (!mediaItemWrapper) {
                    console.error("Media item wrapper not found in container.", container);
                    return;
                }
                const mediaPath = mediaPaths[index];
                const fileExtension = mediaPath.split('.').pop().toLowerCase();
                // The URL is constructed in the template using url_for,
                // here we just need the subpath for the serve_downloaded_file route
                const mediaUrl = `/downloads/${mediaPath}`; // This needs to match the Flask route

                // Clear previous media
                mediaItemWrapper.innerHTML = '';

                let newMediaElement;
                if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'].includes(fileExtension)) {
                    newMediaElement = document.createElement('img');
                    newMediaElement.src = mediaUrl;
                    // Alt text should be dynamic, passed from template or use a generic one
                    newMediaElement.alt = container.dataset.altText || 'Downloaded media';
                    newMediaElement.addEventListener('load', () => {
                        applyAspectRatio(mediaItemWrapper, newMediaElement.naturalWidth, newMediaElement.naturalHeight);
                    });
                } else if (['mp4', 'mov', 'avi', 'mkv', 'webm'].includes(fileExtension)) {
                    newMediaElement = document.createElement('video');
                    newMediaElement.controls = true;
                    const source = document.createElement('source');
                    source.src = mediaUrl;
                    source.type = `video/${fileExtension === 'mov' ? 'quicktime' : (fileExtension === 'mkv' ? 'x-matroska' : fileExtension)}`;
                    newMediaElement.appendChild(source);
                    newMediaElement.appendChild(document.createTextNode(container.dataset.videoNotSupportedText || 'Your browser does not support the video tag.'));
                    newMediaElement.addEventListener('loadedmetadata', () => {
                         applyAspectRatio(mediaItemWrapper, newMediaElement.videoWidth, newMediaElement.videoHeight);
                    });
                } else {
                    newMediaElement = document.createElement('p');
                    newMediaElement.textContent = (container.dataset.unsupportedMediaText || 'Unsupported media type') + `: ${mediaPath.split('/').pop()}`;
                }

                if (newMediaElement) {
                    mediaItemWrapper.appendChild(newMediaElement);
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
             // Initial aspect ratio for the first item if it's an image/video
            const initialMediaElement = mediaItemWrapper.querySelector('img, video');
            if (initialMediaElement) {
                if (initialMediaElement.tagName === 'IMG') {
                    if (initialMediaElement.complete) {
                        applyAspectRatio(mediaItemWrapper, initialMediaElement.naturalWidth, initialMediaElement.naturalHeight);
                    } else {
                        initialMediaElement.addEventListener('load', () => {
                            applyAspectRatio(mediaItemWrapper, initialMediaElement.naturalWidth, initialMediaElement.naturalHeight);
                        });
                    }
                } else if (initialMediaElement.tagName === 'VIDEO') {
                    if (initialMediaElement.readyState >= 1) { // HAVE_METADATA
                        applyAspectRatio(mediaItemWrapper, initialMediaElement.videoWidth, initialMediaElement.videoHeight);
                    } else {
                        initialMediaElement.addEventListener('loadedmetadata', () => {
                            applyAspectRatio(mediaItemWrapper, initialMediaElement.videoWidth, initialMediaElement.videoHeight);
                        });
                    }
                }
            }


        } catch (e) {
            console.error("Error processing media container:", e, "Container data:", container.dataset.mediaPaths);
        }
    });
});
