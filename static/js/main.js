/**
 * Main JavaScript file for Shopify Product Uploader
 */

// Utility function to calculate timeout based on form data
function calculateTimeout(formData) {
    let timeout = 120000; // Base timeout: 120 seconds
    let url = formData.get('product_url');
    if (url) {
        timeout += 30000; // Add 30s for URL scraping
    }
    let variantCount = formData.get('variant_count') || 1;
    timeout += variantCount * 20000; // 20s per variant

    return timeout;
}

function showLoading(button, formData) {
    console.log('[DEBUG] Starting loading state...');
    const timeout = calculateTimeout(formData);
    console.log(`[DEBUG] Calculated timeout: ${timeout}ms`);

    // Create loading indicator
    const loadingIndicator = document.createElement('div');
    loadingIndicator.className = 'loading-indicator';
    loadingIndicator.innerHTML = `
        <div class="progress-wrapper">
            <span class="status-text">Generating...</span>
            <div class="spinner-border spinner-border-sm text-primary ms-2" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;

    // Add stop button
    const stopButton = document.createElement('button');
    stopButton.className = 'btn btn-sm btn-outline-danger ms-2';
    stopButton.innerHTML = '<i class="fas fa-stop"></i> Stop';
    stopButton.onclick = (e) => {
        e.preventDefault();
        window.location.reload();
    };
    loadingIndicator.querySelector('.progress-wrapper').appendChild(stopButton);

    // Replace button content
    button.disabled = true;
    button.innerHTML = loadingIndicator.outerHTML;
    console.log('[DEBUG] Button state updated');

    // Show timeout notification after the calculated timeout
    setTimeout(() => {
        console.log('[DEBUG] Timeout reached, showing notification');
        const timeoutDiv = document.createElement('div');
        timeoutDiv.className = 'alert alert-warning mt-2';
        timeoutDiv.innerHTML = '<i class="fas fa-clock me-2"></i>Taking longer than expected...';
        button.parentNode.appendChild(timeoutDiv);
    }, timeout);
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
    const debug = true;
    const log = (msg) => {
        if (debug) console.log(`[DEBUG] ${msg}`);
    };

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
    const log = (msg) => {
        console.log(`[Client] ${msg}`);
    };

    // Calculate timeout based on form data
    const calculateTimeout = (formData) => {
        return 120000; // 2 minutes default timeout
    };

    // Loading state handler
    const showLoading = (button, formData) => {
        log('Starting generation process...');

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

        log('UI updated to loading state');
        return originalText;
    };

    const hideLoading = () => {
        log('Generation process completed');
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

            log('Form submitted - collecting data');
            formData.forEach((value, key) => {
                log(`Form field: ${key} = ${value}`);
            });

            const originalText = showLoading(submitButton, formData);

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
                    hideLoading();
                }
            });
        }
    });
});