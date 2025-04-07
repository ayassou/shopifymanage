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
    
    return {
        'valid': len(errors) == 0,
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
            # Extract basic product information
            product_data = {
                'product': {
                    'title': row['title'],
                    'body_html': row.get('description', ''),
                    'vendor': row.get('vendor', ''),
                    'product_type': row.get('product_type', ''),
                    'tags': row.get('tags', ''),
                    'status': row.get('status', 'active'),
                    'published': row.get('published', True),
                }
            }
            
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
            
            # Additional image URLs (image_url2, image_url3, etc.)
            additional_images = []
            for col in df.columns:
                if col.startswith('image_url') and col != 'image_url' and pd.notna(row[col]):
                    additional_images.append({'src': row[col]})
            
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
