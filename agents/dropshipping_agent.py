import json
import logging
import os
import requests
from datetime import datetime
from urllib.parse import urlparse

from models import db, TrendAnalysis, ProductSource, ProductEvaluation, NicheAnalysis, AgentTask
from web_scraper import get_website_text_content

logger = logging.getLogger(__name__)

class DropshippingAgent:
    """
    Agent for analyzing trends, finding products, and evaluating them for dropshipping.
    
    This agent helps identify profitable dropshipping opportunities through trend analysis,
    product sourcing, and automated evaluation of dropshipping viability.
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the Dropshipping Agent with the necessary API credentials.
        
        Args:
            api_key (str, optional): API key for AI services. If None, will use environment variable.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("XAI_API_KEY")
        if not self.api_key:
            logger.warning("No API key provided. Some functionality may be limited.")
            
    def start_trend_analysis(self, sources=None, keywords=None, task_id=None):
        """
        Start a trend analysis task.
        
        Args:
            sources (list): List of sources to analyze ('aliexpress', 'amazon', 'tiktok', etc.)
            keywords (list): Initial keywords to search for
            task_id (int): Optional AgentTask ID for tracking progress
            
        Returns:
            dict: Task information including task_id
        """
        # Use default sources if none provided
        if not sources:
            sources = ['aliexpress', 'amazon', 'tiktok']
            
        # Create a new task if one doesn't exist
        if not task_id:
            task = AgentTask(
                task_type='trend_analysis',
                status='running',
                progress=0,
                parameters=json.dumps({
                    'sources': sources,
                    'keywords': keywords
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
            
        # Perform the actual trend analysis asynchronously (in a real app, this would be a background task)
        # For now, we'll just do it synchronously
        try:
            results = self._analyze_trends(sources, keywords, task_id)
            
            # Update task with results
            task = AgentTask.query.get(task_id)
            task.status = 'completed'
            task.progress = 100
            task.result_type = 'trend_analysis'
            # Store the first trend analysis ID as the result ID
            if results and len(results) > 0:
                task.result_id = results[0].id
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'completed',
                'results': [{'id': r.id, 'keyword': r.keyword, 'source': r.source} for r in results]
            }
            
        except Exception as e:
            logger.error(f"Error in trend analysis: {str(e)}")
            task = AgentTask.query.get(task_id)
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _analyze_trends(self, sources, keywords, task_id=None):
        """
        Analyze trends from various sources.
        
        This internal method does the actual work of analyzing trends from specified sources.
        In a real implementation, this would use various APIs and methods to gather trend data.
        For now, it's a simplified implementation.
        
        Args:
            sources (list): List of sources to analyze
            keywords (list): Initial keywords to search for
            task_id (int): AgentTask ID for updating progress
            
        Returns:
            list: List of created TrendAnalysis objects
        """
        results = []
        
        # For each source, analyze trends
        for i, source in enumerate(sources):
            # Update task progress
            if task_id:
                progress = int((i / len(sources)) * 50)  # First half of the progress
                task = AgentTask.query.get(task_id)
                task.progress = progress
                db.session.commit()
            
            # In a real implementation, this would call source-specific APIs and methods
            # For now, we'll simulate trend data for demonstration
            if source == 'aliexpress':
                trending_keywords = keywords or ['wireless earbuds', 'phone accessories', 'home decor']
                for keyword in trending_keywords:
                    trend = TrendAnalysis(
                        source=source,
                        keyword=keyword,
                        search_volume=self._simulate_search_volume(),
                        growth_rate=self._simulate_growth_rate(),
                        competition_level=self._simulate_competition_level(),
                        seasonality=self._get_seasonality(keyword),
                        data_json=json.dumps({
                            'popularity_score': self._simulate_popularity_score(),
                            'price_range': self._simulate_price_range()
                        })
                    )
                    db.session.add(trend)
                    results.append(trend)
            
            elif source == 'amazon':
                trending_keywords = keywords or ['smart gadgets', 'kitchen tools', 'fitness equipment']
                for keyword in trending_keywords:
                    trend = TrendAnalysis(
                        source=source,
                        keyword=keyword,
                        search_volume=self._simulate_search_volume(),
                        growth_rate=self._simulate_growth_rate(),
                        competition_level=self._simulate_competition_level(),
                        seasonality=self._get_seasonality(keyword),
                        data_json=json.dumps({
                            'bestseller_rank': self._simulate_bestseller_rank(),
                            'review_count': self._simulate_review_count()
                        })
                    )
                    db.session.add(trend)
                    results.append(trend)
            
            elif source == 'tiktok':
                trending_keywords = keywords or ['viral products', 'beauty tools', 'eco friendly']
                for keyword in trending_keywords:
                    trend = TrendAnalysis(
                        source=source,
                        keyword=keyword,
                        search_volume=self._simulate_search_volume(),
                        growth_rate=self._simulate_growth_rate(),
                        competition_level=self._simulate_competition_level(),
                        seasonality=self._get_seasonality(keyword),
                        data_json=json.dumps({
                            'video_count': self._simulate_video_count(),
                            'hashtag_views': self._simulate_hashtag_views()
                        })
                    )
                    db.session.add(trend)
                    results.append(trend)
        
        # Commit all trend analyses to the database
        db.session.commit()
        
        # Update task progress
        if task_id:
            task = AgentTask.query.get(task_id)
            task.progress = 50  # Halfway done
            db.session.commit()
        
        return results
    
    def source_products(self, trend_ids=None, urls=None, task_id=None):
        """
        Source products based on trend analysis or direct URLs.
        
        Args:
            trend_ids (list): IDs of TrendAnalysis objects to source products for
            urls (list): Direct product URLs to source
            task_id (int): Optional AgentTask ID for tracking progress
            
        Returns:
            dict: Task information including task_id
        """
        # Create a new task if one doesn't exist
        if not task_id:
            task = AgentTask(
                task_type='product_sourcing',
                status='running',
                progress=0,
                parameters=json.dumps({
                    'trend_ids': trend_ids,
                    'urls': urls
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
            
        # Perform the product sourcing (in a real app, this would be a background task)
        try:
            results = []
            
            # Source products from trends
            if trend_ids:
                trend_products = self._source_from_trends(trend_ids, task_id)
                results.extend(trend_products)
                
            # Source products from direct URLs
            if urls:
                url_products = self._source_from_urls(urls, task_id)
                results.extend(url_products)
                
            # Update task with results
            task = AgentTask.query.get(task_id)
            task.status = 'completed'
            task.progress = 100
            task.result_type = 'product_source'
            # Store the first product ID as the result ID
            if results and len(results) > 0:
                task.result_id = results[0].id
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'completed',
                'results': [{'id': r.id, 'name': r.name, 'platform': r.source_platform} for r in results]
            }
            
        except Exception as e:
            logger.error(f"Error in product sourcing: {str(e)}")
            task = AgentTask.query.get(task_id)
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _source_from_trends(self, trend_ids, task_id=None):
        """
        Source products based on trend analysis.
        
        Args:
            trend_ids (list): IDs of TrendAnalysis objects to source products for
            task_id (int): AgentTask ID for updating progress
            
        Returns:
            list: List of created ProductSource objects
        """
        results = []
        
        # Get the trend analysis objects
        trends = TrendAnalysis.query.filter(TrendAnalysis.id.in_(trend_ids)).all()
        
        # For each trend, source products
        for i, trend in enumerate(trends):
            # Update task progress
            if task_id:
                progress = 50 + int((i / len(trends)) * 25)  # Second quarter of progress
                task = AgentTask.query.get(task_id)
                task.progress = progress
                db.session.commit()
            
            # In a real implementation, this would search for products based on the trend
            # For now, we'll simulate finding 2-3 products per trend
            num_products = self._simulate_product_count(2, 3)
            for j in range(num_products):
                product = ProductSource(
                    trend_id=trend.id,
                    name=f"{trend.keyword} {j+1}",
                    description=f"A great {trend.keyword} product with multiple features.",
                    source_url=f"https://example.com/{trend.source}/{trend.keyword.replace(' ', '-')}-{j+1}",
                    source_platform=trend.source,
                    price=self._simulate_price(),
                    shipping_cost=self._simulate_shipping_cost(),
                    shipping_time=self._simulate_shipping_time(),
                    moq=self._simulate_moq(),
                    rating=self._simulate_rating(),
                    weight=self._simulate_weight(),
                    dimensions=f"{self._simulate_dimension()}x{self._simulate_dimension()}x{self._simulate_dimension()}",
                    image_urls=json.dumps([
                        f"https://example.com/images/{trend.keyword.replace(' ', '-')}-{j+1}-1.jpg",
                        f"https://example.com/images/{trend.keyword.replace(' ', '-')}-{j+1}-2.jpg"
                    ]),
                    is_trending=True,
                    is_seasonal=trend.seasonality != 'all-year'
                )
                db.session.add(product)
                results.append(product)
        
        # Commit all products to the database
        db.session.commit()
        
        return results
    
    def _source_from_urls(self, urls, task_id=None):
        """
        Source products directly from URLs.
        
        In a real implementation, this would scrape the product pages and extract details.
        For now, it's a simplified implementation that simulates product data.
        
        Args:
            urls (list): Direct product URLs to source
            task_id (int): AgentTask ID for updating progress
            
        Returns:
            list: List of created ProductSource objects
        """
        results = []
        
        # For each URL, source the product
        for i, url in enumerate(urls):
            # Update task progress
            if task_id:
                progress = 75 + int((i / len(urls)) * 25)  # Last quarter of progress
                task = AgentTask.query.get(task_id)
                task.progress = progress
                db.session.commit()
            
            # Parse the URL to get domain and path
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            path = parsed_url.path
            
            # In a real implementation, this would use web scraping to get product details
            # For demonstration, we'll create simulated data based on the URL
            if 'aliexpress' in domain:
                platform = 'aliexpress'
            elif 'amazon' in domain:
                platform = 'amazon'
            elif 'alibaba' in domain:
                platform = 'alibaba'
            else:
                platform = 'other'
                
            # Extract a product name from the path
            name_parts = path.strip('/').split('/')[-1].replace('-', ' ').split('_')
            name = ' '.join([p.capitalize() for p in name_parts if p.strip()])
            if not name:
                name = f"Product from {platform.capitalize()}"
            
            product = ProductSource(
                name=name,
                description=f"This {name} is a quality product from {platform}.",
                source_url=url,
                source_platform=platform,
                price=self._simulate_price(),
                shipping_cost=self._simulate_shipping_cost(),
                shipping_time=self._simulate_shipping_time(),
                moq=self._simulate_moq(),
                rating=self._simulate_rating(),
                weight=self._simulate_weight(),
                dimensions=f"{self._simulate_dimension()}x{self._simulate_dimension()}x{self._simulate_dimension()}",
                image_urls=json.dumps([
                    f"https://example.com/images/{platform}/{name.lower().replace(' ', '-')}-1.jpg",
                    f"https://example.com/images/{platform}/{name.lower().replace(' ', '-')}-2.jpg"
                ])
            )
            db.session.add(product)
            results.append(product)
        
        # Commit all products to the database
        db.session.commit()
        
        return results
    
    def evaluate_products(self, product_ids, task_id=None):
        """
        Evaluate products for dropshipping suitability.
        
        Args:
            product_ids (list): IDs of ProductSource objects to evaluate
            task_id (int): Optional AgentTask ID for tracking progress
            
        Returns:
            dict: Task information including task_id
        """
        # Create a new task if one doesn't exist
        if not task_id:
            task = AgentTask(
                task_type='product_evaluation',
                status='running',
                progress=0,
                parameters=json.dumps({
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
            
        # Perform the product evaluation (in a real app, this would be a background task)
        try:
            results = self._evaluate_products(product_ids, task_id)
            
            # Update task with results
            task = AgentTask.query.get(task_id)
            task.status = 'completed'
            task.progress = 100
            task.result_type = 'product_evaluation'
            # Store the first evaluation ID as the result ID
            if results and len(results) > 0:
                task.result_id = results[0].id
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'completed',
                'results': [{'id': r.id, 'product_id': r.product_id, 'score': r.dropshipping_score} for r in results]
            }
            
        except Exception as e:
            logger.error(f"Error in product evaluation: {str(e)}")
            task = AgentTask.query.get(task_id)
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _evaluate_products(self, product_ids, task_id=None):
        """
        Evaluate products for dropshipping suitability.
        
        This internal method performs the actual evaluation based on product attributes.
        In a real implementation, this would use a more sophisticated algorithm.
        
        Args:
            product_ids (list): IDs of ProductSource objects to evaluate
            task_id (int): AgentTask ID for updating progress
            
        Returns:
            list: List of created ProductEvaluation objects
        """
        results = []
        
        # Get the product source objects
        products = ProductSource.query.filter(ProductSource.id.in_(product_ids)).all()
        
        # For each product, evaluate suitability
        for i, product in enumerate(products):
            # Update task progress
            if task_id:
                progress = int((i / len(products)) * 100)
                task = AgentTask.query.get(task_id)
                task.progress = progress
                db.session.commit()
            
            # Calculate profit margin if not already set
            if not product.profit_margin and product.price:
                base_price = product.price
                selling_price = base_price * 2.0  # Simple markup
                if product.shipping_cost:
                    profit = selling_price - (base_price + product.shipping_cost)
                else:
                    profit = selling_price - base_price
                profit_margin = (profit / selling_price) * 100
                product.profit_margin = profit_margin
                db.session.add(product)
            
            # Calculate dropshipping score based on various factors
            market_saturation = self._simulate_market_saturation()
            shipping_complexity = self._calculate_shipping_complexity(product)
            return_risk = self._calculate_return_risk(product)
            profit_potential = self._calculate_profit_potential(product)
            
            # Calculate overall score (0-100)
            score_components = {
                'profit_potential': profit_potential * 35,  # 35% weight
                'shipping_ease': (1 - shipping_complexity) * 25,  # 25% weight
                'return_safety': (1 - return_risk) * 20,  # 20% weight
                'market_opportunity': (1 - market_saturation) * 20  # 20% weight
            }
            
            overall_score = sum(score_components.values())
            
            # Determine overall recommendation
            if overall_score >= 85:
                recommendation = 'highly_recommended'
            elif overall_score >= 70:
                recommendation = 'recommended'
            elif overall_score >= 50:
                recommendation = 'neutral'
            elif overall_score >= 30:
                recommendation = 'not_recommended'
            else:
                recommendation = 'avoid'
            
            # Create evaluation object
            evaluation = ProductEvaluation(
                product_id=product.id,
                dropshipping_score=overall_score,
                market_saturation=market_saturation,
                shipping_complexity=shipping_complexity,
                return_risk=return_risk,
                profit_potential=profit_potential,
                overall_recommendation=recommendation,
                evaluation_notes=self._generate_evaluation_notes(product, score_components, recommendation),
                data_json=json.dumps(score_components)
            )
            db.session.add(evaluation)
            results.append(evaluation)
        
        # Commit all evaluations to the database
        db.session.commit()
        
        return results
    
    def discover_niches(self, keywords=None, task_id=None):
        """
        Discover potential dropshipping niches based on keywords or trends.
        
        Args:
            keywords (list): Keywords to use for niche discovery
            task_id (int): Optional AgentTask ID for tracking progress
            
        Returns:
            dict: Task information including task_id
        """
        # Create a new task if one doesn't exist
        if not task_id:
            task = AgentTask(
                task_type='niche_discovery',
                status='running',
                progress=0,
                parameters=json.dumps({
                    'keywords': keywords
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
            
        # Perform the niche discovery (in a real app, this would be a background task)
        try:
            if not keywords:
                # If no keywords provided, use recent trend analysis
                trends = TrendAnalysis.query.order_by(TrendAnalysis.created_at.desc()).limit(10).all()
                keywords = [trend.keyword for trend in trends]
                
            results = self._discover_niches(keywords, task_id)
            
            # Update task with results
            task = AgentTask.query.get(task_id)
            task.status = 'completed'
            task.progress = 100
            task.result_type = 'niche_analysis'
            # Store the first niche ID as the result ID
            if results and len(results) > 0:
                task.result_id = results[0].id
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'completed',
                'results': [{'id': r.id, 'name': r.name, 'growth_potential': r.growth_potential} for r in results]
            }
            
        except Exception as e:
            logger.error(f"Error in niche discovery: {str(e)}")
            task = AgentTask.query.get(task_id)
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _discover_niches(self, keywords, task_id=None):
        """
        Discover potential dropshipping niches.
        
        This internal method performs the actual niche discovery.
        In a real implementation, this would use more sophisticated techniques.
        
        Args:
            keywords (list): Keywords to use for niche discovery
            task_id (int): AgentTask ID for updating progress
            
        Returns:
            list: List of created NicheAnalysis objects
        """
        results = []
        
        # Example niches based on common dropshipping categories
        example_niches = [
            {
                'name': 'Eco-friendly Kitchen Products',
                'description': 'Sustainable kitchen tools and accessories for environmentally conscious consumers.',
                'main_keywords': ['eco friendly kitchen', 'sustainable kitchenware', 'green kitchen gadgets'],
                'audience_demographics': {'age_range': [25, 45], 'gender': 'mixed', 'interests': ['sustainability', 'cooking', 'health']}
            },
            {
                'name': 'Tech Accessories for Travelers',
                'description': 'Portable and durable tech products designed for people who travel frequently.',
                'main_keywords': ['travel tech', 'portable gadgets', 'travel accessories'],
                'audience_demographics': {'age_range': [22, 40], 'gender': 'mixed', 'interests': ['travel', 'technology', 'productivity']}
            },
            {
                'name': 'Pet Grooming Tools',
                'description': 'Specialized tools and products for pet owners to groom their animals at home.',
                'main_keywords': ['pet grooming', 'dog grooming tools', 'cat grooming'],
                'audience_demographics': {'age_range': [30, 60], 'gender': 'mixed', 'interests': ['pets', 'animal care', 'home services']}
            },
            {
                'name': 'Fitness Equipment for Small Spaces',
                'description': 'Compact and effective fitness gear for people with limited home workout space.',
                'main_keywords': ['compact fitness gear', 'small space workout', 'apartment fitness'],
                'audience_demographics': {'age_range': [20, 35], 'gender': 'mixed', 'interests': ['fitness', 'home workout', 'health']}
            },
            {
                'name': 'Beauty Tools and Accessories',
                'description': 'Specialized beauty tools for skincare and makeup enthusiasts.',
                'main_keywords': ['beauty tools', 'skincare gadgets', 'makeup accessories'],
                'audience_demographics': {'age_range': [18, 40], 'gender': 'mostly female', 'interests': ['beauty', 'skincare', 'self-care']}
            }
        ]
        
        # For keyword-based niches
        for keyword in keywords:
            # Check if keyword matches any example niche
            matching_niches = []
            for niche in example_niches:
                if any(kw.lower() in keyword.lower() or keyword.lower() in kw.lower() for kw in niche['main_keywords']):
                    matching_niches.append(niche)
            
            # If matches found, use those niches
            if matching_niches:
                for i, niche in enumerate(matching_niches):
                    # Update task progress
                    if task_id:
                        progress = int((len(results) / (len(keywords) * 2)) * 100)
                        task = AgentTask.query.get(task_id)
                        task.progress = progress
                        db.session.commit()
                    
                    niche_obj = NicheAnalysis(
                        name=niche['name'],
                        description=niche['description'],
                        main_keywords=json.dumps(niche['main_keywords']),
                        search_volume=self._simulate_search_volume(),
                        competition_level=self._simulate_competition_level(),
                        growth_potential=self._simulate_growth_potential(),
                        audience_demographics=json.dumps(niche['audience_demographics']),
                        marketing_channels=json.dumps(['facebook', 'instagram', 'google ads']),
                        evaluation_notes=f"This niche matches the keyword '{keyword}' and has good potential for dropshipping."
                    )
                    db.session.add(niche_obj)
                    results.append(niche_obj)
            
            # If no matches, create a new niche based on the keyword
            else:
                # Update task progress
                if task_id:
                    progress = int((len(results) / (len(keywords) * 2)) * 100)
                    task = AgentTask.query.get(task_id)
                    task.progress = progress
                    db.session.commit()
                
                # Generate a niche name from the keyword
                niche_name = self._generate_niche_name(keyword)
                
                niche_obj = NicheAnalysis(
                    name=niche_name,
                    description=f"Products related to {keyword}, targeting consumers interested in this category.",
                    main_keywords=json.dumps([keyword, f"{keyword} products", f"best {keyword}"]),
                    search_volume=self._simulate_search_volume(),
                    competition_level=self._simulate_competition_level(),
                    growth_potential=self._simulate_growth_potential(),
                    audience_demographics=json.dumps(self._generate_audience_demographics(keyword)),
                    marketing_channels=json.dumps(['facebook', 'instagram', 'google ads']),
                    evaluation_notes=f"This niche is derived from the keyword '{keyword}' and may have potential for dropshipping."
                )
                db.session.add(niche_obj)
                results.append(niche_obj)
        
        # Commit all niches to the database
        db.session.commit()
        
        return results
    
    # Helper methods for generating simulated data
    def _simulate_search_volume(self):
        """Simulate search volume between 1,000 and 100,000"""
        import random
        return random.randint(1000, 100000)
    
    def _simulate_growth_rate(self):
        """Simulate growth rate between -10% and 50%"""
        import random
        return random.uniform(-10.0, 50.0)
    
    def _simulate_competition_level(self):
        """Simulate competition level between 0 and 1"""
        import random
        return random.uniform(0, 1)
    
    def _get_seasonality(self, keyword):
        """Determine seasonality based on keyword"""
        seasonal_keywords = {
            'summer': ['beach', 'swimwear', 'sunglasses', 'outdoor'],
            'winter': ['scarf', 'gloves', 'winter', 'heating'],
            'spring': ['garden', 'planting', 'allergies'],
            'fall': ['autumn', 'halloween', 'thanksgiving']
        }
        
        for season, keywords in seasonal_keywords.items():
            for k in keywords:
                if k in keyword.lower():
                    return season
        
        return 'all-year'
    
    def _simulate_popularity_score(self):
        """Simulate popularity score between 1 and 100"""
        import random
        return random.randint(1, 100)
    
    def _simulate_price_range(self):
        """Simulate price range as [min, max]"""
        import random
        min_price = random.uniform(5, 50)
        max_price = min_price + random.uniform(10, 100)
        return [round(min_price, 2), round(max_price, 2)]
    
    def _simulate_bestseller_rank(self):
        """Simulate Amazon bestseller rank between 1 and 100,000"""
        import random
        return random.randint(1, 100000)
    
    def _simulate_review_count(self):
        """Simulate review count between 0 and 10,000"""
        import random
        return random.randint(0, 10000)
    
    def _simulate_video_count(self):
        """Simulate TikTok video count between 10 and 10,000"""
        import random
        return random.randint(10, 10000)
    
    def _simulate_hashtag_views(self):
        """Simulate TikTok hashtag views between 1,000 and 10,000,000"""
        import random
        return random.randint(1000, 10000000)
    
    def _simulate_product_count(self, min_count=1, max_count=5):
        """Simulate number of products to create"""
        import random
        return random.randint(min_count, max_count)
    
    def _simulate_price(self):
        """Simulate product price between 5 and 200"""
        import random
        return round(random.uniform(5, 200), 2)
    
    def _simulate_shipping_cost(self):
        """Simulate shipping cost between 0 and 30"""
        import random
        return round(random.uniform(0, 30), 2)
    
    def _simulate_shipping_time(self):
        """Simulate shipping time between 3 and 45 days"""
        import random
        return random.randint(3, 45)
    
    def _simulate_moq(self):
        """Simulate minimum order quantity between 1 and 20"""
        import random
        return random.randint(1, 20)
    
    def _simulate_rating(self):
        """Simulate supplier rating between 1 and 5"""
        import random
        return round(random.uniform(1, 5), 1)
    
    def _simulate_weight(self):
        """Simulate product weight between 0.1 and 10 kg"""
        import random
        return round(random.uniform(0.1, 10), 2)
    
    def _simulate_dimension(self):
        """Simulate product dimension between 1 and 100 cm"""
        import random
        return random.randint(1, 100)
    
    def _simulate_market_saturation(self):
        """Simulate market saturation between 0 and 1"""
        import random
        return random.uniform(0, 1)
    
    def _simulate_growth_potential(self):
        """Simulate growth potential between 0 and 1"""
        import random
        return random.uniform(0, 1)
    
    def _calculate_shipping_complexity(self, product):
        """Calculate shipping complexity based on product attributes"""
        complexity = 0.5  # Base complexity
        
        # Adjust based on weight (heavier = more complex)
        if product.weight:
            if product.weight > 5:
                complexity += 0.3
            elif product.weight > 2:
                complexity += 0.1
            elif product.weight < 0.5:
                complexity -= 0.1
        
        # Adjust based on shipping time (longer = more complex)
        if product.shipping_time:
            if product.shipping_time > 30:
                complexity += 0.2
            elif product.shipping_time > 14:
                complexity += 0.1
            elif product.shipping_time < 7:
                complexity -= 0.1
        
        # Ensure result is between 0 and 1
        return max(0, min(1, complexity))
    
    def _calculate_return_risk(self, product):
        """Calculate return risk based on product attributes"""
        risk = 0.3  # Base risk
        
        # Certain platforms have higher risk
        if product.source_platform == 'aliexpress':
            risk += 0.1
        elif product.source_platform == 'amazon':
            risk -= 0.1
        
        # Higher-priced items have higher risk
        if product.price:
            if product.price > 100:
                risk += 0.2
            elif product.price > 50:
                risk += 0.1
            elif product.price < 15:
                risk -= 0.1
        
        # Ensure result is between 0 and 1
        return max(0, min(1, risk))
    
    def _calculate_profit_potential(self, product):
        """Calculate profit potential based on product attributes"""
        potential = 0.5  # Base potential
        
        # Use profit margin if available
        if product.profit_margin:
            if product.profit_margin > 70:
                potential = 0.9
            elif product.profit_margin > 50:
                potential = 0.8
            elif product.profit_margin > 30:
                potential = 0.6
            elif product.profit_margin < 15:
                potential = 0.3
        
        # Adjust based on price (medium price = better potential)
        if product.price:
            if 20 <= product.price <= 80:
                potential += 0.1
            elif product.price > 200:
                potential -= 0.1
        
        # Ensure result is between 0 and 1
        return max(0, min(1, potential))
    
    def _generate_evaluation_notes(self, product, score_components, recommendation):
        """Generate human-readable evaluation notes"""
        notes = []
        
        # Overall recommendation
        notes.append(f"Overall Recommendation: {recommendation.replace('_', ' ').title()}")
        notes.append(f"Dropshipping Score: {score_components['profit_potential'] + score_components['shipping_ease'] + score_components['return_safety'] + score_components['market_opportunity']:.1f}/100")
        
        # Profit potential
        profit_note = "High profit potential." if score_components['profit_potential'] > 25 else "Moderate profit potential." if score_components['profit_potential'] > 15 else "Low profit potential."
        notes.append(profit_note)
        
        # Shipping
        shipping_note = "Easy to ship." if score_components['shipping_ease'] > 20 else "Moderate shipping complexity." if score_components['shipping_ease'] > 10 else "Complex shipping requirements."
        notes.append(shipping_note)
        
        # Return risk
        return_note = "Low return risk." if score_components['return_safety'] > 15 else "Moderate return risk." if score_components['return_safety'] > 10 else "High return risk."
        notes.append(return_note)
        
        # Market opportunity
        market_note = "Excellent market opportunity." if score_components['market_opportunity'] > 15 else "Decent market opportunity." if score_components['market_opportunity'] > 10 else "Saturated market."
        notes.append(market_note)
        
        # Add platform-specific notes
        if product.source_platform == 'aliexpress':
            notes.append("Sourced from AliExpress, which typically offers good margins but longer shipping times.")
        elif product.source_platform == 'amazon':
            notes.append("Sourced from Amazon, which typically offers faster shipping but lower margins.")
        
        return "\n".join(notes)
    
    def _generate_niche_name(self, keyword):
        """Generate a niche name from a keyword"""
        # Clean the keyword
        keyword = keyword.strip().lower()
        
        # Example transformations
        niche_templates = [
            "{keyword} Products for Enthusiasts",
            "Specialized {keyword} Accessories",
            "Premium {keyword} Collection",
            "{keyword} Essentials",
            "Innovative {keyword} Solutions"
        ]
        
        import random
        template = random.choice(niche_templates)
        return template.format(keyword=keyword.title())
    
    def _generate_audience_demographics(self, keyword):
        """Generate audience demographics based on keyword"""
        import random
        
        # Default demographics
        demographics = {
            'age_range': [25, 45],
            'gender': 'mixed',
            'interests': [keyword]
        }
        
        # Modify based on keyword
        tech_keywords = ['tech', 'gadget', 'electronic', 'digital', 'computer', 'phone']
        beauty_keywords = ['beauty', 'makeup', 'skincare', 'cosmetic', 'hair']
        fitness_keywords = ['fitness', 'workout', 'exercise', 'gym', 'sport']
        home_keywords = ['home', 'kitchen', 'decor', 'furniture', 'garden']
        
        if any(k in keyword.lower() for k in tech_keywords):
            demographics['age_range'] = [18, 40]
            demographics['gender'] = 'mixed'
            demographics['interests'] = ['technology', 'gadgets', 'innovation']
            
        elif any(k in keyword.lower() for k in beauty_keywords):
            demographics['age_range'] = [18, 35]
            demographics['gender'] = 'mostly female'
            demographics['interests'] = ['beauty', 'fashion', 'self-care']
            
        elif any(k in keyword.lower() for k in fitness_keywords):
            demographics['age_range'] = [20, 45]
            demographics['gender'] = 'mixed'
            demographics['interests'] = ['fitness', 'health', 'active lifestyle']
            
        elif any(k in keyword.lower() for k in home_keywords):
            demographics['age_range'] = [25, 55]
            demographics['gender'] = 'mixed'
            demographics['interests'] = ['home improvement', 'interior design', 'cooking']
            
        return demographics