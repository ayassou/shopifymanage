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
