import pandas as pd
import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def validate_data(df):
    """
    Validate the data in the DataFrame
    
    Args:
        df (pandas.DataFrame): The DataFrame to validate
        
    Returns:
        dict: Validation result with 'valid' (bool) and 'errors' (list)
    """
    errors = []
    warnings = []
    
    # Check for required columns
    required_columns = ['title', 'price']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        return {'valid': False, 'errors': errors}
    
    # Check for empty titles
    if df['title'].isnull().any():
        errors.append("Some products are missing titles")
    
    # Check for valid prices
    if 'price' in df.columns:
        invalid_prices = df['price'].apply(
            lambda x: not (isinstance(x, (int, float)) or 
                          (isinstance(x, str) and re.match(r'^\d+(\.\d{1,2})?$', x)))
        )
        if invalid_prices.any():
            invalid_indices = df.index[invalid_prices].tolist()
            errors.append(f"Invalid prices at rows: {invalid_indices}")
    
    # Check for valid image URLs if present
    if 'image_url' in df.columns:
        invalid_urls = df['image_url'].apply(
            lambda x: x is not None and not pd.isna(x) and not bool(urlparse(str(x)).netloc)
        )
        if invalid_urls.any():
            invalid_indices = df.index[invalid_urls].tolist()
            errors.append(f"Invalid image URLs at rows: {invalid_indices}")
    
    # SEO Validation Checks
    
    # Check meta title length (best practice is 50-60 characters)
    if 'meta_title' in df.columns:
        long_titles = df['meta_title'].apply(
            lambda x: x is not None and not pd.isna(x) and len(str(x)) > 70
        )
        if long_titles.any():
            long_indices = df.index[long_titles].tolist()
            warnings.append(f"Meta titles exceeding 70 characters at rows: {long_indices} (may be truncated in search results)")
    
    # Check meta description length (best practice is 150-160 characters)
    if 'meta_description' in df.columns:
        long_descriptions = df['meta_description'].apply(
            lambda x: x is not None and not pd.isna(x) and len(str(x)) > 160
        )
        if long_descriptions.any():
            long_indices = df.index[long_descriptions].tolist()
            warnings.append(f"Meta descriptions exceeding 160 characters at rows: {long_indices} (may be truncated in search results)")
    
    # Validate URL handles format (lowercase, alphanumeric with hyphens)
    if 'url_handle' in df.columns:
        invalid_handles = df['url_handle'].apply(
            lambda x: x is not None and not pd.isna(x) and not bool(re.match(r'^[a-z0-9-]+$', str(x)))
        )
        if invalid_handles.any():
            invalid_indices = df.index[invalid_handles].tolist()
            errors.append(f"Invalid URL handles at rows: {invalid_indices} (should contain only lowercase letters, numbers, and hyphens)")
    
    # Validate category_hierarchy format
    if 'category_hierarchy' in df.columns:
        invalid_categories = df['category_hierarchy'].apply(
            lambda x: x is not None and not pd.isna(x) and '>' not in str(x)
        )
        if invalid_categories.any():
            invalid_indices = df.index[invalid_categories].tolist()
            warnings.append(f"Category hierarchies at rows: {invalid_indices} should be formatted as 'Parent > Child > Grandchild'")
    
    # Add warnings to errors list but mark them differently
    if warnings:
        for warning in warnings:
            errors.append(f"WARNING: {warning}")
    
    return {
        'valid': len([e for e in errors if not e.startswith('WARNING:')]) == 0,
        'errors': errors
    }

def process_data(df, shopify_client):
    """
    Process the data and upload to Shopify
    
    Args:
        df (pandas.DataFrame): The DataFrame with product data
        shopify_client (ShopifyClient): The Shopify API client
        
    Returns:
        list: Results of the processing with status for each product
    """
    logger.info(f"Processing {len(df)} products")
    results = []
    
    # Process each row in the DataFrame
    for index, row in df.iterrows():
        try:
            # Validate required fields
            if 'title' not in row or pd.isna(row['title']):
                raise ValueError("Product title is required")

            # Extract basic product information with defaults
            product_data = {
                'product': {
                    'title': str(row['title']).strip(),
                    'body_html': str(row.get('description', '')).strip(),
                    'vendor': str(row.get('vendor', 'Default Vendor')).strip(),
                    'product_type': str(row.get('product_type', 'General')).strip(),
                    'tags': str(row.get('tags', '')).strip(),
                    'status': 'active',
                    'published': True,
                }
            }
            
            # Add SEO fields if present
            if 'meta_title' in row and pd.notna(row['meta_title']):
                product_data['product']['metafields_global_title_tag'] = row['meta_title']
            
            if 'meta_description' in row and pd.notna(row['meta_description']):
                product_data['product']['metafields_global_description_tag'] = row['meta_description']
            
            # Handle custom URL handle (slug)
            if 'url_handle' in row and pd.notna(row['url_handle']):
                product_data['product']['handle'] = row['url_handle']
            
            # Add meta keywords via metafields if available
            if 'meta_keywords' in row and pd.notna(row['meta_keywords']):
                if 'metafields' not in product_data['product']:
                    product_data['product']['metafields'] = []
                
                product_data['product']['metafields'].append({
                    'key': 'keywords',
                    'value': row['meta_keywords'],
                    'namespace': 'global',
                    'value_type': 'string'
                })
            
            # Add hierarchical categorization via collections tags if available
            if 'category_hierarchy' in row and pd.notna(row['category_hierarchy']):
                categories = str(row['category_hierarchy']).split('>')
                categories = [cat.strip() for cat in categories]
                
                # Add hierarchical categories to tags for better SEO
                existing_tags = product_data['product']['tags']
                hierarchical_tags = ', '.join([f"category:{cat}" for cat in categories])
                
                if existing_tags:
                    product_data['product']['tags'] = f"{existing_tags}, {hierarchical_tags}"
                else:
                    product_data['product']['tags'] = hierarchical_tags
            
            # Add price as a variant
            variant = {
                'price': str(row['price']),
                'sku': row.get('sku', ''),
                'inventory_management': row.get('inventory_management', 'shopify'),
                'inventory_quantity': int(row.get('inventory_quantity', 0)),
                'requires_shipping': row.get('requires_shipping', True),
                'taxable': row.get('taxable', True),
                'weight': float(row.get('weight', 0)),
                'weight_unit': row.get('weight_unit', 'kg'),
                'inventory_policy': row.get('inventory_policy', 'deny'),
            }
            
            # Handle options and variants
            options = []
            option_columns = [col for col in df.columns if col.startswith('option')]
            
            if option_columns:
                for i, option_col in enumerate(option_columns, 1):
                    option_name = row.get(f'option{i}_name', f'Option {i}')
                    option_value = row.get(option_col)
                    if pd.notna(option_value):
                        options.append({
                            'name': option_name,
                            'values': [option_value]
                        })
                        variant[f'option{i}'] = option_value
            
            if options:
                product_data['product']['options'] = options
            
            # Add the variant to the product
            product_data['product']['variants'] = [variant]
            
            # Add images if present
            if 'image_url' in row and pd.notna(row['image_url']):
                product_data['product']['images'] = [{
                    'src': row['image_url']
                }]
                
                # Add alt text for the image if available (good for SEO)
                if 'image_alt' in row and pd.notna(row['image_alt']):
                    product_data['product']['images'][0]['alt'] = row['image_alt']
            
            # Additional image URLs (image_url2, image_url3, etc.)
            additional_images = []
            for col in df.columns:
                if col.startswith('image_url') and col != 'image_url' and pd.notna(row[col]):
                    image_data = {'src': row[col]}
                    
                    # Add alt text for additional images if available
                    alt_col = col.replace('image_url', 'image_alt')
                    if alt_col in row and pd.notna(row[alt_col]):
                        image_data['alt'] = row[alt_col]
                        
                    additional_images.append(image_data)
            
            if additional_images:
                if 'images' not in product_data['product']:
                    product_data['product']['images'] = []
                product_data['product']['images'].extend(additional_images)
            
            # Create the product in Shopify
            logger.debug(f"Creating product: {product_data}")
            response = shopify_client.create_product(product_data)
            
            # Add the result
            product_id = response['product']['id']
            product_title = response['product']['title']
            results.append({
                'row': index + 2,  # +2 to account for 0-indexing and header row
                'title': product_title,
                'id': product_id,
                'status': 'success',
                'message': f"Created product {product_title} with ID {product_id}"
            })
            
        except Exception as e:
            logger.error(f"Error processing row {index}: {str(e)}")
            results.append({
                'row': index + 2,
                'title': row.get('title', 'Unknown'),
                'status': 'error',
                'message': str(e)
            })
    
    return results
