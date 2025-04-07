import logging
import requests
from bs4 import BeautifulSoup
import trafilatura
from urllib.parse import urljoin, urlparse

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ProductScraper:
    """
    A class for scraping product data from e-commerce websites.
    This provides specialized methods for extracting product information,
    images, and other details from common e-commerce platforms.
    """
    
    def __init__(self):
        """Initialize the product scraper."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
        })
    
    def get_website_text_content(self, url):
        """
        Extract the main text content from a website.
        
        Args:
            url (str): The URL of the website
            
        Returns:
            str: The extracted text content
        """
        try:
            # Download the website content
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                raise ValueError(f"Failed to download content from {url}")
            
            # Extract the main text content
            text = trafilatura.extract(downloaded)
            if not text:
                raise ValueError(f"Failed to extract text content from {url}")
            
            return text
        except Exception as e:
            logger.error(f"Error extracting text content from {url}: {str(e)}")
            raise
    
    def extract_product_images(self, url, limit=5):
        """
        Extract product images from a website.
        
        Args:
            url (str): The URL of the website
            limit (int): Maximum number of images to extract
            
        Returns:
            list: List of image URLs
        """
        try:
            # Parse the URL to extract the domain
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Download the page
            response = self.session.get(url)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all image tags
            image_tags = soup.find_all('img')
            
            # Filter for likely product images
            product_images = []
            for img in image_tags:
                # Skip small images, icons, and logos
                if 'src' not in img.attrs:
                    continue
                
                # Get image source
                src = img['src']
                
                # Handle relative URLs
                if not src.startswith(('http://', 'https://')):
                    src = urljoin(base_url, src)
                
                # Filter out common non-product images
                skip_patterns = [
                    'logo', 'icon', 'banner', 'button', 
                    'background', 'footer', 'header', 'nav'
                ]
                if any(pattern in src.lower() for pattern in skip_patterns):
                    continue
                
                # Check for likely product image indicators
                product_indicators = [
                    'product', 'item', 'goods', 'img', 'image',
                    'photo', 'picture', 'large', 'detail', 'zoom'
                ]
                
                # Prioritize likely product images
                is_likely_product = any(indicator in src.lower() for indicator in product_indicators)
                
                # Check common paths for product images
                path = urlparse(src).path.lower()
                if '/products/' in path or '/product/' in path or '/images/products' in path:
                    is_likely_product = True
                
                # Check for image size in attributes
                width = img.get('width')
                height = img.get('height')
                
                # Convert to integers if possible
                try:
                    width = int(width) if width else 0
                    height = int(height) if height else 0
                except ValueError:
                    width = 0
                    height = 0
                
                # Skip very small images
                if (width > 0 and width < 100) or (height > 0 and height < 100):
                    continue
                
                # If it passes all filters, add to product images
                if is_likely_product:
                    product_images.insert(0, src)  # Prioritize
                else:
                    product_images.append(src)
            
            # Return the top N images
            return product_images[:limit]
            
        except Exception as e:
            logger.error(f"Error extracting product images from {url}: {str(e)}")
            return []
    
    def extract_structured_data(self, url):
        """
        Extract structured product data from a website (JSON-LD, microdata, etc.).
        
        Args:
            url (str): The URL of the website
            
        Returns:
            dict: Structured product data if available
        """
        try:
            # Download the page
            response = self.session.get(url)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for JSON-LD structured data
            structured_data = {}
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            
            import json
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Look for Product schema
                    if isinstance(data, dict) and '@type' in data and data['@type'] == 'Product':
                        structured_data['product_title'] = data.get('name', '')
                        structured_data['product_description'] = data.get('description', '')
                        
                        # Extract price
                        if 'offers' in data:
                            offers = data['offers']
                            if isinstance(offers, dict):
                                structured_data['price'] = offers.get('price', '')
                            elif isinstance(offers, list) and len(offers) > 0:
                                structured_data['price'] = offers[0].get('price', '')
                        
                        # Extract brand
                        if 'brand' in data and isinstance(data['brand'], dict):
                            structured_data['vendor'] = data['brand'].get('name', '')
                        
                        # Extract image URLs
                        if 'image' in data:
                            if isinstance(data['image'], str):
                                structured_data['image_urls'] = [data['image']]
                            elif isinstance(data['image'], list):
                                structured_data['image_urls'] = data['image']
                        
                        break  # Found what we need
                        
                    # Look for specific e-commerce platforms
                    # Shopify
                    if isinstance(data, dict) and 'Shopify' in script.string:
                        if 'product' in data:
                            product = data['product']
                            structured_data['product_title'] = product.get('title', '')
                            structured_data['product_description'] = product.get('description', '')
                            structured_data['product_type'] = product.get('type', '')
                            structured_data['vendor'] = product.get('vendor', '')
                            
                            if 'variants' in product and len(product['variants']) > 0:
                                structured_data['price'] = product['variants'][0].get('price', '')
                                
                            if 'images' in product and len(product['images']) > 0:
                                structured_data['image_urls'] = product['images']
                            
                            break  # Found what we need
                            
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.warning(f"Error parsing JSON-LD: {e}")
                    continue
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Error extracting structured data from {url}: {str(e)}")
            return {}