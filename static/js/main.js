/**
 * Main JavaScript file for Shopify Product Uploader
 */

// Debug logging setup
const debug = true;
const log = (msg) => {
    if (debug) console.log(`[DEBUG] ${msg}`);
};

// Calculate timeout based on form data
function calculateTimeout(formData) {
    console.log("[DEBUG] Calculating timeout...");
    // Base timeout of 2 minutes
    return 120000;
}

// Show loading state with progress
function showLoading(button, formData) {
    console.log("[DEBUG] Showing loading state...");
    const timeout = calculateTimeout(formData);

    // Create loading overlay
    const loadingOverlay = document.createElement('div');
    loadingOverlay.classList.add('loading-overlay');
    loadingOverlay.innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <p class="mt-2">Generating product data...</p>
    `;
    document.body.appendChild(loadingOverlay);

    // Update button state
    button.disabled = true;
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';

    // Return cleanup function
    return () => {
        loadingOverlay.remove();
        button.disabled = false;
        button.innerHTML = originalText;
    };
}

// Initialize page when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    log('Page loaded, initializing...');

    // Enable Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

    // Enable Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.forEach(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));

    // Auto dismiss alerts
    setTimeout(() => {
        document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Add form validation styles
    document.querySelectorAll('.needs-validation').forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Add form submission handlers
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            log('Form submitted, processing...');
            const generateButton = e.submitter;
            if (generateButton && generateButton.classList.contains('generate-button')) {
                const cleanup = showLoading(generateButton, new FormData(form));
                //Example of how to use cleanup function after fetch.  Could be improved.
                // fetch(form.action, {method: 'POST', body: new FormData(form)})
                // .then(response => {
                //     if(!response.ok) throw new Error("Network response was not ok");
                //     return response.json();
                // })
                // .then(data => {
                //     //Handle success here
                // })
                // .catch(error => {
                //     //Handle error here
                // })
                // .finally(cleanup);
            }
        });
    });
});