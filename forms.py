from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed, MultipleFileField
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, IntegerField, RadioField, BooleanField
from wtforms.validators import DataRequired, URL, Optional, NumberRange

class UploadForm(FlaskForm):
    """Form for uploading product data files"""
    file = FileField('Product Data File', 
                     validators=[
                         FileRequired(),
                         FileAllowed(['csv', 'xlsx', 'xls'], 'CSV or Excel files only!')
                     ])
    submit = SubmitField('Upload and Process')

class ShopifySettingsForm(FlaskForm):
    """Form for Shopify API settings"""
    api_key = StringField('API Key', validators=[DataRequired()])
    password = PasswordField('API Password/Access Token', validators=[DataRequired()])
    store_url = StringField('Store URL', validators=[DataRequired(), URL()],
                          description='Example: mystore.myshopify.com')
    api_version = StringField('API Version', validators=[DataRequired()],
                            default='2023-07')
    submit = SubmitField('Save Settings')

class AISettingsForm(FlaskForm):
    """Form for AI API settings"""
    api_provider = SelectField('AI Provider', 
                             choices=[('openai', 'OpenAI (GPT-4o)'), 
                                      ('x.ai', 'X.AI (Grok)')],
                             default='openai')
    api_key = PasswordField('API Key', validators=[DataRequired()])
    submit = SubmitField('Save AI Settings')

class AIGeneratorForm(FlaskForm):
    """Form for the AI product generator"""
    input_type = RadioField('Input Type', 
                           choices=[
                               ('url', 'Product URL (Scrape Website)'),
                               ('text', 'Text Description'),
                               ('partial_data', 'Partial Product Data')
                           ],
                           default='url')
    
    # URL input fields
    product_url = StringField('Product URL', 
                             validators=[Optional(), URL()],
                             description='Enter URL of a product page to scrape')
    
    # Text description input fields
    product_description = TextAreaField('Product Description', 
                                      validators=[Optional()],
                                      description='Enter a detailed description of your product(s)')
    
    # Partial data input fields
    product_title = StringField('Product Title', validators=[Optional()])
    price = StringField('Price', validators=[Optional()])
    vendor = StringField('Vendor/Brand', validators=[Optional()])
    product_type = StringField('Product Category', validators=[Optional()])
    
    # Common settings
    variant_count = IntegerField('Number of Variants', 
                               validators=[Optional(), NumberRange(min=1, max=10)],
                               default=1,
                               description='How many variants to generate (sizes, colors, etc.)')
    
    seo_optimize = BooleanField('Optimize for SEO', default=True,
                              description='Generate SEO-friendly meta titles, descriptions, and keywords')
    
    extract_images = BooleanField('Extract Images', default=True,
                                description='For URLs: automatically extract product images')
    
    submit = SubmitField('Generate Product Data')
    
class BlogPostGeneratorForm(FlaskForm):
    """Form for the AI blog post generator"""
    title = StringField('Blog Post Title', 
                      validators=[Optional()],
                      description='Optional: Leave blank for AI to generate title')
    
    topic = StringField('Topic/Subject', 
                      validators=[DataRequired()],
                      description='Main subject of the blog post (e.g., "Summer Fashion Trends", "Benefits of Organic Products")')
    
    keywords = TextAreaField('Keywords', 
                           validators=[DataRequired()],
                           description='Comma-separated keywords to include in the post')
    
    content_type = SelectField('Content Type',
                            choices=[
                                ('how_to', 'How-To Guide'),
                                ('list', 'List Article (Top 10, etc.)'),
                                ('comparison', 'Comparison/Review'),
                                ('informational', 'Informational'),
                                ('case_study', 'Case Study'),
                                ('news', 'News/Trend Analysis'),
                                ('story', 'Story/Narrative')
                            ],
                            default='informational')
    
    tone = SelectField('Tone of Voice',
                     choices=[
                         ('professional', 'Professional'),
                         ('casual', 'Casual/Conversational'),
                         ('enthusiastic', 'Enthusiastic'),
                         ('informative', 'Informative'),
                         ('humorous', 'Humorous'),
                         ('authoritative', 'Authoritative')
                     ],
                     default='professional')
    
    target_audience = StringField('Target Audience',
                                validators=[Optional()],
                                description='Who is this content for? (e.g., "new parents", "tech enthusiasts")')
    
    word_count = IntegerField('Word Count',
                            validators=[Optional(), NumberRange(min=300, max=5000)],
                            default=1000,
                            description='Target length of the blog post')
    
    include_sections = BooleanField('Include Sections with Headings', default=True,
                                  description='Organize content into sections with headings')
    
    include_faq = BooleanField('Include FAQ Section', default=True,
                             description='Add a frequently asked questions section to the post')
    
    include_cta = BooleanField('Include Call to Action', default=True,
                             description='Add a call-to-action section at the end')
                             
    reference_products = BooleanField('Reference Store Products', default=True,
                                    description='Include relevant product mentions from your store')
    
    seo_optimize = BooleanField('Optimize for SEO', default=True,
                              description='Generate SEO-friendly meta title, description, and keywords')
    
    generate_image = BooleanField('Generate Featured Image', default=False,
                                description='Use AI to generate a featured image (requires image generation capabilities)')
    
    submit = SubmitField('Generate Blog Post')


class PageGeneratorForm(FlaskForm):
    """Form for the AI page content generator"""
    page_type = SelectField('Page Type',
                         choices=[
                             ('about', 'About Us'),
                             ('contact', 'Contact Us'),
                             ('faq', 'FAQ'),
                             ('terms', 'Terms of Service'),
                             ('privacy', 'Privacy Policy'),
                             ('returns', 'Return Policy'),
                             ('shipping', 'Shipping Information')
                         ],
                         default='about')
                         
    title = StringField('Page Title', 
                      validators=[Optional()],
                      description='Optional: Leave blank for AI to generate appropriate title')
    
    # Company Information (for About Us, etc.)
    company_name = StringField('Company/Store Name',
                             validators=[Optional()],
                             description='Your company or store name')
                             
    company_description = TextAreaField('Company Description',
                                      validators=[Optional()],
                                      description='Brief description of your company/store (products, services, mission)')
                                      
    industry = StringField('Industry',
                         validators=[Optional()],
                         description='E.g., Fashion, Electronics, Health & Beauty, Home Goods')
                         
    founding_year = IntegerField('Founding Year',
                               validators=[Optional(), NumberRange(min=1900, max=2030)],
                               description='Year your company was founded')
                               
    location = StringField('Company Location',
                         validators=[Optional()],
                         description='City, State, Country or multiple locations')
                         
    values = TextAreaField('Company Values',
                         validators=[Optional()],
                         description='Comma-separated list of your company values (e.g., "Sustainability, Quality, Innovation")')
    
    # Contact Information (for Contact pages)
    contact_email = StringField('Contact Email',
                              validators=[Optional()],
                              description='Primary contact email for your business')
                              
    contact_phone = StringField('Contact Phone',
                              validators=[Optional()],
                              description='Main business phone number')
                              
    contact_address = TextAreaField('Physical Address',
                                  validators=[Optional()],
                                  description='Your business address(es)')
                                  
    social_media = TextAreaField('Social Media',
                               validators=[Optional()],
                               description='List your social media handles (e.g., "Instagram: @yourstore, Facebook: yourstorefb")')
    
    # FAQ fields
    faq_topics = TextAreaField('FAQ Topics',
                             validators=[Optional()],
                             description='Comma-separated list of topics to generate FAQs about (e.g., "shipping, returns, sizing")')
    
    # General Page Settings
    tone = SelectField('Tone of Voice',
                     choices=[
                         ('professional', 'Professional'),
                         ('friendly', 'Friendly & Approachable'),
                         ('formal', 'Formal & Business-like'),
                         ('informative', 'Informative'),
                         ('conversational', 'Conversational')
                     ],
                     default='professional')
                     
    target_audience = StringField('Target Audience',
                                validators=[Optional()],
                                description='Who is your primary customer base?')
                                
    seo_optimize = BooleanField('Optimize for SEO', default=True,
                              description='Generate SEO-friendly meta title, description, and keywords')
                              
    generate_image = BooleanField('Generate Featured Image', default=False,
                                description='Use AI to create an on-brand featured image for this page')
                                
    submit = SubmitField('Generate Page Content')


class ImageCaptionGeneratorForm(FlaskForm):
    """Form for the AI image caption generator"""
    batch_name = StringField('Batch Name',
                           validators=[DataRequired()],
                           description='Name for this batch of images (for organization)')
    
    input_type = RadioField('Image Source', 
                          choices=[
                              ('url', 'Product URL (Scrape Images)'),
                              ('upload', 'Upload Images'),
                              ('shopify', 'Import from Shopify Store'),
                              ('search', 'Web Image Search')
                          ],
                          default='url')
    
    # URL input fields
    product_url = StringField('Product URL', 
                            validators=[Optional(), URL()],
                            description='Enter URL of a product page to extract images')
    
    # File upload fields
    image_files = MultipleFileField('Upload Images',
                                 validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 
                                                                 'Image files only!')],
                                 description='Select multiple image files to upload')
    
    # Shopify import fields
    product_type_filter = StringField('Product Type Filter',
                                   validators=[Optional()],
                                   description='Filter Shopify products by type (e.g., "T-shirts")')
    
    include_all_variants = BooleanField('Include All Variant Images', default=True,
                                     description='Include images from all product variants')
    
    missing_alt_only = BooleanField('Only Products Missing Alt Text', default=True,
                                  description='Only process products with missing alt text')
    
    # Image search fields
    search_query = StringField('Search Query',
                             validators=[Optional()],
                             description='Keywords to search for product images (e.g., "blue denim jacket")')
    
    search_count = IntegerField('Number of Images',
                              validators=[Optional(), NumberRange(min=1, max=20)],
                              default=5,
                              description='Number of images to retrieve from search')
    
    # Output options
    output_format = SelectField('Output Format',
                              choices=[
                                  ('csv', 'CSV Export (for Shopify Import)'),
                                  ('shopify', 'Direct Update to Shopify Store'),
                                  ('library', 'Save to Image Library')
                              ],
                              default='csv')
    
    # Caption settings
    caption_style = SelectField('Caption Style',
                             choices=[
                                 ('descriptive', 'Descriptive (Detailed Product Description)'),
                                 ('seo', 'SEO-Optimized (Keyword Rich)'),
                                 ('minimal', 'Minimal (Short & Concise)'),
                                 ('technical', 'Technical (Feature-Focused)')
                             ],
                             default='descriptive')
    
    max_alt_length = IntegerField('Maximum Alt Text Length',
                                validators=[Optional(), NumberRange(min=50, max=250)],
                                default=125,
                                description='Maximum character length for alt text (recommended: 125)')
    
    include_keywords = BooleanField('Generate SEO Keywords', default=True,
                                  description='Extract key terms for SEO optimization')
    
    include_product_type = BooleanField('Suggest Product Category', default=True, 
                                      description='Have AI suggest product category based on image')
    
    generate_title = BooleanField('Generate Product Title', default=True,
                                description='Have AI suggest product names from images')
    
    shopify_tags = BooleanField('Generate Shopify Tags', default=True,
                              description='Create product tags based on image analysis')
    
    submit = SubmitField('Process Images')
