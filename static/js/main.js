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
    // Base timeout of 2 minutes
    return 120000;
}

// Show loading state
function showLoading(button, formData) {
    console.log('Starting loading process...');
    const originalText = button.innerHTML;

    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';

    // Return cleanup function
    return () => {
        button.disabled = false;
        button.innerHTML = originalText;
    };
}


// Add form submission handler
document.addEventListener('DOMContentLoaded', () => {
    // Enable Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Enable Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
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


    // Add form submission handler
    // Global console logging setup

    // Add form submission handler
    document.addEventListener('DOMContentLoaded', () => {
        log('Page loaded, initializing form handlers...');
        const form = document.querySelector('form');
        if (form) {
            log('Form found, attaching submit handler...');
            form.addEventListener('submit', (e) => {
                log('Form submitted, processing...');
                const generateButton = e.submitter;
                if (generateButton && generateButton.classList.contains('generate-button')) {
                    showLoading(generateButton, new FormData(form));
                }
            });
        }
    });

        // Add form submission handlers to all generator forms
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                const submitButton = this.querySelector('button[type="submit"]');
                showLoading(submitButton, new FormData(this));
            });
        });


        // Logging utility
    const log2 = (msg) => {
        console.log(`[Client] ${msg}`);
    };

    // Calculate timeout based on form data
    const calculateTimeout2 = (formData) => {
        return 120000; // 2 minutes default timeout
    };

    // Loading state handler
    const showLoading2 = (button, formData) => {
        log2('Starting generation process...');

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
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';

        log2('UI updated to loading state');
        return originalText;
    };

    const hideLoading2 = () => {
        log2('Generation process completed');
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }

        // Re-enable all generate buttons
        document.querySelectorAll('button[type="submit"]').forEach(button => {
            button.disabled = false;
            button.classList.remove('button-loading');
            if (button.dataset.originalText) {
                button.innerHTML = button.dataset.originalText;
            }
        });
    };

    // Form submission handler
    const form = document.getElementById('store-creation-form');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const submitButton = this.querySelector('button[type="submit"]');
            const formData = new FormData(this);

            log2('Form submitted - collecting data');
            formData.forEach((value, key) => {
                log2(`Form field: ${key} = ${value}`);
            });

            const originalText = showLoading2(submitButton, formData);

                try {
                    const response = await fetch(this.action, {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) {
                        throw new Error('Generation failed');
                    }

                    // Redirect to results or handle response
                    const result = await response.json();
                    if (result.redirect) {
                        window.location.href = result.redirect;
                    }
                } catch (error) {
                    console.error('Generation error:', error);
                    // Show error state but keep stop button visible
                    const timeoutNotif = document.querySelector('.timeout-notification');
                    if (timeoutNotif) {
                        timeoutNotif.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Generation failed';
                        timeoutNotif.style.display = 'inline-block';
                        timeoutNotif.classList.add('text-danger');
                    }
                } finally {
                    hideLoading2();
                }
            });
        }
    });
});