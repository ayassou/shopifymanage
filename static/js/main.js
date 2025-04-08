/**
 * Main JavaScript file for Shopify Product Uploader
 */

// Document ready function
window.showLoading = (button, formData) => {
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

    const calculateTimeout = (formData) => {
        // Base timeout 30 seconds
        let timeout = 30000;

        // Add time based on form type and data
        if (window.location.pathname.includes('ai_generator')) {
            const variantCount = formData.get('variant_count') || 1;
            timeout += variantCount * 10000; // 10s per variant
        } else if (window.location.pathname.includes('blog_generator')) {
            const wordCount = formData.get('word_count') || 1000;
            timeout += Math.floor(wordCount / 100) * 5000; // 5s per 100 words
        } else if (window.location.pathname.includes('page_generator')) {
            timeout += 45000; // Additional 45s for page generation
        }

        return timeout;
    };

    const showLoading = (button, formData) => {
        const timeout = calculateTimeout(formData);

        // Create stop button
        const stopBtn = document.createElement('button');
        stopBtn.className = 'btn btn-danger stop-generation';
        stopBtn.innerHTML = '<i class="fas fa-times me-2"></i>Stop Generation';
        stopBtn.onclick = () => {
            if (confirm('Are you sure you want to stop the generation?')) {
                window.location.reload();
            }
        };

        // Store original text and disable button
        button.disabled = true;
        button.classList.add('button-loading');
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';

        // Add stop button after the generate button
        button.parentNode.insertBefore(stopBtn, button.nextSibling);

        // Show stop button after timeout
        setTimeout(() => {
            stopBtn.classList.add('visible');
            button.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Taking longer than expected...';
        }, timeout);
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
            showLoading(submitButton, new FormData(this));

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