/**
 * Main JavaScript file for Shopify Product Uploader
 */

// Document ready function
const showLoading = (button, formData) => {
    const timeout = calculateTimeout(formData);

    // Create stop button
    const stopBtn = document.createElement('button');
    stopBtn.className = 'btn btn-sm btn-outline-danger stop-generation';
    stopBtn.innerHTML = '<i class="fas fa-times"></i>';
    stopBtn.title = 'Stop Generation';
    stopBtn.onclick = () => {
        if (confirm('Are you sure you want to stop the generation?')) {
            window.location.reload();
        }
    };

    // Create timeout notification
    const timeoutNotif = document.createElement('div');
    timeoutNotif.className = 'timeout-notification';
    timeoutNotif.innerHTML = '<i class="fas fa-clock me-2"></i>Taking longer than expected...';
    timeoutNotif.style.display = 'none';

    // Store original text and disable button
    button.disabled = true;
    button.classList.add('button-loading');
    button.dataset.originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';

    // Add stop button and notification after the generate button
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'button-container';
    button.parentNode.insertBefore(buttonContainer, button.nextSibling);
    buttonContainer.appendChild(button);
    buttonContainer.appendChild(stopBtn);
    buttonContainer.appendChild(timeoutNotif);

    // Show stop button and notification after timeout
    setTimeout(() => {
        stopBtn.classList.add('visible');
        timeoutNotif.style.display = 'block';
    }, timeout);
};

const calculateTimeout = (formData) => {
    // Base timeout 120 seconds
    let timeout = 120000;

    // Add time based on form type and data
    if (window.location.pathname.includes('ai_generator')) {
        // Add time for URL scraping if needed
        if (formData.get('input_type') === 'url') {
            timeout += 60000; // 60s for web scraping
        }
        const variantCount = parseInt(formData.get('variant_count')) || 1;
        timeout += variantCount * 45000; // 45s per variant
    } else if (window.location.pathname.includes('blog_generator')) {
        const wordCount = parseInt(formData.get('word_count')) || 1000;
        timeout += Math.floor(wordCount / 100) * 15000; // 15s per 100 words
    } else if (window.location.pathname.includes('page_generator')) {
        timeout += 180000; // Additional 180s for page generation
    }

    return timeout;
};

const hideLoading = () => {
    loadingIndicator.style.display = 'none';
    // Re-enable all generate buttons
    document.querySelectorAll('button[type="submit"]').forEach(button => {
        button.disabled = false;
        button.classList.remove('button-loading');
        // Restore original text
        if (button.dataset.originalText) {
            button.innerHTML = button.dataset.originalText;
        }
        // Remove stop button if exists
        const stopBtn = button.nextElementSibling;
        if (stopBtn && stopBtn.classList.contains('stop-generation')) {
            button.parentNode.removeChild(stopBtn);
        }
    });
};


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


    // Add form submission handlers to all generator forms
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const submitButton = this.querySelector('button[type="submit"]');
            showLoading(submitButton, new FormData(this));
        });
    });


    const form = document.getElementById('store-creation-form');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const submitButton = this.querySelector('button[type="submit"]');
            const formData = new FormData(this);
            showLoading(submitButton, formData);

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