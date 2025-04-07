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
        
    # Blog API Methods
    
    def get_blogs(self):
        """
        Get a list of all blogs from the Shopify store
        
        Returns:
            dict: List of blogs
        """
        return self._make_request('GET', 'blogs.json')
        
    def get_blog(self, blog_id):
        """
        Get details of a specific blog
        
        Args:
            blog_id (str): ID of the blog to retrieve
            
        Returns:
            dict: Blog data
        """
        return self._make_request('GET', f'blogs/{blog_id}.json')
        
    def create_blog(self, blog_data):
        """
        Create a new blog in Shopify
        
        Args:
            blog_data (dict): Blog data in Shopify API format
            
        Returns:
            dict: Response from the Shopify API
        """
        return self._make_request('POST', 'blogs.json', data=blog_data)
        
    def get_articles(self, blog_id, limit=50):
        """
        Get articles from a specific blog
        
        Args:
            blog_id (str): ID of the blog
            limit (int): Maximum number of articles to retrieve
            
        Returns:
            dict: List of articles
        """
        return self._make_request('GET', f'blogs/{blog_id}/articles.json?limit={limit}')
        
    def get_article(self, blog_id, article_id):
        """
        Get a specific article from a blog
        
        Args:
            blog_id (str): ID of the blog
            article_id (str): ID of the article
            
        Returns:
            dict: Article data
        """
        return self._make_request('GET', f'blogs/{blog_id}/articles/{article_id}.json')
        
    def create_article(self, blog_id, article_data):
        """
        Create a new article in a blog
        
        Args:
            blog_id (str): ID of the blog
            article_data (dict): Article data in Shopify API format
            
        Returns:
            dict: Response from the Shopify API
        """
        return self._make_request('POST', f'blogs/{blog_id}/articles.json', data=article_data)
        
    def update_article(self, blog_id, article_id, article_data):
        """
        Update an existing article
        
        Args:
            blog_id (str): ID of the blog
            article_id (str): ID of the article to update
            article_data (dict): Updated article data
            
        Returns:
            dict: Response from the Shopify API
        """
        return self._make_request('PUT', f'blogs/{blog_id}/articles/{article_id}.json', data=article_data)
        
    def delete_article(self, blog_id, article_id):
        """
        Delete an article from a blog
        
        Args:
            blog_id (str): ID of the blog
            article_id (str): ID of the article to delete
            
        Returns:
            dict: Response from the Shopify API
        """
        return self._make_request('DELETE', f'blogs/{blog_id}/articles/{article_id}.json')
        
    # Page API Methods
    
    def get_pages(self, limit=50):
        """
        Get a list of all pages from the Shopify store
        
        Args:
            limit (int): Maximum number of pages to retrieve
            
        Returns:
            dict: List of pages
        """
        return self._make_request('GET', f'pages.json?limit={limit}')
        
    def get_page(self, page_id):
        """
        Get details of a specific page
        
        Args:
            page_id (str): ID of the page to retrieve
            
        Returns:
            dict: Page data
        """
        return self._make_request('GET', f'pages/{page_id}.json')
        
    def create_page(self, page_data):
        """
        Create a new page in Shopify
        
        Args:
            page_data (dict): Page data in Shopify API format
            
        Returns:
            dict: Response from the Shopify API
        """
        return self._make_request('POST', 'pages.json', data=page_data)
        
    def update_page(self, page_id, page_data):
        """
        Update an existing page
        
        Args:
            page_id (str): ID of the page to update
            page_data (dict): Updated page data
            
        Returns:
            dict: Response from the Shopify API
        """
        return self._make_request('PUT', f'pages/{page_id}.json', data=page_data)
        
    def delete_page(self, page_id):
        """
        Delete a page
        
        Args:
            page_id (str): ID of the page to delete
            
        Returns:
            dict: Response from the Shopify API
        """
        return self._make_request('DELETE', f'pages/{page_id}.json')
        
    # Product Image API Methods
    
    def get_product_images(self, product_id=None, collection_id=None, limit=50):
        """
        Get images from products in the Shopify store
        
        Args:
            product_id (str, optional): ID of a specific product to get images from
            collection_id (str, optional): ID of a collection to get images from
            limit (int): Maximum number of product results to retrieve
            
        Returns:
            list: List of product images with product ID reference
        """
        images = []
        
        try:
            # If a specific product ID is provided
            if product_id:
                product_data = self.get_product(product_id)
                if 'product' in product_data and 'images' in product_data['product']:
                    for image in product_data['product']['images']:
                        image['product_id'] = product_id
                        images.append(image)
                return images
                
            # If a collection ID is provided
            if collection_id:
                products_response = self._make_request('GET', f'collections/{collection_id}/products.json?limit={limit}')
                products = products_response.get('products', [])
            else:
                # Otherwise get all products
                products_response = self._make_request('GET', f'products.json?limit={limit}')
                products = products_response.get('products', [])
            
            # Extract images from each product
            for product in products:
                product_id = product['id']
                for image in product.get('images', []):
                    image['product_id'] = product_id
                    images.append(image)
                    
            return images
            
        except Exception as e:
            logger.error(f"Error getting product images: {str(e)}")
            return []
    
    def get_product_image(self, product_id, image_id):
        """
        Get a specific product image
        
        Args:
            product_id (str): ID of the product
            image_id (str): ID of the image
            
        Returns:
            dict: Image data
        """
        return self._make_request('GET', f'products/{product_id}/images/{image_id}.json')
    
    def update_product_image(self, product_id, image_id, alt_text=None, metadata=None):
        """
        Update a product image, primarily for alt text and metadata
        
        Args:
            product_id (str): ID of the product
            image_id (str): ID of the image to update
            alt_text (str, optional): New alt text for the image
            metadata (dict, optional): Metadata to add to the image
            
        Returns:
            dict: Response from the Shopify API
        """
        image_data = {
            "image": {}
        }
        
        if alt_text is not None:
            image_data["image"]["alt"] = alt_text
            
        if metadata is not None:
            image_data["image"]["metafields"] = metadata
            
        return self._make_request('PUT', f'products/{product_id}/images/{image_id}.json', data=image_data)
    
    def upload_product_image(self, product_id, image_url=None, image_base64=None, alt_text=None, position=1):
        """
        Upload a new image to a product
        
        Args:
            product_id (str): ID of the product
            image_url (str, optional): URL of the image to upload
            image_base64 (str, optional): Base64-encoded image data
            alt_text (str, optional): Alt text for the image
            position (int): Position of the image in the product gallery
            
        Returns:
            dict: Response from the Shopify API
        """
        image_data = {
            "image": {
                "position": position
            }
        }
        
        if alt_text is not None:
            image_data["image"]["alt"] = alt_text
            
        if image_url is not None:
            image_data["image"]["src"] = image_url
        elif image_base64 is not None:
            image_data["image"]["attachment"] = image_base64
        else:
            raise ValueError("Either image_url or image_base64 must be provided")
            
        return self._make_request('POST', f'products/{product_id}/images.json', data=image_data)
        
    def delete_product_image(self, product_id, image_id):
        """
        Delete a product image
        
        Args:
            product_id (str): ID of the product
            image_id (str): ID of the image to delete
            
        Returns:
            dict: Response from the Shopify API
        """
        return self._make_request('DELETE', f'products/{product_id}/images/{image_id}.json')
