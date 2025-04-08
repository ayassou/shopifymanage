/**
 * Main JavaScript file for Shopify Product Uploader
 */

// Debug logging setup
const debug = true;
const log = (msg) => {
    if (debug) console.log(`[DEBUG] ${msg}`);
};

// Make functions available globally
window.calculateTimeout = (formData) => {
    return 120000; // 2 minutes default timeout
};

window.showLoading = (button, formData) => {
    log('Starting generation process...');
    const originalText = button.innerHTML;

    // Create loading indicator
    const loadingIndicator = document.createElement('div');
    loadingIndicator.id = 'loading-indicator';
    loadingIndicator.innerHTML = `
        <div class="loading-spinner">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
        <p>Processing your request...</p>
    `;
    document.body.appendChild(loadingIndicator);

    // Update button state
    button.disabled = true;
    button.classList.add('button-loading');
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';

    // Show timeout notification after calculated timeout
    setTimeout(() => {
        log('Timeout reached, showing notification');
        const timeoutNotif = document.createElement('div');
        timeoutNotif.className = 'timeout-notification';
        timeoutNotif.innerHTML = '<i class="fas fa-clock me-2"></i>Taking longer than expected...';
        button.parentNode.appendChild(timeoutNotif);
    }, window.calculateTimeout(formData));

    // Return cleanup function
    return () => {
        button.disabled = false;
        button.classList.remove('button-loading');
        button.innerHTML = originalText;
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
        const timeoutNotif = button.parentNode.querySelector('.timeout-notification');
        if (timeoutNotif) {
            timeoutNotif.remove();
        }
    };
};

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
                const cleanup = window.showLoading(generateButton, new FormData(form));
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