function changeLanguage(lang) {
    const currentUrl = new URL(window.location.href);
    currentUrl.searchParams.set('lang', lang);
    window.location.href = currentUrl.toString();
}

document.addEventListener('DOMContentLoaded', function() {
    const downloadLimitInput = document.getElementById('download_limit');
    const reactionFilterCheckbox = document.getElementById('reaction_filter');
    const searchForm = document.querySelector('.input-form');

    // Function to update the disabled state of the download limit input
    function updateDownloadLimitState() {
        if (reactionFilterCheckbox && downloadLimitInput) {
            downloadLimitInput.disabled = !reactionFilterCheckbox.checked;
            // Clear the value if disabled
            if (downloadLimitInput.disabled) {
                downloadLimitInput.value = '';
            }
        }
    }

    // Ensure default state is off/empty and update input state
    if (reactionFilterCheckbox) {
        reactionFilterCheckbox.checked = false;
    }
    if (downloadLimitInput) {
        downloadLimitInput.value = ''; // Set to empty string for placeholder to show
    }
    updateDownloadLimitState(); // Set initial state

    // Add event listener to the checkbox
    if (reactionFilterCheckbox) {
        reactionFilterCheckbox.addEventListener('change', updateDownloadLimitState);
    }


    // Client-side validation for download limit
    if (searchForm && downloadLimitInput) {
        searchForm.addEventListener('submit', function(event) {
            // Only validate if the input is not disabled (i.e., checkbox is checked)
            if (!downloadLimitInput.disabled) {
                const limitValue = parseInt(downloadLimitInput.value, 10);

                if (downloadLimitInput.value !== '' && (isNaN(limitValue) || limitValue <= 0)) {
                    alert('{{ t("download_limit_validation_error", lang) }}');
                    event.preventDefault(); // Prevent form submission
                }
                // Add validation for excessively high values if needed, but for now min="1" and type="number" handle basic cases.
            }
        });
    }
});
