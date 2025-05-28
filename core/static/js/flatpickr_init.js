// static/js/admin/flatpickr_init.js
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Flatpickr on all input fields with the class "flatpickr"
    flatpickr('.flatpickr', {
        enableTime: true,
        noCalendar: true,
        dateFormat: 'H:i', // Matches Django's expected format
        time_24hr: false,
        allowInput: true, // Allow manual input (including clearing)
        onValueUpdate: function(selectedDates, dateStr, instance) {
            if (!dateStr) {
                instance.input.value = ''; // Clear the input if the value is empty
            }
        }
    // Initialize Flatpickr for the "date_employed" field (date picker)
    });
    flatpickr("#date_employed", {
        dateFormat: "Y-m-d",   // Ensure date is formatted as 'YYYY-MM-DD'
        altInput: true,         // Human-readable format in the input (e.g., "December 31, 2024")
        altFormat: "F j, Y",    // Alternative format to show in the input field
        allowInput: true,       // Allow users to manually enter the date
        onValueUpdate: function(selectedDates, dateStr, instance) {
            if (!dateStr) {
                instance.input.value = ''; // Clear input if no date is selected
            }
        }
    });
});

