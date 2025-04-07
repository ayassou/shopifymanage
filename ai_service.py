import os
import json
import base64
import logging
import requests
import datetime
from io import BytesIO
import pandas as pd
from openai import OpenAI
from urllib.parse import urlparse
import trafilatura
from PIL import Image

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AIService:
    """
    Central AI service for coordinating product generation tasks.
    This service orchestrates all AI-related operations including web scraping,
    image processing, SEO optimization, and product data generation.
    """
    
    def __init__(self, api_key=None, api_provider="openai"):
        """
        Initialize the AI service with the appropriate API credentials.
        
        Args:
            api_key (str, optional): The API key for the AI provider. If None, will try to get from env.
            api_provider (str): The AI provider to use ('openai' or 'x.ai')
        """
        self.api_provider = api_provider
        
        # Set up the appropriate client based on provider
        if self.api_provider == "openai":
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key is required. Please provide it or set OPENAI_API_KEY in environment variables.")
            self.client = OpenAI(api_key=self.api_key)
        elif self.api_provider == "x.ai":
            self.api_key = api_key or os.environ.get("XAI_API_KEY")
            if not self.api_key:
                raise ValueError("X.AI API key is required. Please provide it or set XAI_API_KEY in environment variables.")
            self.client = OpenAI(base_url="https://api.x.ai/v1", api_key=self.api_key)
        else:
            raise ValueError(f"Unsupported API provider: {api_provider}")
    
    def generate_product_data(self, input_type, input_data, num_variants=1):
        """
        Central method to generate product data based on input type and data.
        
        Args:
            input_type (str): Type of input ('url', 'text', or 'partial_data')
            input_data (str or dict): The input data (URL, text description, or partial product data)
            num_variants (int): Number of product variants to generate
            
        Returns:
            dict: Generated product data in CSV-compatible format
        """
        product_data = {}
        
        try:
            # Step 1: Extract initial data based on input type
            if input_type == "url":
                # Extract data from URL
                scraped_data = self.scrape_website(input_data)
                product_data.update(scraped_data)
                
                # Try to extract and download images
                image_urls = self.extract_image_urls(input_data)
                if image_urls:
                    product_data["image_urls"] = image_urls
            
            elif input_type == "text":
                # Generate product data from natural language description
                text_based_data = self.generate_from_text(input_data, num_variants)
                product_data.update(text_based_data)
            
            elif input_type == "partial_data":
                # Complete partial product data
                product_data.update(input_data)
                completed_data = self.complete_product_data(input_data)
                product_data.update(completed_data)
            
            else:
                raise ValueError(f"Unsupported input type: {input_type}")
            
            # Step 2: Enrich data with SEO optimization if not already present
            if not all(key in product_data for key in ["meta_title", "meta_description", "meta_keywords"]):
                seo_data = self.optimize_seo(product_data)
                product_data.update(seo_data)
            
            # Step 3: Generate variants if requested and not already present
            if num_variants > 1 and "variants" not in product_data:
                variants = self.generate_variants(product_data, num_variants)
                product_data["variants"] = variants
            
            # Step 4: Format the data for CSV export
            formatted_data = self.format_for_csv(product_data)
            return formatted_data
            
        except Exception as e:
            logger.error(f"Error generating product data: {str(e)}")
            raise
    
    def scrape_website(self, url):
        """
        Scrape product information from a website URL.
        
        Args:
            url (str): The URL to scrape
            
        Returns:
            dict: Extracted product data
        """
        try:
            logger.debug(f"Scraping website: {url}")
            
            # Validate URL format
            parsed_url = urlparse(url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                raise ValueError("Invalid URL format")
            
            # Fetch the page content using trafilatura
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                raise ValueError(f"Failed to download content from {url}")
            
            # Extract main text content
            extracted_text = trafilatura.extract(downloaded)
            if not extracted_text:
                raise ValueError(f"Failed to extract text content from {url}")
            
            # Use AI to extract structured product information from the text
            prompt = f"""
            Extract product information from the following webpage content. 
            Include as many details as possible in a structured format.
            
            Webpage content:
            {extracted_text[:8000]}  # Limit to avoid token limits
            
            Please extract and return the following in JSON format:
            - product_title: The title of the product
            - product_description: Detailed description of the product
            - price: The price of the product (if available)
            - product_type: The category or type of the product
            - tags: Keywords associated with the product
            - vendor: The manufacturer or vendor (if available)
            - features: List of product features or specifications
            - meta_title: SEO-optimized title (70 chars max)
            - meta_description: SEO-optimized description (160 chars max)
            - meta_keywords: SEO keywords separated by commas
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            logger.debug(f"Successfully extracted product data from {url}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to scrape website {url}: {str(e)}")
            raise
    
    def extract_image_urls(self, url):
        """
        Extract product image URLs from a website.
        
        Args:
            url (str): The URL to scrape for images
            
        Returns:
            list: List of image URLs found on the page
        """
        try:
            logger.debug(f"Extracting image URLs from: {url}")
            
            # Fetch the page content
            response = requests.get(url)
            response.raise_for_status()
            html_content = response.text
            
            # Use AI to analyze the HTML and extract likely product image URLs
            prompt = f"""
            Analyze this HTML code and extract URLs of product images only. 
            Ignore logos, icons, and non-product images.
            Focus on high-resolution product images.
            Limit to 5 main product images maximum.
            
            Return only a JSON array of image URLs, like:
            ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
            
            HTML content:
            {html_content[:15000]}  # Limit to avoid token limits
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            
            # Check if it's in the expected format (list of URLs)
            if isinstance(result, dict) and "urls" in result:
                image_urls = result["urls"]
            elif isinstance(result, list):
                image_urls = result
            else:
                image_urls = []
                
            logger.debug(f"Extracted {len(image_urls)} image URLs")
            return image_urls
            
        except Exception as e:
            logger.error(f"Failed to extract image URLs from {url}: {str(e)}")
            # Return empty list rather than failing the whole process
            return []
    
    def generate_from_text(self, text_description, num_variants=1):
        """
        Generate product data from a natural language description.
        
        Args:
            text_description (str): The natural language description of the product(s)
            num_variants (int): Number of product variants to generate
            
        Returns:
            dict: Generated product data
        """
        try:
            logger.debug("Generating product data from text description")
            
            prompt = f"""
            Generate detailed product information based on this description:
            "{text_description}"
            
            Create a complete product listing with the following details in JSON format:
            - product_title: Compelling product title
            - product_description: Detailed, marketing-focused description
            - price: Suggested retail price
            - product_type: Category classification
            - tags: Relevant search keywords (array)
            - vendor: Suggested brand or manufacturer
            - features: List of key product features (array)
            - meta_title: SEO-optimized title (70 chars max)
            - meta_description: SEO-optimized description (160 chars max)
            - meta_keywords: SEO keywords separated by commas
            
            If the description mentions multiple products or variants, focus on the main product.
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            logger.debug("Successfully generated product data from text description")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate product data from text: {str(e)}")
            raise
    
    def complete_product_data(self, partial_data):
        """
        Complete partial product data with AI-generated content.
        
        Args:
            partial_data (dict): Partial product data
            
        Returns:
            dict: Completed product data
        """
        try:
            logger.debug("Completing partial product data")
            
            # Convert partial data to a formatted string for the prompt
            partial_data_str = json.dumps(partial_data, indent=2)
            
            prompt = f"""
            Complete the missing fields in this partial product data:
            
            {partial_data_str}
            
            Fill in any missing required fields from this list:
            - product_title
            - product_description
            - price
            - product_type
            - tags (array)
            - vendor
            - features (array)
            - meta_title (70 chars max)
            - meta_description (160 chars max)
            - meta_keywords (comma separated)
            
            Return a complete JSON object with all fields filled in.
            For existing fields, maintain their values unless they need to be fixed or improved.
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            
            # Only keep fields that weren't in the original data
            completed_data = {k: v for k, v in result.items() if k not in partial_data}
            
            logger.debug("Successfully completed partial product data")
            return completed_data
            
        except Exception as e:
            logger.error(f"Failed to complete product data: {str(e)}")
            raise
    
    def optimize_seo(self, product_data):
        """
        Generate SEO-optimized content for a product.
        
        Args:
            product_data (dict): The product data to optimize
            
        Returns:
            dict: SEO-optimized data fields
        """
        try:
            logger.debug("Optimizing SEO for product")
            
            # Extract relevant fields for SEO optimization
            product_title = product_data.get("product_title", "")
            product_description = product_data.get("product_description", "")
            product_type = product_data.get("product_type", "")
            
            # Combine relevant data for the AI to work with
            product_context = f"""
            Product Title: {product_title}
            Product Description: {product_description}
            Product Type/Category: {product_type}
            """
            
            prompt = f"""
            Generate SEO-optimized content for this product:
            
            {product_context}
            
            Return a JSON object with:
            1. meta_title: SEO-optimized title (60-70 characters max)
            2. meta_description: Compelling meta description (150-160 characters max)
            3. meta_keywords: 7-10 relevant keywords separated by commas
            4. url_handle: SEO-friendly URL slug (lowercase, hyphens instead of spaces)
            5. tags: Array of 5-7 relevant search tags
            
            Consider current SEO best practices for e-commerce. Focus on searchability, 
            click-through rates, and conversion optimization. Avoid keyword stuffing.
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            logger.debug("Successfully generated SEO-optimized content")
            return result
            
        except Exception as e:
            logger.error(f"Failed to optimize SEO: {str(e)}")
            raise
    
    def generate_variants(self, product_data, num_variants):
        """
        Generate product variants based on base product data.
        
        Args:
            product_data (dict): Base product data
            num_variants (int): Number of variants to generate
            
        Returns:
            list: List of product variants
        """
        try:
            logger.debug(f"Generating {num_variants} product variants")
            
            # Convert product data to a formatted string for the prompt
            product_data_str = json.dumps(product_data, indent=2)
            
            prompt = f"""
            Generate {num_variants} variants for this product:
            
            {product_data_str}
            
            For each variant, return:
            - title: Variant title (e.g., "Small Blue T-Shirt")
            - sku: Unique SKU code
            - price: Price for this variant
            - option1: First option (e.g., "Size")
            - value1: Value for option1 (e.g., "Small")
            - option2: Second option if applicable (e.g., "Color")
            - value2: Value for option2 (e.g., "Blue")
            - option3: Third option if applicable
            - value3: Value for option3
            
            Return a JSON array of variant objects.
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            
            # Check if the result contains a "variants" key or is itself an array
            if isinstance(result, dict) and "variants" in result:
                variants = result["variants"]
            elif isinstance(result, list):
                variants = result
            else:
                variants = []
                
            logger.debug(f"Successfully generated {len(variants)} product variants")
            return variants
            
        except Exception as e:
            logger.error(f"Failed to generate product variants: {str(e)}")
            # Return empty list rather than failing
            return []
    
    def format_for_csv(self, product_data):
        """
        Format the product data for CSV export.
        
        Args:
            product_data (dict): The processed product data
            
        Returns:
            dict: CSV-ready data structure
        """
        try:
            # Extract base product data
            csv_data = {
                "Handle": product_data.get("url_handle", ""),
                "Title": product_data.get("product_title", ""),
                "Body HTML": product_data.get("product_description", ""),
                "Vendor": product_data.get("vendor", ""),
                "Product Category": product_data.get("product_type", ""),
                "Type": product_data.get("product_type", ""),
                "Tags": ", ".join(product_data.get("tags", [])) if isinstance(product_data.get("tags"), list) else product_data.get("tags", ""),
                "Published": "TRUE",
                "Option1 Name": "",
                "Option1 Value": "",
                "Option2 Name": "",
                "Option2 Value": "",
                "Option3 Name": "",
                "Option3 Value": "",
                "Variant SKU": "",
                "Variant Price": product_data.get("price", ""),
                "Variant Compare At Price": "",
                "Variant Requires Shipping": "TRUE",
                "Variant Taxable": "TRUE",
                "Variant Inventory Tracker": "shopify",
                "Variant Inventory Qty": "10",
                "Variant Inventory Policy": "deny",
                "Variant Fulfillment Service": "manual",
                "Variant Weight": "",
                "Variant Weight Unit": "kg",
                "Variant Image": "",
                "Metafields: custom.meta_title": product_data.get("meta_title", ""),
                "Metafields: custom.meta_description": product_data.get("meta_description", ""),
                "Metafields: custom.meta_keywords": product_data.get("meta_keywords", ""),
                "Image Src": "",
                "Image Position": "",
                "Image Alt Text": "",
                "Gift Card": "FALSE",
                "SEO Title": product_data.get("meta_title", ""),
                "SEO Description": product_data.get("meta_description", ""),
                "Google Shopping / Category": product_data.get("product_type", ""),
                "Status": "active"
            }
            
            # Handle variants if present
            formatted_data = []
            variants = product_data.get("variants", [])
            
            if variants and len(variants) > 0:
                # First row contains the product info without variant specifics
                base_product = csv_data.copy()
                
                # Add option names from the first variant
                if len(variants) > 0:
                    first_variant = variants[0]
                    base_product["Option1 Name"] = first_variant.get("option1", "")
                    base_product["Option2 Name"] = first_variant.get("option2", "")
                    base_product["Option3 Name"] = first_variant.get("option3", "")
                
                formatted_data.append(base_product)
                
                # Add variant rows
                for i, variant in enumerate(variants):
                    variant_row = {k: "" for k in csv_data.keys()}  # Empty row except for variant data
                    variant_row["Handle"] = csv_data["Handle"]  # Keep handle the same
                    variant_row["Option1 Value"] = variant.get("value1", "")
                    variant_row["Option2 Value"] = variant.get("value2", "")
                    variant_row["Option3 Value"] = variant.get("value3", "")
                    variant_row["Variant SKU"] = variant.get("sku", "")
                    variant_row["Variant Price"] = variant.get("price", csv_data["Variant Price"])
                    variant_row["Variant Inventory Qty"] = "10"
                    formatted_data.append(variant_row)
            else:
                formatted_data.append(csv_data)
            
            # Handle image URLs if present
            image_urls = product_data.get("image_urls", [])
            if image_urls and len(image_urls) > 0:
                for i, image_url in enumerate(image_urls):
                    if i == 0 and len(formatted_data) > 0:
                        # Add the first image to the main product/first variant
                        formatted_data[0]["Image Src"] = image_url
                        formatted_data[0]["Image Position"] = "1"
                        formatted_data[0]["Image Alt Text"] = f"{csv_data['Title']} - Main Image"
                    else:
                        # Add additional images as new rows
                        image_row = {k: "" for k in csv_data.keys()}  # Empty row except for image data
                        image_row["Handle"] = csv_data["Handle"]  # Keep handle the same
                        image_row["Image Src"] = image_url
                        image_row["Image Position"] = str(i + 1)
                        image_row["Image Alt Text"] = f"{csv_data['Title']} - Image {i+1}"
                        formatted_data.append(image_row)
            
            # Create a DataFrame for CSV export
            df = pd.DataFrame(formatted_data)
            
            # Return in a format compatible with the existing system
            return {
                "csv_data": df, 
                "product_count": 1,
                "variant_count": len(variants),
                "image_count": len(image_urls) if "image_urls" in product_data else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to format product data for CSV: {str(e)}")
            raise
            
    def generate_blog_post(self, blog_params):
        """
        Generate a complete blog post based on input parameters.
        
        Args:
            blog_params (dict): Parameters for blog generation including topic, keywords, etc.
            
        Returns:
            dict: Generated blog post data
        """
        try:
            logger.debug(f"Generating blog post on topic: {blog_params.get('topic', 'Unspecified')}")
            
            # Extract parameters
            title = blog_params.get('title')
            topic = blog_params.get('topic', '')
            keywords = blog_params.get('keywords', '')
            content_type = blog_params.get('content_type', 'informational')
            tone = blog_params.get('tone', 'professional')
            target_audience = blog_params.get('target_audience', '')
            word_count = blog_params.get('word_count', 1000)
            include_sections = blog_params.get('include_sections', True)
            include_faq = blog_params.get('include_faq', True)
            include_cta = blog_params.get('include_cta', True)
            reference_products = blog_params.get('reference_products', True)
            
            # Content type mapping for better prompting
            content_type_instructions = {
                'how_to': "Create a step-by-step guide explaining how to solve a problem or accomplish a task.",
                'list': "Format as a numbered list article with clear bullet points and brief explanations.",
                'comparison': "Compare and contrast different options, highlighting pros and cons.",
                'informational': "Provide detailed, authoritative information on the topic.",
                'case_study': "Structure as a case study with background, challenge, solution, and results.",
                'news': "Present as timely news or analysis of current trends.",
                'story': "Frame as a narrative with a beginning, middle, and end."
            }
            
            # Tone mapping for better prompting
            tone_instructions = {
                'professional': "Use formal, authoritative language appropriate for business contexts.",
                'casual': "Write in a conversational, friendly tone as if talking to a friend.",
                'enthusiastic': "Employ energetic, passionate language that conveys excitement.",
                'informative': "Focus on clear, factual communication without unnecessary embellishment.",
                'humorous': "Include appropriate humor and a light-hearted approach.",
                'authoritative': "Write as an expert with strong, confident assertions backed by evidence."
            }
            
            # Structure options based on parameters
            structure_instructions = []
            if include_sections:
                structure_instructions.append("Organize the post with clear H2 and H3 headings for different sections.")
            if include_faq:
                structure_instructions.append("Include a FAQ section at the end with 3-5 common questions and concise answers.")
            if include_cta:
                structure_instructions.append("End with a strong call-to-action that encourages reader engagement.")
            if reference_products:
                structure_instructions.append("Naturally incorporate references to relevant products where appropriate.")
            
            # Build the prompt
            content_instruction = content_type_instructions.get(content_type, content_type_instructions['informational'])
            tone_instruction = tone_instructions.get(tone, tone_instructions['professional'])
            structure_instruction = " ".join(structure_instructions)
            
            # If title is provided, use it; otherwise, instruct AI to generate one
            title_instruction = f"Use this title: '{title}'" if title else "Generate an engaging, SEO-friendly title."
            
            prompt = f"""
            Generate a comprehensive blog post on: "{topic}"
            
            {title_instruction}
            
            Key details:
            - Keywords to include: {keywords}
            - Target audience: {target_audience if target_audience else "General readers interested in this topic"}
            - Target word count: approximately {word_count} words
            
            Content approach: {content_instruction}
            Tone of voice: {tone_instruction}
            Structure: {structure_instruction}
            
            Format the response as a JSON object with the following fields:
            - title: The blog post title (engaging and SEO-optimized)
            - content: The full blog post content with HTML formatting (use <h2>, <h3>, <p>, <ul>, <li> tags appropriately)
            - summary: A 2-3 sentence summary of the post
            - meta_title: SEO-optimized title (60-70 characters)
            - meta_description: Compelling meta description (150-160 characters)
            - meta_keywords: 5-8 relevant keywords separated by commas
            - url_handle: SEO-friendly URL slug (lowercase, hyphens instead of spaces)
            - tags: Array of 5-7 relevant tags
            - category: Suggested primary category for the post
            - estimated_reading_time: Estimated reading time in minutes
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            
            # Add some metadata
            result['generated_at'] = datetime.datetime.now().isoformat()
            result['generation_params'] = {
                'topic': topic,
                'content_type': content_type,
                'tone': tone,
                'word_count': word_count
            }
            
            logger.debug(f"Successfully generated blog post: {result.get('title', 'Untitled')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate blog post: {str(e)}")
            raise
    
    def generate_page_content(self, page_params):
        """
        Generate content for a static page based on input parameters.
        
        Args:
            page_params (dict): Parameters for page generation including type, company info, etc.
            
        Returns:
            dict: Generated page content data
        """
        try:
            logger.debug(f"Generating page content for page type: {page_params.get('page_type', 'Unspecified')}")
            
            # Extract parameters
            page_type = page_params.get('page_type', 'about')
            title = page_params.get('title')
            company_name = page_params.get('company_name', '')
            company_description = page_params.get('company_description', '')
            industry = page_params.get('industry', '')
            founding_year = page_params.get('founding_year', '')
            location = page_params.get('location', '')
            company_values = page_params.get('values', '')
            tone = page_params.get('tone', 'professional')
            target_audience = page_params.get('target_audience', '')
            
            # Contact page parameters
            contact_email = page_params.get('contact_email', '')
            contact_phone = page_params.get('contact_phone', '')
            contact_address = page_params.get('contact_address', '')
            social_media = page_params.get('social_media', '')
            
            # FAQ parameters
            faq_topics = page_params.get('faq_topics', '')
            
            # Page type specific instructions
            page_type_instructions = {
                'about': "Create an engaging About Us page that tells the company's story, mission, vision, and values.",
                'contact': "Design a clear Contact Us page with all contact information and a brief message encouraging visitors to reach out.",
                'faq': "Develop a comprehensive FAQ page addressing common customer questions with clear, helpful answers.",
                'terms': "Draft professionally-worded Terms of Service covering standard legal aspects of website and store usage.",
                'privacy': "Create a thorough Privacy Policy explaining how customer data is collected, used, and protected.",
                'returns': "Detail the store's return and refund policies in a customer-friendly, clear manner.",
                'shipping': "Explain shipping methods, timeframes, costs, and policies in an organized format."
            }
            
            # Tone mapping
            tone_instructions = {
                'professional': "Use formal, polished language appropriate for business contexts.",
                'friendly': "Write in a warm, approachable tone that feels welcoming to visitors.",
                'formal': "Employ precise, business-like language suitable for legal or policy documents.",
                'informative': "Focus on clear, factual communication that prioritizes information delivery.",
                'conversational': "Use a casual, personable tone as if speaking directly to the visitor."
            }
            
            # Build the prompt based on page type
            content_instruction = page_type_instructions.get(page_type, page_type_instructions['about'])
            tone_instruction = tone_instructions.get(tone, tone_instructions['professional'])
            
            # If title is provided, use it; otherwise, instruct AI to generate one
            title_instruction = f"Use this title: '{title}'" if title else "Generate an appropriate page title."
            
            # Base company information for context
            company_context = f"""
            Company/Store Name: {company_name if company_name else "[Company Name]"}
            Industry: {industry if industry else "Unspecified"}
            Description: {company_description if company_description else "Unspecified"}
            Founded: {founding_year if founding_year else "Unspecified"}
            Location: {location if location else "Unspecified"}
            Values: {company_values if company_values else "Unspecified"}
            Target Audience: {target_audience if target_audience else "General customers"}
            """
            
            # Page type specific contexts
            type_specific_context = ""
            if page_type == 'contact':
                type_specific_context = f"""
                Contact Information:
                Email: {contact_email if contact_email else "[Contact Email]"}
                Phone: {contact_phone if contact_phone else "[Contact Phone]"}
                Address: {contact_address if contact_address else "[Contact Address]"}
                Social Media: {social_media if social_media else "[Social Media Handles]"}
                """
            elif page_type == 'faq':
                type_specific_context = f"""
                FAQ Topics to Cover: {faq_topics if faq_topics else "Common customer questions about products, ordering, shipping, returns, etc."}
                """
            
            # Build the prompt
            prompt = f"""
            Generate content for a {page_type.replace('_', ' ').title()} page for an e-commerce store.
            
            {title_instruction}
            
            Company Information:
            {company_context}
            
            {type_specific_context}
            
            Content approach: {content_instruction}
            Tone of voice: {tone_instruction}
            
            Format the response as a JSON object with the following fields:
            - title: The page title
            - content: The full page content with HTML formatting (use <h2>, <h3>, <p>, <ul>, <li> tags appropriately)
            - summary: A 1-2 sentence summary of the page's purpose
            - meta_title: SEO-optimized title (60-70 characters)
            - meta_description: Compelling meta description (150-160 characters)
            - meta_keywords: 5-8 relevant keywords separated by commas
            - url_handle: SEO-friendly URL slug (lowercase, hyphens instead of spaces)
            """
            
            # Add FAQ-specific instruction if needed
            if page_type == 'faq':
                prompt += """
                - faq_items: An array of objects with "question" and "answer" fields
                """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            
            # Add some metadata
            result['generated_at'] = datetime.datetime.now().isoformat()
            result['page_type'] = page_type
            result['generation_params'] = {
                'company_name': company_name,
                'industry': industry,
                'tone': tone
            }
            
            logger.debug(f"Successfully generated page content: {result.get('title', 'Untitled')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate page content: {str(e)}")
            raise
    
    def generate_page_image(self, page_type, title, company_info):
        """
        Generate a featured image for a static page.
        
        Args:
            page_type (str): The type of page (about, contact, etc.)
            title (str): The page title
            company_info (str): Brief company information
            
        Returns:
            str: URL or base64 data of the generated image
        """
        try:
            logger.debug(f"Generating featured image for {page_type} page: {title}")
            
            # Create a descriptive prompt for the image based on page type
            image_prompts = {
                'about': f"Create a professional image representing a company about page for {company_info}. Show elements that convey trust, professionalism, and company culture.",
                'contact': "Create a clean, professional image for a contact page with subtle visual elements like message icons, phones, or communication themes.",
                'faq': "Create a simple, clean image representing a FAQ or help section with subtle question mark visuals or people finding solutions.",
                'terms': "Create a professional, subtle image for terms of service or legal page with elements suggesting agreement, security, or protection.",
                'privacy': "Create a minimalist image representing data privacy and protection with subtle visual elements like shields or locks.",
                'returns': "Create a simple image representing a product return policy with subtle visual elements of packages or customer service.",
                'shipping': "Create a professional image representing shipping and delivery with subtle visual elements of packages, trucks, or global delivery."
            }
            
            # Get the appropriate prompt based on page type
            image_prompt = image_prompts.get(page_type, image_prompts['about'])
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=image_prompt,
                n=1,
                size="1024x1024"
            )
            
            # Get the URL of the generated image
            image_url = response.data[0].url
            
            # Download the image
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            
            # Convert to base64 for storage
            image_data = base64.b64encode(image_response.content).decode('utf-8')
            
            logger.debug("Successfully generated page image")
            return f"data:image/png;base64,{image_data}"
            
        except Exception as e:
            logger.error(f"Failed to generate page image: {str(e)}")
            # Return None without failing the whole process
            return None
            
    def generate_blog_image(self, title, content_summary):
        """
        Generate a featured image for a blog post.
        
        Args:
            title (str): The blog post title
            content_summary (str): A summary of the blog content
            
        Returns:
            str: URL or base64 data of the generated image
        """
        try:
            logger.debug(f"Generating featured image for blog: {title}")
            
            # Create a descriptive prompt for the image
            prompt = f"""
            Create a featured image for a blog post titled: "{title}"
            
            Content summary: {content_summary}
            
            Style: Professional, editorial, suitable for a business blog.
            Make it visually appealing and relevant to the topic.
            No text overlay needed - the image should be clean and versatile.
            """
            
            # Only OpenAI supports image generation currently
            if self.api_provider == "openai":
                response = self.client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    n=1,
                    size="1024x1024",
                )
                image_url = response.data[0].url
                logger.debug(f"Successfully generated image with URL: {image_url}")
                return image_url
            else:
                logger.warning(f"Image generation not supported for provider: {self.api_provider}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate blog image: {str(e)}")
            # Return None rather than failing the whole process
            return None
            
    def analyze_image_for_caption(self, image_data, caption_style="descriptive", max_alt_length=125):
        """
        Analyze an image and generate appropriate captions and alt text.
        
        Args:
            image_data (bytes or str): Image data as bytes or base64-encoded string or URL
            caption_style (str): Style of caption to generate ('descriptive', 'seo', 'minimal', 'technical')
            max_alt_length (int): Maximum length for alt text
            
        Returns:
            dict: Dictionary containing generated caption data
        """
        try:
            logger.debug("Analyzing image for caption generation")
            
            # Determine how to process the image data
            if isinstance(image_data, str) and (image_data.startswith('http://') or image_data.startswith('https://')):
                # It's a URL, we'll pass it directly to the vision model
                image_for_analysis = image_data
            elif isinstance(image_data, bytes):
                # It's binary data, encode to base64
                base64_image = base64.b64encode(image_data).decode('utf-8')
                image_for_analysis = f"data:image/jpeg;base64,{base64_image}"
            elif isinstance(image_data, str) and image_data.startswith('data:image'):
                # It's already base64 encoded with data URL
                image_for_analysis = image_data
            else:
                # Try to convert from base64 string without prefix
                try:
                    image_for_analysis = f"data:image/jpeg;base64,{image_data}"
                except:
                    logger.error("Invalid image data format provided")
                    return None
            
            # Create a prompt based on the requested caption style
            style_prompts = {
                "descriptive": "Analyze this product image in detail. Describe what you see including color, style, design, materials, and any notable features. Focus on being descriptive and accurate.",
                "seo": "Analyze this product image for e-commerce. Create SEO-friendly descriptions that include likely search terms. Focus on features and benefits that shoppers would search for.",
                "minimal": "Create a concise, minimal description of this product image. Focus on only the most essential details in as few words as possible.",
                "technical": "Analyze this product image focusing on technical specifications, materials, dimensions, and functional features. Be precise and detail-oriented."
            }
            
            prompt = style_prompts.get(caption_style, style_prompts["descriptive"])
            
            # Add instructions for output format
            system_prompt = f"""
            You are an e-commerce image analysis expert specializing in product photography. 
            {prompt}
            
            Format your response as a JSON object with the following structure:
            {{
                "alt_text": "A short, descriptive alt text under {max_alt_length} characters",
                "caption": "A longer, more detailed caption suitable for product descriptions",
                "tags": ["tag1", "tag2", "tag3"], 
                "product_title": "Suggested product title based on the image",
                "product_category": "Suggested product category or type",
                "seo_keywords": ["keyword1", "keyword2", "keyword3"],
                "detailed_description": "A paragraph with detailed product description"
            }}
            
            Ensure the alt_text is under {max_alt_length} characters and follows accessibility best practices.
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            if self.api_provider == "openai":
                # Use GPT-4o with vision for image analysis
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user", 
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Please analyze this product image and provide the information in the specified JSON format."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": image_for_analysis}
                                }
                            ]
                        }
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=1000
                )
                
                result = json.loads(response.choices[0].message.content)
                logger.debug("Successfully generated image caption data")
                return result
                
            elif self.api_provider == "x.ai":
                # Use Grok-2-vision for image analysis
                response = self.client.chat.completions.create(
                    model="grok-2-vision-1212",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user", 
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Please analyze this product image and provide the information in the specified JSON format."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": image_for_analysis}
                                }
                            ]
                        }
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=1000
                )
                
                result = json.loads(response.choices[0].message.content)
                logger.debug("Successfully generated image caption data")
                return result
                
        except Exception as e:
            logger.error(f"Error analyzing image for caption: {str(e)}")
            return None
            
    def search_images(self, query, count=5):
        """
        Search for images based on a query string.
        
        Args:
            query (str): Search query for images
            count (int): Number of images to retrieve
            
        Returns:
            list: List of image URLs
        """
        # This is a placeholder - in a real implementation, you would integrate
        # with a search API like Google Custom Search, Bing Image Search, etc.
        logger.warning("Image search functionality requires integration with a search API")
        # For demo purposes, return a message
        return []
        
    def download_image(self, url):
        """
        Download an image from a URL.
        
        Args:
            url (str): URL of the image
            
        Returns:
            bytes: Image data as bytes
        """
        try:
            logger.debug(f"Downloading image from URL: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            logger.debug(f"Successfully downloaded image ({len(response.content)} bytes)")
            return response.content
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {e}")
            return None
            
    def process_image_batch(self, images_data, batch_name, caption_style="descriptive", max_alt_length=125, output_format="csv"):
        """
        Process a batch of images to generate captions and alt text.
        
        Args:
            images_data (list): List of image data (URLs, paths, or binary data)
            batch_name (str): Name for this batch of images
            caption_style (str): Style of captions to generate
            max_alt_length (int): Maximum length for alt text
            output_format (str): Output format (csv, shopify_update, library)
            
        Returns:
            dict: Processing results including generated data
        """
        logger.debug(f"Processing image batch: {batch_name}, {len(images_data)} images")
        results = []
        
        for i, image in enumerate(images_data):
            # Log progress
            logger.debug(f"Processing image {i+1}/{len(images_data)}")
            
            # Determine if this is a URL, path, or binary data
            if isinstance(image, str) and (image.startswith('http://') or image.startswith('https://')):
                # It's a URL
                image_url = image
                image_data = self.download_image(image_url)
                filename = os.path.basename(urlparse(image_url).path)
            elif isinstance(image, str) and os.path.exists(image):
                # It's a file path
                filename = os.path.basename(image)
                with open(image, 'rb') as f:
                    image_data = f.read()
                image_url = None
            elif isinstance(image, bytes):
                # It's binary data
                image_data = image
                filename = f"image-{i+1}.jpg"
                image_url = None
            else:
                logger.error(f"Unsupported image data format: {type(image)}")
                continue
                
            # Skip if image couldn't be processed
            if not image_data:
                logger.warning(f"Could not process image: {image}")
                continue
                
            # Generate captions
            caption_data = self.analyze_image_for_caption(image_data, caption_style, max_alt_length)
            
            if caption_data:
                result = {
                    "filename": filename,
                    "url": image_url,
                    "caption_data": caption_data,
                    "status": "completed"
                }
            else:
                result = {
                    "filename": filename,
                    "url": image_url,
                    "status": "failed",
                    "error_message": "Failed to generate caption data"
                }
                
            results.append(result)
            
        # Format the results based on the requested output format
        if output_format == "csv":
            return self.format_captions_for_csv(results)
        elif output_format == "shopify_update":
            return results  # Raw format for Shopify updates
        else:
            return results  # Default format
    
    def format_captions_for_csv(self, results):
        """
        Format image caption results for CSV export.
        
        Args:
            results (list): List of image processing results
            
        Returns:
            dict: CSV-compatible data structure
        """
        logger.debug("Formatting caption results for CSV")
        csv_data = {
            "Handle": [],
            "Image Src": [],
            "Image Position": [],
            "Image Alt Text": [],
            "Variant SKU": [],
            "Metafields: alt_text": [],
            "Tags": []
        }
        
        for i, result in enumerate(results):
            if result["status"] == "completed":
                filename = result["filename"] or f"product-image-{i+1}"
                handle = filename.split('.')[0].lower().replace(' ', '-')
                
                csv_data["Handle"].append(handle)
                csv_data["Image Src"].append(result["url"] or "")
                csv_data["Image Position"].append(i + 1)
                csv_data["Image Alt Text"].append(result["caption_data"]["alt_text"])
                csv_data["Variant SKU"].append("")  # Leave blank for default
                csv_data["Metafields: alt_text"].append(result["caption_data"]["alt_text"])
                
                # Join tags with comma
                if "tags" in result["caption_data"]:
                    tags = ", ".join(result["caption_data"]["tags"])
                    csv_data["Tags"].append(tags)
                else:
                    csv_data["Tags"].append("")
        
        logger.debug(f"CSV formatting complete, {len(csv_data['Handle'])} processed")
        return csv_data
        
    def generate_image_captions(self, image_source, include_alt_text=True, include_seo=True, 
                              include_tags=True, include_product_suggestions=True):
        """
        Generate captions and descriptive text for product images using AI vision models.
        
        Args:
            image_source (dict): Image source information with type ('file' or 'url') and path/url
            include_alt_text (bool): Generate accessibility-focused alt text
            include_seo (bool): Generate SEO keywords and metadata
            include_tags (bool): Generate categorization tags
            include_product_suggestions (bool): Suggest product name and category
            
        Returns:
            dict: Generated captions and metadata
        """
        try:
            logger.debug(f"Generating captions for image: {image_source}")
            
            # Prepare the image for processing - either from file or URL
            image_data = None
            if image_source['type'] == 'file':
                # Load image from file path
                with open(image_source['path'], 'rb') as img_file:
                    image_data = base64.b64encode(img_file.read()).decode('utf-8')
            elif image_source['type'] == 'url':
                # Download image from URL
                response = requests.get(image_source['url'])
                response.raise_for_status()
                image_data = base64.b64encode(response.content).decode('utf-8')
            else:
                raise ValueError(f"Unsupported image source type: {image_source['type']}")
            
            if not image_data:
                raise ValueError("Failed to load image data")
            
            # Construct the vision model prompt based on requested outputs
            system_prompt = """
            You are an expert product photographer and e-commerce specialist.
            Analyze this product image and provide detailed, accurate captions and metadata.
            Focus on describing what you see in detail, including:
            - Visual characteristics (color, shape, pattern, texture)
            - Product category and possible uses
            - Notable features visible in the image
            - Style, design elements, and brand aesthetic
            
            Avoid making claims about non-visible features (functionality, materials, dimensions)
            unless they are clearly evident in the image.
            """
            
            user_prompt = "Provide the following information about this product image:"
            
            if include_alt_text:
                user_prompt += """
                
                - alt_text: A concise, SEO-friendly alt text (125 characters max) that accurately 
                  describes the product for accessibility and search engines
                """
                
            user_prompt += """
            
            - caption: A detailed, marketing-focused caption (1-2 paragraphs) describing the 
              product's visual appearance, style, and key visible features
            """
            
            if include_seo:
                user_prompt += """
                
                - seo_keywords: 5-7 targeted keywords relevant to the product image, 
                  comma-separated
                - seo_title: An SEO-optimized product image title (60-70 characters max)
                """
                
            if include_tags:
                user_prompt += """
                
                - tags: An array of 5-10 specific tags for categorizing the product, 
                  focusing on visible attributes
                """
                
            if include_product_suggestions:
                user_prompt += """
                
                - product_name: A suggested product name based on the image
                - product_category: The most specific product category/subcategory this item belongs to
                """
                
            user_prompt += """
            
            - detailed_description: A comprehensive visual description of the product 
              for detailed product pages or catalog entries
            
            Return your analysis in JSON format with these exact fields.
            """
            
            # Call vision API with appropriate model
            if self.api_provider == "openai":
                # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                # do not change this unless explicitly requested by the user
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                        ]}
                    ],
                    response_format={"type": "json_object"}
                )
            elif self.api_provider == "x.ai":
                # Use appropriate Grok model for vision
                response = self.client.chat.completions.create(
                    model="grok-2-vision-1212",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                        ]}
                    ]
                )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            logger.debug("Successfully generated image captions")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate image captions: {str(e)}")
            raise