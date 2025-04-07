import requests
import time
import logging
from base64 import b64encode
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class ShopifyClient:
    """Client for interacting with the Shopify API"""
    
    def __init__(self, api_key, password, store_url, api_version):
        """
        Initialize the Shopify API client
        
        Args:
            api_key (str): Shopify API key
            password (str): Shopify API password or access token
            store_url (str): Shopify store URL (e.g., mystore.myshopify.com)
            api_version (str): Shopify API version (e.g., 2023-07)
        """
        self.api_key = api_key
        self.password = password
        self.store_url = store_url.rstrip('/')
        if not self.store_url.startswith('https://'):
            self.store_url = f'https://{self.store_url}'
        self.api_version = api_version
        self.base_url = f'{self.store_url}/admin/api/{self.api_version}'
        
        # Set up authentication
        auth_str = f"{self.api_key}:{self.password}"
        self.auth_header = b64encode(auth_str.encode()).decode()
        self.headers = {
            'Authorization': f'Basic {self.auth_header}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # For rate limiting
        self.last_request_time = 0
        self.rate_limit_delay = 0.5  # 500ms between requests to avoid rate limiting
    
    def _make_request(self, method, endpoint, data=None):
        """
        Make a request to the Shopify API with rate limiting
        
        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE)
            endpoint (str): API endpoint
            data (dict, optional): Data to send in the request
            
        Returns:
            dict: Response data
        """
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        
        url = urljoin(self.base_url, endpoint)
        logger.debug(f"Making {method} request to {url}")
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data
            )
            self.last_request_time = time.time()
            
            # Check for rate limiting headers
            if 'X-Shopify-Shop-Api-Call-Limit' in response.headers:
                limit_header = response.headers['X-Shopify-Shop-Api-Call-Limit']
                current, limit = map(int, limit_header.split('/'))
                if current > limit * 0.8:  # If we're using more than 80% of our limit
                    self.rate_limit_delay = 1.0  # Increase delay
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status code: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise
    
    def test_connection(self):
        """Test the connection to the Shopify API"""
        try:
            response = self._make_request('GET', 'shop.json')
            return True, response
        except Exception as e:
            return False, str(e)
    
    def create_product(self, product_data):
        """
        Create a new product in Shopify
        
        Args:
            product_data (dict): Product data in Shopify API format
            
        Returns:
            dict: Response from the Shopify API
        """
        return self._make_request('POST', 'products.json', data=product_data)
    
    def update_product(self, product_id, product_data):
        """
        Update an existing product in Shopify
        
        Args:
            product_id (str): ID of the product to update
            product_data (dict): Updated product data
            
        Returns:
            dict: Response from the Shopify API
        """
        return self._make_request('PUT', f'products/{product_id}.json', data=product_data)
    
    def get_product(self, product_id):
        """
        Get a product from Shopify
        
        Args:
            product_id (str): ID of the product to get
            
        Returns:
            dict: Product data
        """
        return self._make_request('GET', f'products/{product_id}.json')
    
    def search_products(self, query):
        """
        Search for products in Shopify
        
        Args:
            query (str): Search query
            
        Returns:
            dict: Search results
        """
        return self._make_request('GET', f'products.json?title={query}')
