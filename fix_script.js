document.addEventListener('DOMContentLoaded', function() {
    try {
        // Show/hide appropriate input sections based on selected input type
        const inputTypeRadios = document.querySelectorAll('input[name="input_type"]');
        if (!inputTypeRadios || inputTypeRadios.length === 0) return;
        
        const urlInputSection = document.getElementById('urlInputSection');
        const uploadInputSection = document.getElementById('uploadInputSection');
        const shopifyInputSection = document.getElementById('shopifyInputSection');
        const searchInputSection = document.getElementById('searchInputSection');
        
        if (!urlInputSection || !uploadInputSection || !shopifyInputSection || !searchInputSection) return;
        
        function updateInputSections() {
            const checkedRadio = document.querySelector('input[name="input_type"]:checked');
            if (!checkedRadio) return;
            
            const selectedValue = checkedRadio.value;
            
            // Hide all sections first
            urlInputSection.classList.add('d-none');
            uploadInputSection.classList.add('d-none');
            shopifyInputSection.classList.add('d-none');
            searchInputSection.classList.add('d-none');
            
            // Show the selected section
            if (selectedValue === 'url') {
                urlInputSection.classList.remove('d-none');
            } else if (selectedValue === 'upload') {
                uploadInputSection.classList.remove('d-none');
            } else if (selectedValue === 'shopify') {
                shopifyInputSection.classList.remove('d-none');
            } else if (selectedValue === 'search') {
                searchInputSection.classList.remove('d-none');
            }
        }
        
        // Add change event listeners to all input type radio buttons
        inputTypeRadios.forEach(function(radio) {
            radio.addEventListener('change', updateInputSections);
        });
        
        // Initialize sections based on default selection
        updateInputSections();
        
        // Update output format options based on input type
        const outputFormatSelect = document.getElementById('output_format');
        if (!outputFormatSelect) return;
        
        inputTypeRadios.forEach(function(radio) {
            radio.addEventListener('change', function() {
                const checkedRadio = document.querySelector('input[name="input_type"]:checked');
                if (!checkedRadio) return;
                
                const selectedValue = checkedRadio.value;
                
                // Enable all options first
                for (let i = 0; i < outputFormatSelect.options.length; i++) {
                    outputFormatSelect.options[i].disabled = false;
                }
                
                // Disable incompatible options
                if (selectedValue === 'shopify') {
                    // If Shopify is selected as input, prefer Shopify update as output
                    for (let i = 0; i < outputFormatSelect.options.length; i++) {
                        if (outputFormatSelect.options[i].value === 'shopify_update') {
                            outputFormatSelect.value = 'shopify_update';
                            break;
                        }
                    }
                }
            });
        });
    } catch (e) {
        console.log("Error initializing image caption form:", e);
    }
});
