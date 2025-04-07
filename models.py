from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

class ShopifySettings(db.Model):
    """Model for Shopify API settings"""
    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    store_url = db.Column(db.String(255), nullable=False)
    api_version = db.Column(db.String(50), nullable=False, default='2023-07')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ShopifySettings {self.store_url}>'

class AISettings(db.Model):
    """Model for AI API settings"""
    id = db.Column(db.Integer, primary_key=True)
    api_provider = db.Column(db.String(50), nullable=False, default='openai')
    api_key = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<AISettings {self.api_provider}>'

class UploadHistory(db.Model):
    """Model for tracking product upload history"""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # CSV, XLSX, etc.
    record_count = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    settings_id = db.Column(db.Integer, db.ForeignKey('shopify_settings.id'), nullable=True)
    
    # Relationship with ShopifySettings
    settings = db.relationship('ShopifySettings', backref=db.backref('uploads', lazy=True))
    
    def __repr__(self):
        return f'<UploadHistory {self.filename} - {self.upload_date}>'

class ProductUploadResult(db.Model):
    """Model for storing individual product upload results"""
    id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey('upload_history.id'), nullable=False)
    shopify_product_id = db.Column(db.String(255), nullable=True)
    product_title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # success, error
    message = db.Column(db.Text, nullable=True)
    row_number = db.Column(db.Integer, nullable=True)
    
    # SEO fields
    meta_title = db.Column(db.String(255), nullable=True)
    meta_description = db.Column(db.Text, nullable=True)
    meta_keywords = db.Column(db.Text, nullable=True)
    url_handle = db.Column(db.String(255), nullable=True)
    category_hierarchy = db.Column(db.Text, nullable=True)
    
    # Relationship with UploadHistory
    upload = db.relationship('UploadHistory', backref=db.backref('results', lazy=True))
    
    def __repr__(self):
        return f'<ProductUploadResult {self.product_title} - {self.status}>'
        
        
class BlogPost(db.Model):
    """Model for storing blog posts generated by AI"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=True)
    featured_image_url = db.Column(db.String(1024), nullable=True)
    
    # Blog post metadata
    author = db.Column(db.String(100), nullable=True)
    publish_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(db.String(50), default='draft')  # draft, published, scheduled
    
    # SEO and categorization
    meta_title = db.Column(db.String(255), nullable=True)
    meta_description = db.Column(db.Text, nullable=True)
    meta_keywords = db.Column(db.Text, nullable=True)
    url_handle = db.Column(db.String(255), nullable=True)
    tags = db.Column(db.Text, nullable=True)  # Comma-separated tags
    category = db.Column(db.String(100), nullable=True)
    
    # Generation parameters (to facilitate regeneration)
    topic = db.Column(db.String(255), nullable=True)
    keywords = db.Column(db.Text, nullable=True)
    tone = db.Column(db.String(50), nullable=True)  # informative, casual, professional, etc.
    target_audience = db.Column(db.String(100), nullable=True)
    word_count = db.Column(db.Integer, nullable=True)
    
    # Shopify integration
    shopify_blog_id = db.Column(db.String(255), nullable=True)
    shopify_post_id = db.Column(db.String(255), nullable=True)
    settings_id = db.Column(db.Integer, db.ForeignKey('shopify_settings.id'), nullable=True)
    
    # Relationship with ShopifySettings
    settings = db.relationship('ShopifySettings', backref=db.backref('blog_posts', lazy=True))
    
    def __repr__(self):
        return f'<BlogPost {self.title} - {self.status}>'


class PageContent(db.Model):
    """Model for storing static page content generated by AI"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    page_type = db.Column(db.String(50), nullable=False)  # about, faq, contact, terms, privacy, etc.
    summary = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(1024), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published = db.Column(db.Boolean, default=False)
    publish_date = db.Column(db.DateTime, nullable=True)
    
    # SEO fields
    meta_title = db.Column(db.String(255), nullable=True)
    meta_description = db.Column(db.Text, nullable=True)
    meta_keywords = db.Column(db.Text, nullable=True)
    url_handle = db.Column(db.String(255), nullable=True)
    
    # Generation parameters
    company_name = db.Column(db.String(255), nullable=True)
    company_description = db.Column(db.Text, nullable=True)
    industry = db.Column(db.String(100), nullable=True)
    founding_year = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(255), nullable=True)
    values = db.Column(db.Text, nullable=True)  # Comma-separated values
    tone = db.Column(db.String(50), nullable=True)  # professional, friendly, casual, etc.
    target_audience = db.Column(db.String(100), nullable=True)
    
    # For FAQ pages
    faq_items = db.Column(db.Text, nullable=True)  # JSON string of Q&A pairs
    faq_topics = db.Column(db.Text, nullable=True)  # Topics used to generate FAQs
    
    # For contact pages
    contact_email = db.Column(db.String(255), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    contact_address = db.Column(db.Text, nullable=True)
    social_media = db.Column(db.Text, nullable=True)  # JSON string of social media links
    
    # Performance metrics
    generation_time = db.Column(db.Float, nullable=True)  # Time taken to generate content in seconds
    
    # Original generation parameters (for regeneration)
    parameters = db.Column(db.Text, nullable=True)  # JSON string of all parameters used
    
    # Shopify page information
    shopify_page_id = db.Column(db.String(255), nullable=True)
    settings_id = db.Column(db.Integer, db.ForeignKey('shopify_settings.id'), nullable=True)
    
    settings = db.relationship('ShopifySettings', backref=db.backref('pages', lazy=True))
    
    def __repr__(self):
        return f'<PageContent {self.title} - {self.page_type}>'


class ImageBatch(db.Model):
    """Model for storing image batch information for caption generation"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)  # User-defined batch name
    source_type = db.Column(db.String(50), nullable=False)  # url, upload, shopify, search
    source_detail = db.Column(db.Text, nullable=True)  # URL, search terms, or other source info
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Batch status tracking
    status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    processed_count = db.Column(db.Integer, default=0)
    total_count = db.Column(db.Integer, default=0)
    
    # Export information
    export_format = db.Column(db.String(50), nullable=True)  # csv, shopify_update, json
    export_path = db.Column(db.String(1024), nullable=True)  # File path for exported data
    
    # Shopify integration
    settings_id = db.Column(db.Integer, db.ForeignKey('shopify_settings.id'), nullable=True)
    settings = db.relationship('ShopifySettings', backref=db.backref('image_batches', lazy=True))
    
    def __repr__(self):
        return f'<ImageBatch {self.name} - {self.source_type}>'


class ImageItem(db.Model):
    """Model for storing individual image information and generated captions"""
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('image_batch.id'), nullable=False)
    
    # Image information
    filename = db.Column(db.String(255), nullable=True)
    url = db.Column(db.String(1024), nullable=True)
    file_path = db.Column(db.String(1024), nullable=True)  # Local path for uploaded images
    mimetype = db.Column(db.String(100), nullable=True)
    filesize = db.Column(db.Integer, nullable=True)  # in bytes
    
    # Generated data
    alt_text = db.Column(db.String(255), nullable=True)
    caption = db.Column(db.Text, nullable=True)
    tags = db.Column(db.Text, nullable=True)  # Comma-separated tags
    detailed_description = db.Column(db.Text, nullable=True)  # Longer, more detailed description
    
    # SEO data
    seo_keywords = db.Column(db.Text, nullable=True)
    seo_title = db.Column(db.String(255), nullable=True)
    
    # Product association
    product_suggested_name = db.Column(db.String(255), nullable=True)
    product_category = db.Column(db.String(100), nullable=True)
    
    # Processing status
    status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    error_message = db.Column(db.Text, nullable=True)
    
    # Shopify specific information
    shopify_product_id = db.Column(db.String(255), nullable=True)
    shopify_image_id = db.Column(db.String(255), nullable=True)
    shopify_updated = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship with ImageBatch
    batch = db.relationship('ImageBatch', backref=db.backref('images', lazy=True))
    
    def __repr__(self):
        return f'<ImageItem {self.filename or self.url[:30]}>'