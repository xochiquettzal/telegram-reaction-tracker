function changeLanguage(lang) {
    const currentUrl = new URL(window.location.href);
    currentUrl.searchParams.set('lang', lang);
    window.location.href = currentUrl.toString();
}

document.addEventListener('DOMContentLoaded', function() {
    const chatSelect = document.getElementById('chat_id');
    const downloadLimitInput = document.getElementById('download_limit');
    const reactionFilterCheckbox = document.getElementById('reaction_filter');
    const searchForm = document.querySelector('.input-form');

    // Function to fetch chats and populate the dropdown
    async function fetchAndPopulateChats() {
        const loadingText = chatSelect.dataset.loadingText;
        const selectChatText = chatSelect.dataset.selectChatText;

        chatSelect.innerHTML = `<option value="">${loadingText}</option>`;
        chatSelect.disabled = true; // Disable while loading

        try {
            const response = await fetch('/get_chats');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const chats = await response.json();

            chatSelect.innerHTML = ''; // Clear loading option
            chatSelect.add(new Option(selectChatText, '')); // Add default "Select a chat" option

            // Sort chats alphabetically by title
            chats.sort((a, b) => a.title.localeCompare(b.title));

            chats.forEach(chat => {
                // Prioritize username if available, otherwise use ID
                const value = chat.username ? chat.username : chat.id;
                const option = new Option(chat.title, value);
                chatSelect.add(option);
            });
        } catch (error) {
            console.error('Error fetching chats:', error);
            chatSelect.innerHTML = `<option value="">Error loading chats</option>`; // Display error message
            // Optionally, re-enable the input or provide a retry mechanism
        } finally {
            chatSelect.disabled = false; // Re-enable after loading (or error)
        }
    }

    // Call the function to fetch and populate chats
    fetchAndPopulateChats();

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
