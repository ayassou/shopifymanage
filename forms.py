from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
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
