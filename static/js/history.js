// static/js/history.js

// Modal functions
function confirmDelete(historyId) {
    const modal = document.getElementById('deleteModal');
    const deleteForm = document.getElementById('deleteForm');

    // Set the action URL for the delete form
    if (deleteForm) {
        deleteForm.action = "/delete_history/" + historyId; // Make sure this route exists in Flask
    }

    // Show the modal
    if (modal) {
        modal.style.display = "flex";
    }
}

function closeModal() {
    const modal = document.getElementById('deleteModal');
    if (modal) {
        modal.style.display = "none";
    }
}

// Close modal when clicking outside of it
window.onclick = function(event) {
    const modal = document.getElementById('deleteModal');
    if (event.target === modal) {
        closeModal();
    }
};

// JavaScript for bulk delete
document.addEventListener('DOMContentLoaded', function() {
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const historyCheckboxes = document.querySelectorAll('.history-checkbox');
    const deleteSelectedBtn = document.getElementById('deleteSelectedBtn');

    // Function to update the state of the delete button
    function updateDeleteButtonState() {
        if (!deleteSelectedBtn) return; // Guard clause if button not present
        const checkedCheckboxes = document.querySelectorAll('.history-checkbox:checked');
        deleteSelectedBtn.disabled = checkedCheckboxes.length === 0;
    }

    // Event listener for "Select All" checkbox
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            historyCheckboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });
            updateDeleteButtonState();
        });
    }

    // Event listeners for individual history checkboxes
    historyCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            if (!this.checked) {
                if (selectAllCheckbox) {
                    selectAllCheckbox.checked = false;
                }
            } else {
                // Optional: Check if all are selected to check "Select All"
                const allChecked = Array.from(historyCheckboxes).every(cb => cb.checked);
                if (selectAllCheckbox) {
                    selectAllCheckbox.checked = allChecked;
                }
            }
            updateDeleteButtonState();
        });
    });

    // Initial state of the delete button
    updateDeleteButtonState();

    // Add event listener for the deleteSelectedBtn to send the delete request
    if (deleteSelectedBtn) {
        deleteSelectedBtn.addEventListener('click', function() {
            const checkedCheckboxes = document.querySelectorAll('.history-checkbox:checked');
            const historyIdsToDelete = Array.from(checkedCheckboxes).map(checkbox => checkbox.value);

            if (historyIdsToDelete.length > 0) {
                // Using the global confirm for simplicity, can be replaced with a custom modal
                if (confirm(deleteSelectedBtn.dataset.confirmMessage || 'Are you sure you want to delete the selected history entries?')) {
                    fetch('/delete_selected_history', { // Make sure this route exists in Flask
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            // Include CSRF token if your app uses it
                            // 'X-CSRFToken': '{{ csrf_token() }}' // This won't work in a static JS file
                        },
                        body: JSON.stringify({ history_ids: historyIdsToDelete }),
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert(data.message || 'Selected history entries deleted successfully.');
                            window.location.reload();
                        } else {
                            alert('Error deleting selected history entries: ' + (data.message || 'Unknown error'));
                        }
                    })
                    .catch((error) => {
                        console.error('Error:', error);
                        alert('An error occurred while trying to delete selected history entries.');
                    });
                }
            } else {
                alert(deleteSelectedBtn.dataset.noSelectionMessage || 'Please select at least one history entry to delete.');
            }
        });
    }
});
