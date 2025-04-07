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