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