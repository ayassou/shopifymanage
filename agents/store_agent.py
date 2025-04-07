import json
import logging
import os
from datetime import datetime

from models import db, StoreSetup, StorePage, StoreProduct, ThemeCustomization, AgentTask, ProductSource

logger = logging.getLogger(__name__)

class StoreAgent:
    """
    Agent for setting up and configuring a Shopify store.
    
    This agent automates the process of creating a store, setting up theme,
    adding products, and generating content pages.
    """
    
    def __init__(self, shopify_client=None, ai_service=None):
        """
        Initialize the Store Agent with the necessary API connections.
        
        Args:
            shopify_client: The Shopify API client
            ai_service: AI service for content generation
        """
        self.shopify_client = shopify_client
        self.ai_service = ai_service
        
    def create_store(self, store_params, user_id=None, settings_id=None, task_id=None):
        """
        Initialize a new store setup.
        
        Args:
            store_params (dict): Parameters for the store setup
            user_id (int): User ID associated with the store
            settings_id (int): ShopifySettings ID to use for API calls
            task_id (int): Optional AgentTask ID for tracking progress
            
        Returns:
            dict: Task information including task_id and store_id
        """
        # Create a new task if one doesn't exist
        if not task_id:
            task = AgentTask(
                user_id=user_id,
                task_type='store_setup',
                status='running',
                progress=0,
                parameters=json.dumps(store_params)
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
            
        # Update existing task if provided
        else:
            task = AgentTask.query.get(task_id)
            if not task:
                raise ValueError(f"Task with ID {task_id} not found")
            task.status = 'running'
            task.progress = 0
            db.session.commit()
            
        try:
            # Create the store record
            store = StoreSetup(
                user_id=user_id,
                settings_id=settings_id,
                store_name=store_params.get('store_name'),
                store_url=store_params.get('store_url'),
                niche=store_params.get('niche'),
                logo_url=store_params.get('logo_url'),
                theme_id=store_params.get('theme_id'),
                currency=store_params.get('currency', 'USD'),
                status='pending',
                settings_json=json.dumps(store_params.get('settings', {}))
            )
            db.session.add(store)
            db.session.commit()
            
            # Update task with store ID
            task.result_id = store.id
            task.result_type = 'store_setup'
            task.progress = 10
            db.session.commit()
            
            # Trigger the actual store setup (in a real app, this would be a background task)
            result = self._setup_store(store.id, task_id)
            
            return {
                'task_id': task_id,
                'store_id': store.id,
                'status': result.get('status', 'pending'),
                'details': result.get('details', {})
            }
            
        except Exception as e:
            logger.error(f"Error in store creation: {str(e)}")
            task = AgentTask.query.get(task_id)
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _setup_store(self, store_id, task_id=None):
        """
        Perform the actual store setup process.
        
        This includes:
        1. Creating the store in Shopify (if not already created)
        2. Setting up the theme
        3. Creating essential pages
        4. Configuring settings
        
        Args:
            store_id (int): StoreSetup ID
            task_id (int): AgentTask ID for updating progress
            
        Returns:
            dict: Result of the setup process
        """
        store = StoreSetup.query.get(store_id)
        if not store:
            raise ValueError(f"Store with ID {store_id} not found")
        
        # Update task and store status
        task = None
        if task_id:
            task = AgentTask.query.get(task_id)
            task.progress = 15
            db.session.commit()
        
        store.status = 'in_progress'
        db.session.commit()
        
        # Connect to Shopify (in a real implementation)
        # For now, we'll simulate the process
        try:
            # 1. Verify or create store in Shopify
            if task:
                task.progress = 20
                db.session.commit()
            
            # 2. Install and configure theme
            theme_result = self._setup_theme(store_id)
            if task:
                task.progress = 40
                db.session.commit()
            
            # 3. Create essential pages
            pages_result = self._create_essential_pages(store_id)
            if task:
                task.progress = 70
                db.session.commit()
            
            # 4. Configure store settings
            settings_result = self._configure_store_settings(store_id)
            if task:
                task.progress = 90
                db.session.commit()
            
            # Update store status to completed
            store.status = 'completed'
            db.session.commit()
            
            # Update task to completed
            if task:
                task.status = 'completed'
                task.progress = 100
                db.session.commit()
            
            return {
                'status': 'completed',
                'details': {
                    'theme': theme_result,
                    'pages': pages_result,
                    'settings': settings_result
                }
            }
            
        except Exception as e:
            logger.error(f"Error in store setup: {str(e)}")
            store.status = 'failed'
            db.session.commit()
            
            if task:
                task.status = 'failed'
                task.error_message = str(e)
                db.session.commit()
            
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _setup_theme(self, store_id):
        """
        Install and configure a theme for the store.
        
        Args:
            store_id (int): StoreSetup ID
            
        Returns:
            dict: Theme setup results
        """
        store = StoreSetup.query.get(store_id)
        
        # Check if theme customization already exists
        existing_customization = ThemeCustomization.query.filter_by(store_id=store_id).first()
        
        if existing_customization:
            # Theme already set up, return info
            return {
                'theme_id': existing_customization.theme_id,
                'status': 'already_exists'
            }
        
        # In a real implementation, this would:
        # 1. Install the theme in Shopify
        # 2. Configure theme settings via API
        
        # For now, simulate theme installation
        theme_id = 'theme_123456789'  # This would be the actual theme ID from Shopify
        
        # Create theme customization record
        settings_json = json.loads(store.settings_json) if store.settings_json else {}
        theme_settings = settings_json.get('theme', {})
        
        customization = ThemeCustomization(
            store_id=store_id,
            theme_id=theme_id,
            primary_color=theme_settings.get('primary_color', '#000000'),
            secondary_color=theme_settings.get('secondary_color', '#ffffff'),
            font_heading=theme_settings.get('font_heading', 'Helvetica'),
            font_body=theme_settings.get('font_body', 'Arial'),
            logo_position=theme_settings.get('logo_position', 'center'),
            hero_layout=theme_settings.get('hero_layout', 'default'),
            home_page_sections=json.dumps(theme_settings.get('home_page_sections', ['hero', 'featured_products', 'collection_list'])),
            collection_layout=theme_settings.get('collection_layout', 'grid'),
            product_page_layout=theme_settings.get('product_page_layout', 'standard'),
            settings_json=json.dumps(theme_settings)
        )
        db.session.add(customization)
        
        # Update store record with theme ID
        store.theme_id = theme_id
        db.session.commit()
        
        return {
            'theme_id': theme_id,
            'status': 'created'
        }
    
    def _create_essential_pages(self, store_id):
        """
        Create essential pages for the store.
        
        Args:
            store_id (int): StoreSetup ID
            
        Returns:
            dict: Page creation results
        """
        store = StoreSetup.query.get(store_id)
        
        # Essential page types to create
        essential_pages = ['about', 'contact', 'faq', 'terms', 'privacy']
        
        results = {}
        for page_type in essential_pages:
            # Check if page already exists
            existing_page = StorePage.query.filter_by(store_id=store_id, page_type=page_type).first()
            
            if existing_page:
                results[page_type] = {
                    'page_id': existing_page.id,
                    'status': 'already_exists'
                }
                continue
            
            # Generate content (in a real implementation, this would use the AI service)
            title, content = self._generate_page_content(store, page_type)
            
            # Create the page in database
            page = StorePage(
                store_id=store_id,
                page_type=page_type,
                title=title,
                content=content,
                meta_title=f"{title} - {store.store_name}",
                meta_description=f"{store.store_name} {page_type} page.",
                is_published=False  # Not published to Shopify yet
            )
            db.session.add(page)
            db.session.commit()
            
            results[page_type] = {
                'page_id': page.id,
                'status': 'created'
            }
        
        return results
    
    def _generate_page_content(self, store, page_type):
        """
        Generate content for a store page.
        
        Args:
            store (StoreSetup): The store record
            page_type (str): Type of page to generate
            
        Returns:
            tuple: (title, content)
        """
        # In a real implementation, this would use the AI service to generate content
        # For now, use placeholders
        
        store_name = store.store_name
        niche = store.niche or "online store"
        
        if page_type == 'about':
            title = f"About {store_name}"
            content = f"""
            <h1>About {store_name}</h1>
            <p>{store_name} is a premier {niche} dedicated to providing high-quality products and exceptional customer service.</p>
            <p>Founded with a passion for {niche}, we strive to offer innovative and practical solutions for our customers.</p>
            <p>Our mission is to deliver premium products that enhance your experience and lifestyle.</p>
            """
            
        elif page_type == 'contact':
            title = "Contact Us"
            content = f"""
            <h1>Contact {store_name}</h1>
            <p>We're here to help! Get in touch with our team for any questions, concerns, or feedback.</p>
            <p>Email: contact@example.com</p>
            <p>Phone: (555) 123-4567</p>
            <p>Hours: Monday-Friday, 9am-5pm</p>
            <form>
                <label for="name">Name:</label>
                <input type="text" id="name" name="name" required>
                
                <label for="email">Email:</label>
                <input type="email" id="email" name="email" required>
                
                <label for="message">Message:</label>
                <textarea id="message" name="message" required></textarea>
                
                <button type="submit">Send Message</button>
            </form>
            """
            
        elif page_type == 'faq':
            title = "Frequently Asked Questions"
            content = f"""
            <h1>Frequently Asked Questions</h1>
            <h2>Shipping & Delivery</h2>
            <p><strong>Q: How long does shipping take?</strong></p>
            <p>A: Standard shipping typically takes 5-7 business days. Express shipping options are available at checkout.</p>
            
            <p><strong>Q: Do you ship internationally?</strong></p>
            <p>A: Yes, we ship to most countries worldwide. Shipping costs and delivery times vary by location.</p>
            
            <h2>Returns & Exchanges</h2>
            <p><strong>Q: What is your return policy?</strong></p>
            <p>A: We offer a 30-day return policy for most items. Products must be in original condition with tags attached.</p>
            
            <p><strong>Q: How do I initiate a return?</strong></p>
            <p>A: Contact our customer service team to obtain a return authorization and shipping instructions.</p>
            """
            
        elif page_type == 'terms':
            title = "Terms & Conditions"
            content = f"""
            <h1>Terms & Conditions</h1>
            <p>Last updated: {datetime.now().strftime('%B %d, %Y')}</p>
            
            <h2>1. Introduction</h2>
            <p>Welcome to {store_name}. By accessing our website and making purchases, you agree to these Terms & Conditions.</p>
            
            <h2>2. Intellectual Property</h2>
            <p>All content on this site, including images, text, and logos, is the property of {store_name} and protected by copyright laws.</p>
            
            <h2>3. User Accounts</h2>
            <p>When creating an account, you must provide accurate information. You are responsible for maintaining the confidentiality of your account.</p>
            
            <h2>4. Product Information</h2>
            <p>We strive to display products accurately, but cannot guarantee all details are 100% accurate. We reserve the right to modify product information.</p>
            
            <h2>5. Pricing and Payment</h2>
            <p>All prices are subject to change without notice. We reserve the right to refuse any order placed with us.</p>
            """
            
        elif page_type == 'privacy':
            title = "Privacy Policy"
            content = f"""
            <h1>Privacy Policy</h1>
            <p>Last updated: {datetime.now().strftime('%B %d, %Y')}</p>
            
            <h2>1. Information We Collect</h2>
            <p>We collect personal information that you provide directly, such as name, email, shipping address, and payment details.</p>
            
            <h2>2. How We Use Your Information</h2>
            <p>We use your information to process orders, provide customer service, and improve our website and products.</p>
            
            <h2>3. Information Sharing</h2>
            <p>We do not sell or rent your personal information. We may share information with service providers who help us operate our business.</p>
            
            <h2>4. Cookies</h2>
            <p>We use cookies to enhance your browsing experience, analyze site traffic, and personalize content.</p>
            
            <h2>5. Data Security</h2>
            <p>We implement appropriate security measures to protect your personal information from unauthorized access or disclosure.</p>
            """
            
        else:
            title = f"{page_type.title()} Page"
            content = f"<h1>{title}</h1><p>Content for {store_name} {page_type} page.</p>"
        
        return title, content
    
    def _configure_store_settings(self, store_id):
        """
        Configure general store settings.
        
        Args:
            store_id (int): StoreSetup ID
            
        Returns:
            dict: Configuration results
        """
        store = StoreSetup.query.get(store_id)
        
        # In a real implementation, this would:
        # 1. Configure store settings via Shopify API
        # 2. Set up shipping, taxes, payment methods, etc.
        
        # For now, just mark settings as configured
        settings_json = json.loads(store.settings_json) if store.settings_json else {}
        
        # Update settings in the database
        store.settings_json = json.dumps(settings_json)
        db.session.commit()
        
        return {
            'status': 'configured',
            'settings': settings_json
        }
    
    def add_products(self, store_id, product_sources=None, product_ids=None, task_id=None):
        """
        Add products to the store.
        
        Args:
            store_id (int): StoreSetup ID
            product_sources (list): List of product source data (dicts)
            product_ids (list): IDs of ProductSource objects to add
            task_id (int): Optional AgentTask ID for tracking progress
            
        Returns:
            dict: Task information
        """
        # Create a new task if one doesn't exist
        if not task_id:
            task = AgentTask(
                task_type='add_products',
                status='running',
                progress=0,
                parameters=json.dumps({
                    'store_id': store_id,
                    'product_sources': product_sources,
                    'product_ids': product_ids
                })
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
            
        # Update existing task if provided
        else:
            task = AgentTask.query.get(task_id)
            if not task:
                raise ValueError(f"Task with ID {task_id} not found")
            task.status = 'running'
            task.progress = 0
            db.session.commit()
            
        try:
            # Process product IDs if provided
            if product_ids:
                products = ProductSource.query.filter(ProductSource.id.in_(product_ids)).all()
                product_data = []
                for p in products:
                    product_data.append({
                        'id': p.id,
                        'name': p.name,
                        'description': p.description,
                        'price': p.price,
                        'images': json.loads(p.image_urls) if p.image_urls else []
                    })
                    
                product_sources = product_data
            
            # Process the products
            results = self._add_products_to_store(store_id, product_sources, task_id)
            
            # Update task with results
            task = AgentTask.query.get(task_id)
            task.status = 'completed'
            task.progress = 100
            task.result_type = 'store_products'
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'completed',
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error adding products: {str(e)}")
            task = AgentTask.query.get(task_id)
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _add_products_to_store(self, store_id, product_data, task_id=None):
        """
        Add products to the store database and Shopify.
        
        Args:
            store_id (int): StoreSetup ID
            product_data (list): List of product data dictionaries
            task_id (int): AgentTask ID for updating progress
            
        Returns:
            list: Processing results for each product
        """
        results = []
        
        # Check and get the store
        store = StoreSetup.query.get(store_id)
        if not store:
            raise ValueError(f"Store with ID {store_id} not found")
        
        # Process each product
        for i, product in enumerate(product_data):
            # Update task progress
            if task_id:
                progress = int((i / len(product_data)) * 100)
                task = AgentTask.query.get(task_id)
                task.progress = progress
                db.session.commit()
            
            try:
                # Extract product data
                name = product.get('name')
                description = product.get('description', '')
                price = product.get('price', 0)
                images = product.get('images', [])
                source_id = product.get('id')
                
                # Generate SEO-friendly data
                seo_title = name
                seo_description = description[:160] if description else name  # Limit to 160 chars
                
                # Create a product in the database
                store_product = StoreProduct(
                    store_id=store_id,
                    product_source_id=source_id,
                    title=name,
                    description=description,
                    price=price,
                    images=json.dumps(images),
                    seo_title=seo_title,
                    seo_description=seo_description,
                    status='draft'
                )
                db.session.add(store_product)
                db.session.commit()
                
                # In a real implementation, this would also create the product in Shopify
                # and update the shopify_product_id in the database
                
                results.append({
                    'product_id': store_product.id,
                    'status': 'created',
                    'name': name
                })
                
            except Exception as e:
                logger.error(f"Error processing product {product.get('name')}: {str(e)}")
                results.append({
                    'name': product.get('name'),
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
    
    def publish_products(self, store_id, product_ids=None, task_id=None):
        """
        Publish products to Shopify.
        
        Args:
            store_id (int): StoreSetup ID
            product_ids (list): IDs of StoreProduct objects to publish, or None for all
            task_id (int): Optional AgentTask ID for tracking progress
            
        Returns:
            dict: Task information
        """
        # Create a new task if one doesn't exist
        if not task_id:
            task = AgentTask(
                task_type='publish_products',
                status='running',
                progress=0,
                parameters=json.dumps({
                    'store_id': store_id,
                    'product_ids': product_ids
                })
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
            
        # Update existing task if provided
        else:
            task = AgentTask.query.get(task_id)
            if not task:
                raise ValueError(f"Task with ID {task_id} not found")
            task.status = 'running'
            task.progress = 0
            db.session.commit()
            
        try:
            # Get the products to publish
            query = StoreProduct.query.filter_by(store_id=store_id, status='draft')
            if product_ids:
                query = query.filter(StoreProduct.id.in_(product_ids))
            
            products = query.all()
            
            # No products to publish
            if not products:
                task.status = 'completed'
                task.progress = 100
                task.result_type = 'store_products'
                db.session.commit()
                
                return {
                    'task_id': task_id,
                    'status': 'completed',
                    'message': 'No draft products to publish',
                    'products_published': 0
                }
            
            # Process the products
            results = self._publish_products_to_shopify(store_id, products, task_id)
            
            # Update task with results
            task = AgentTask.query.get(task_id)
            task.status = 'completed'
            task.progress = 100
            task.result_type = 'store_products'
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'completed',
                'products_published': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error publishing products: {str(e)}")
            task = AgentTask.query.get(task_id)
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _publish_products_to_shopify(self, store_id, products, task_id=None):
        """
        Publish products to Shopify.
        
        Args:
            store_id (int): StoreSetup ID
            products (list): List of StoreProduct objects to publish
            task_id (int): AgentTask ID for updating progress
            
        Returns:
            list: Publishing results for each product
        """
        results = []
        
        # Check and get the store
        store = StoreSetup.query.get(store_id)
        if not store:
            raise ValueError(f"Store with ID {store_id} not found")
        
        # Process each product
        for i, product in enumerate(products):
            # Update task progress
            if task_id:
                progress = int((i / len(products)) * 100)
                task = AgentTask.query.get(task_id)
                task.progress = progress
                db.session.commit()
            
            try:
                # In a real implementation, this would call the Shopify API to create/update the product
                # For now, simulate a successful publish
                
                # Generate a fake Shopify product ID
                shopify_product_id = f"shopify_{product.id}_{store_id}"
                
                # Update the product in the database
                product.shopify_product_id = shopify_product_id
                product.status = 'active'
                db.session.commit()
                
                results.append({
                    'product_id': product.id,
                    'shopify_product_id': shopify_product_id,
                    'status': 'published',
                    'name': product.title
                })
                
            except Exception as e:
                logger.error(f"Error publishing product {product.title}: {str(e)}")
                results.append({
                    'product_id': product.id,
                    'name': product.title,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
    
    def publish_pages(self, store_id, page_ids=None, task_id=None):
        """
        Publish pages to Shopify.
        
        Args:
            store_id (int): StoreSetup ID
            page_ids (list): IDs of StorePage objects to publish, or None for all
            task_id (int): Optional AgentTask ID for tracking progress
            
        Returns:
            dict: Task information
        """
        # Create a new task if one doesn't exist
        if not task_id:
            task = AgentTask(
                task_type='publish_pages',
                status='running',
                progress=0,
                parameters=json.dumps({
                    'store_id': store_id,
                    'page_ids': page_ids
                })
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
            
        # Update existing task if provided
        else:
            task = AgentTask.query.get(task_id)
            if not task:
                raise ValueError(f"Task with ID {task_id} not found")
            task.status = 'running'
            task.progress = 0
            db.session.commit()
            
        try:
            # Get the pages to publish
            query = StorePage.query.filter_by(store_id=store_id, is_published=False)
            if page_ids:
                query = query.filter(StorePage.id.in_(page_ids))
            
            pages = query.all()
            
            # No pages to publish
            if not pages:
                task.status = 'completed'
                task.progress = 100
                task.result_type = 'store_pages'
                db.session.commit()
                
                return {
                    'task_id': task_id,
                    'status': 'completed',
                    'message': 'No unpublished pages to publish',
                    'pages_published': 0
                }
            
            # Process the pages
            results = self._publish_pages_to_shopify(store_id, pages, task_id)
            
            # Update task with results
            task = AgentTask.query.get(task_id)
            task.status = 'completed'
            task.progress = 100
            task.result_type = 'store_pages'
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'completed',
                'pages_published': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error publishing pages: {str(e)}")
            task = AgentTask.query.get(task_id)
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _publish_pages_to_shopify(self, store_id, pages, task_id=None):
        """
        Publish pages to Shopify.
        
        Args:
            store_id (int): StoreSetup ID
            pages (list): List of StorePage objects to publish
            task_id (int): AgentTask ID for updating progress
            
        Returns:
            list: Publishing results for each page
        """
        results = []
        
        # Check and get the store
        store = StoreSetup.query.get(store_id)
        if not store:
            raise ValueError(f"Store with ID {store_id} not found")
        
        # Process each page
        for i, page in enumerate(pages):
            # Update task progress
            if task_id:
                progress = int((i / len(pages)) * 100)
                task = AgentTask.query.get(task_id)
                task.progress = progress
                db.session.commit()
            
            try:
                # In a real implementation, this would call the Shopify API to create/update the page
                # For now, simulate a successful publish
                
                # Generate a fake Shopify page ID
                shopify_page_id = f"shopify_page_{page.id}_{store_id}"
                
                # Update the page in the database
                page.shopify_page_id = shopify_page_id
                page.is_published = True
                db.session.commit()
                
                results.append({
                    'page_id': page.id,
                    'shopify_page_id': shopify_page_id,
                    'status': 'published',
                    'title': page.title
                })
                
            except Exception as e:
                logger.error(f"Error publishing page {page.title}: {str(e)}")
                results.append({
                    'page_id': page.id,
                    'title': page.title,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
    
    def customize_theme(self, store_id, theme_settings, task_id=None):
        """
        Customize the store's theme.
        
        Args:
            store_id (int): StoreSetup ID
            theme_settings (dict): Theme customization settings
            task_id (int): Optional AgentTask ID for tracking progress
            
        Returns:
            dict: Task information
        """
        # Create a new task if one doesn't exist
        if not task_id:
            task = AgentTask(
                task_type='customize_theme',
                status='running',
                progress=0,
                parameters=json.dumps({
                    'store_id': store_id,
                    'theme_settings': theme_settings
                })
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
            
        # Update existing task if provided
        else:
            task = AgentTask.query.get(task_id)
            if not task:
                raise ValueError(f"Task with ID {task_id} not found")
            task.status = 'running'
            task.progress = 0
            db.session.commit()
            
        try:
            # Get the theme customization
            customization = ThemeCustomization.query.filter_by(store_id=store_id).first()
            
            if not customization:
                # Theme not set up yet, do it now
                self._setup_theme(store_id)
                customization = ThemeCustomization.query.filter_by(store_id=store_id).first()
                
                if not customization:
                    raise ValueError("Failed to set up theme")
            
            # Update the theme customization with new settings
            for key, value in theme_settings.items():
                if hasattr(customization, key) and key != 'store_id' and key != 'theme_id':
                    if key == 'home_page_sections' and isinstance(value, list):
                        setattr(customization, key, json.dumps(value))
                    else:
                        setattr(customization, key, value)
            
            # Update the settings_json field with the full settings
            current_settings = json.loads(customization.settings_json) if customization.settings_json else {}
            current_settings.update(theme_settings)
            customization.settings_json = json.dumps(current_settings)
            
            db.session.commit()
            
            # In a real implementation, this would also update the theme in Shopify
            # via the Theme API
            
            # Update task status
            task.status = 'completed'
            task.progress = 100
            task.result_type = 'theme_customization'
            task.result_id = customization.id
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'completed',
                'theme_id': customization.theme_id,
                'updated_fields': list(theme_settings.keys())
            }
            
        except Exception as e:
            logger.error(f"Error customizing theme: {str(e)}")
            task = AgentTask.query.get(task_id)
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }
            
    def create_store_from_dropshipping_results(self, niche_id=None, product_ids=None, user_id=None, settings_id=None, store_name=None, task_id=None):
        """
        Create a complete store based on dropshipping agent results.
        
        This is a comprehensive method that:
        1. Creates a store setup
        2. Adds products from dropshipping results
        3. Customizes theme based on niche
        4. Creates and publishes all pages
        5. Publishes all products
        
        Args:
            niche_id (int): NicheAnalysis ID to use for store theme/content
            product_ids (list): IDs of ProductSource objects to add
            user_id (int): User ID associated with the store
            settings_id (int): ShopifySettings ID to use for API calls
            store_name (str): Name for the store (optional)
            task_id (int): Optional AgentTask ID for tracking progress
            
        Returns:
            dict: Task information
        """
        # Create a new task if one doesn't exist
        if not task_id:
            task = AgentTask(
                user_id=user_id,
                task_type='create_full_store',
                status='running',
                progress=0,
                parameters=json.dumps({
                    'niche_id': niche_id,
                    'product_ids': product_ids,
                    'store_name': store_name
                })
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
            
        # Update existing task if provided
        else:
            task = AgentTask.query.get(task_id)
            if not task:
                raise ValueError(f"Task with ID {task_id} not found")
            task.status = 'running'
            task.progress = 0
            db.session.commit()
            
        try:
            # Get niche information if provided
            niche_name = None
            niche_description = None
            niche_keywords = []
            if niche_id:
                from models import NicheAnalysis
                niche = NicheAnalysis.query.get(niche_id)
                if niche:
                    niche_name = niche.name
                    niche_description = niche.description
                    if niche.main_keywords:
                        try:
                            niche_keywords = json.loads(niche.main_keywords)
                        except:
                            pass
            
            # If no store name provided, generate one from niche
            if not store_name and niche_name:
                store_name = f"{niche_name} Store"
            elif not store_name:
                store_name = "My Dropshipping Store"
            
            # 1. Create the store setup (20% of progress)
            store_url = f"https://{store_name.lower().replace(' ', '-')}.myshopify.com"
            store_params = {
                'store_name': store_name,
                'store_url': store_url,
                'niche': niche_name,
                'currency': 'USD',
                'settings': {
                    'niche_description': niche_description,
                    'keywords': niche_keywords
                }
            }
            
            # Create the store
            store_result = self.create_store(store_params, user_id, settings_id)
            store_id = store_result.get('store_id')
            
            if not store_id:
                raise ValueError("Failed to create store")
            
            # Update task progress
            task.progress = 20
            db.session.commit()
            
            # 2. Add products from dropshipping results (40% of progress)
            if product_ids:
                product_result = self.add_products(store_id, product_ids=product_ids)
                
                # Update task progress
                task.progress = 40
                db.session.commit()
                
                # 3. Publish all products (60% of progress)
                publish_result = self.publish_products(store_id)
                
                # Update task progress
                task.progress = 60
                db.session.commit()
            
            # 4. Customize theme based on niche (80% of progress)
            theme_settings = self._generate_theme_settings_for_niche(niche_name, niche_keywords)
            theme_result = self.customize_theme(store_id, theme_settings)
            
            # Update task progress
            task.progress = 80
            db.session.commit()
            
            # 5. Publish all pages (100% of progress)
            pages_result = self.publish_pages(store_id)
            
            # Update task to completed
            task.status = 'completed'
            task.progress = 100
            task.result_type = 'store_setup'
            task.result_id = store_id
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'completed',
                'store_id': store_id,
                'store_name': store_name,
                'store_url': store_url
            }
            
        except Exception as e:
            logger.error(f"Error creating full store: {str(e)}")
            task = AgentTask.query.get(task_id)
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _generate_theme_settings_for_niche(self, niche_name, niche_keywords):
        """
        Generate theme settings based on niche.
        
        Args:
            niche_name (str): Name of the niche
            niche_keywords (list): Keywords associated with the niche
            
        Returns:
            dict: Theme settings
        """
        # In a real implementation, this would intelligently select colors, fonts, etc.
        # based on the niche. For now, use some simple rules.
        
        settings = {
            'primary_color': '#4A90E2',  # Default blue
            'secondary_color': '#F5F5F5',  # Light gray
            'font_heading': 'Montserrat',
            'font_body': 'Open Sans',
            'logo_position': 'center',
            'hero_layout': 'fullwidth',
            'home_page_sections': ['hero', 'featured_collection', 'image_text', 'testimonials'],
            'collection_layout': 'grid',
            'product_page_layout': 'standard'
        }
        
        # Adjust settings based on niche keywords
        if niche_name:
            niche_lower = niche_name.lower()
            
            # Tech/gadgets themes tend to be more modern
            if any(word in niche_lower for word in ['tech', 'gadget', 'electronic']):
                settings['primary_color'] = '#000000'  # Black
                settings['secondary_color'] = '#F8F8F8'  # Very light gray
                settings['font_heading'] = 'Roboto'
                settings['font_body'] = 'Roboto'
                settings['hero_layout'] = 'split'
                
            # Beauty/fashion themes are often more elegant
            elif any(word in niche_lower for word in ['beauty', 'fashion', 'cosmetic']):
                settings['primary_color'] = '#FF6B6B'  # Coral pink
                settings['secondary_color'] = '#FFF9F9'  # Very light pink
                settings['font_heading'] = 'Playfair Display'
                settings['font_body'] = 'Lato'
                
            # Home/kitchen themes are often warm and inviting
            elif any(word in niche_lower for word in ['home', 'kitchen', 'decor']):
                settings['primary_color'] = '#5D4037'  # Brown
                settings['secondary_color'] = '#EFEBE9'  # Light brown/beige
                settings['font_heading'] = 'Merriweather'
                settings['font_body'] = 'Source Sans Pro'
                
            # Fitness/sports themes are often energetic
            elif any(word in niche_lower for word in ['fitness', 'sport', 'gym']):
                settings['primary_color'] = '#00C853'  # Green
                settings['secondary_color'] = '#E8F5E9'  # Light green
                settings['font_heading'] = 'Exo 2'
                settings['font_body'] = 'Roboto'
                
            # Eco-friendly themes often use earth tones
            elif any(word in niche_lower for word in ['eco', 'green', 'sustainable']):
                settings['primary_color'] = '#388E3C'  # Forest green
                settings['secondary_color'] = '#E8F5E9'  # Light green
                settings['font_heading'] = 'Amatic SC'
                settings['font_body'] = 'Quicksand'
        
        return settings