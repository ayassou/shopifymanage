/**
 * Main JavaScript file for Shopify Product Uploader
 */

// Document ready function
document.addEventListener('DOMContentLoaded', function() {
    // Enable Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Enable Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto dismiss alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Add form validation styles
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Add loading indicator element (assuming it's a div)
    const loadingIndicator = document.createElement('div');
    loadingIndicator.id = 'loading-indicator';
    loadingIndicator.style.display = 'none'; // Initially hidden
    loadingIndicator.innerHTML = '<p>Generating Product...</p>';
    document.body.appendChild(loadingIndicator);

    const showLoading = () => {
        loadingIndicator.style.display = 'block';
    };

    const hideLoading = () => {
        loadingIndicator.style.display = 'none';
    };


    const form = document.getElementById('store-creation-form');
    if (form) {
        form.addEventListener('submit', async function(e) {
        e.preventDefault();
        showLoading();
        try {
            //Simulate API call - Replace with your actual API call
            const response = await fetch('/api/generateProduct', {
                method: 'POST',
                body: new FormData(this) // Assumes form uses FormData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || 'An unexpected error occurred.');
            }

            const data = await response.json();
            // Handle successful response
            console.log('Product generated successfully:', data);
            alert('Product generated successfully!');
        } catch (error) {
            console.error('Error generating product:', error);
            alert('Error generating product: ' + error.message);
        } finally {
            hideLoading();
        }
        });
    }
});