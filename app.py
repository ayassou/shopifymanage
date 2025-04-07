import os
import logging
import time
import json
import tempfile
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, Response, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
from forms import UploadForm, ShopifySettingsForm, AISettingsForm, AIGeneratorForm, BlogPostGeneratorForm, PageGeneratorForm, ImageCaptionGeneratorForm
from data_processor import process_data, validate_data
from shopify_client import ShopifyClient
from ai_service import AIService
from web_scraper import ProductScraper
from models import db, ShopifySettings, AISettings, UploadHistory, ProductUploadResult, BlogPost, PageContent, ImageBatch, ImageItem
from models import TrendAnalysis, ProductSource, ProductEvaluation, NicheAnalysis, AgentTask
from models import StoreSetup, StorePage, StoreProduct, ThemeCustomization
from agents import DropshippingAgent, StoreAgent

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create a Blueprint instead of a Flask app
app = Blueprint('main', __name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

# Temporary storage for uploaded files
UPLOAD_FOLDER = '/tmp'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    # Get upload history for display on the dashboard
    recent_uploads = UploadHistory.query.order_by(UploadHistory.upload_date.desc()).limit(5).all()
    return render_template('index.html', recent_uploads=recent_uploads)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    form = ShopifySettingsForm()
    
    # Get the active settings from the database if they exist
    active_settings = ShopifySettings.query.filter_by(is_active=True).first()
    
    if form.validate_on_submit():
        # Create new settings or update existing ones
        if active_settings:
            active_settings.api_key = form.api_key.data
            active_settings.password = form.password.data
            active_settings.store_url = form.store_url.data
            active_settings.api_version = form.api_version.data
            active_settings.last_used_at = datetime.utcnow()
            db.session.commit()
        else:
            new_settings = ShopifySettings(
                api_key=form.api_key.data,
                password=form.password.data,
                store_url=form.store_url.data,
                api_version=form.api_version.data
            )
            db.session.add(new_settings)
            db.session.commit()
        
        flash('Shopify settings saved successfully!', 'success')
        return redirect(url_for('settings'))
    
    # Pre-fill the form with existing settings if available
    if active_settings:
        form.api_key.data = active_settings.api_key
        form.password.data = active_settings.password
        form.store_url.data = active_settings.store_url
        form.api_version.data = active_settings.api_version
    
    return render_template('settings.html', form=form)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # Check if Shopify settings exist in the database
    active_settings = ShopifySettings.query.filter_by(is_active=True).first()
    if not active_settings:
        flash('Please configure your Shopify API settings first.', 'warning')
        return redirect(url_for('main.settings'))
    
    form = UploadForm()
    
    if form.validate_on_submit():
        file = form.file.data
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            try:
                # Process the file based on its extension
                file_type = filename.rsplit('.', 1)[1].lower()
                if file_type == 'csv':
                    df = pd.read_csv(filepath)
                else:  # Excel file
                    df = pd.read_excel(filepath)
                
                # Validate the data
                validation_result = validate_data(df)
                if not validation_result['valid']:
                    flash(f"Data validation failed: {validation_result['errors']}", 'danger')
                    return render_template('upload.html', form=form)
                
                # Create an upload history record
                upload_history = UploadHistory(
                    filename=filename,
                    file_type=file_type,
                    record_count=len(df),
                    settings_id=active_settings.id
                )
                db.session.add(upload_history)
                db.session.commit()
                
                # Store data for processing
                session['file_path'] = filepath
                session['upload_id'] = upload_history.id
                
                # Process the data and upload to Shopify
                return redirect(url_for('main.process'))
                
            except Exception as e:
                logger.error(f"Error processing file: {str(e)}")
                flash(f'Error processing file: {str(e)}', 'danger')
                return render_template('upload.html', form=form)
        else:
            flash('Invalid file. Please upload a CSV or Excel file.', 'danger')
    
    return render_template('upload.html', form=form)

@app.route('/process')
def process():
    # Check if file path exists in session
    if 'file_path' not in session or 'upload_id' not in session:
        flash('No file uploaded. Please upload a file first.', 'warning')
        return redirect(url_for('main.upload'))
    
    # Get the upload history record
    upload_id = session.get('upload_id')
    upload_history = UploadHistory.query.get(upload_id)
    if not upload_history:
        flash('Upload record not found. Please try again.', 'danger')
        return redirect(url_for('main.upload'))
    
    # Get the Shopify settings
    active_settings = ShopifySettings.query.get(upload_history.settings_id)
    if not active_settings:
        flash('Shopify settings not found. Please configure your settings first.', 'danger')
        return redirect(url_for('main.settings'))
    
    # Initialize Shopify client
    shopify_client = ShopifyClient(
        active_settings.api_key,
        active_settings.password,
        active_settings.store_url,
        active_settings.api_version
    )
    
    try:
        # Read the file
        file_path = session['file_path']
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:  # Excel file
            df = pd.read_excel(file_path)
        
        # Process and upload the data to Shopify
        results = process_data(df, shopify_client)
        
        # Update the upload history with success/error counts
        success_count = sum(1 for result in results if result['status'] == 'success')
        error_count = sum(1 for result in results if result['status'] == 'error')
        
        upload_history.success_count = success_count
        upload_history.error_count = error_count
        db.session.commit()
        
        # Store the results in the database
        for result in results:
            row_number = result.get('row', 0)
            row_index = row_number - 2  # Adjust for 0-indexing and header
            
            # Extract SEO data from the row if it exists
            seo_data = {}
            if 0 <= row_index < len(df):
                row_data = df.iloc[row_index]
                seo_data = {
                    'meta_title': row_data.get('meta_title', None),
                    'meta_description': row_data.get('meta_description', None),
                    'meta_keywords': row_data.get('meta_keywords', None),
                    'url_handle': row_data.get('url_handle', None),
                    'category_hierarchy': row_data.get('category_hierarchy', None)
                }
            
            # Create a product upload result record
            product_result = ProductUploadResult(
                upload_id=upload_id,
                product_title=result.get('product_title', 'Unknown'),
                status=result.get('status', 'unknown'),
                message=result.get('message', ''),
                row_number=row_number,
                shopify_product_id=result.get('product_id', None),
                meta_title=seo_data.get('meta_title'),
                meta_description=seo_data.get('meta_description'),
                meta_keywords=seo_data.get('meta_keywords'),
                url_handle=seo_data.get('url_handle'),
                category_hierarchy=seo_data.get('category_hierarchy')
            )
            db.session.add(product_result)
        
        db.session.commit()
        
        # Clean up session data
        session.pop('file_path', None)
        session.pop('upload_id', None)
        
        # Render the results page
        return render_template('results.html', results=results, upload=upload_history)
        
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        flash(f'Error processing data: {str(e)}', 'danger')
        return redirect(url_for('main.upload'))

@app.route('/ai/settings', methods=['GET', 'POST'])
def ai_settings():
    """Route for configuring AI API settings"""
    form = AISettingsForm()
    
    # Get the active AI settings from the database if they exist
    active_settings = AISettings.query.filter_by(is_active=True).first()
    
    if form.validate_on_submit():
        # Create new settings or update existing ones
        if active_settings:
            active_settings.api_provider = form.api_provider.data
            active_settings.api_key = form.api_key.data
            active_settings.last_used_at = datetime.utcnow()
            db.session.commit()
        else:
            new_settings = AISettings(
                api_provider=form.api_provider.data,
                api_key=form.api_key.data
            )
            db.session.add(new_settings)
            db.session.commit()
        
        flash('AI API settings saved successfully!', 'success')
        return redirect(url_for('ai_settings'))
    
    # Pre-fill the form with existing settings if available
    if active_settings:
        form.api_provider.data = active_settings.api_provider
        form.api_key.data = active_settings.api_key
    
    return render_template('ai_settings.html', form=form, ai_settings=active_settings)

@app.route('/ai/generator', methods=['GET', 'POST'])
def ai_generator():
    """Route for the AI product generator"""
    # Check if AI settings exist in the database
    active_settings = AISettings.query.filter_by(is_active=True).first()
    form = AIGeneratorForm()
    
    if form.validate_on_submit():
        if not active_settings:
            flash('Please configure your AI API settings first.', 'warning')
            return redirect(url_for('main.ai_settings'))
        
        try:
            # Initialize the AI Service
            ai_service = AIService(api_key=active_settings.api_key, 
                                 api_provider=active_settings.api_provider)
            
            # Record the start time for performance tracking
            start_time = time.time()
            
            # Process the input based on the selected type
            input_type = form.input_type.data
            
            # For URL input
            if input_type == 'url':
                product_url = form.product_url.data
                if not product_url:
                    flash('Please enter a product URL.', 'warning')
                    return render_template('ai_generator.html', form=form, ai_settings=active_settings)
                
                # Store image URLs if extraction is enabled
                image_urls = []
                if form.extract_images.data:
                    # Create a product scraper instance
                    scraper = ProductScraper()
                    try:
                        image_urls = scraper.extract_product_images(product_url)
                    except Exception as e:
                        logger.warning(f"Failed to extract images from {product_url}: {str(e)}")
                
                # Generate product data from URL
                result = ai_service.generate_product_data(
                    input_type='url',
                    input_data=product_url,
                    num_variants=form.variant_count.data
                )
                
                # Add the extracted image URLs to the result
                if image_urls:
                    result['csv_data']['image_urls'] = image_urls
            
            # For text description input
            elif input_type == 'text':
                product_description = form.product_description.data
                if not product_description:
                    flash('Please enter a product description.', 'warning')
                    return render_template('ai_generator.html', form=form, ai_settings=active_settings)
                
                # Generate product data from text description
                result = ai_service.generate_product_data(
                    input_type='text',
                    input_data=product_description,
                    num_variants=form.variant_count.data
                )
            
            # For partial data input
            elif input_type == 'partial_data':
                # Collect the partial data from the form
                partial_data = {
                    'product_title': form.product_title.data,
                    'price': form.price.data,
                    'vendor': form.vendor.data,
                    'product_type': form.product_type.data
                }
                
                # Remove empty values
                partial_data = {k: v for k, v in partial_data.items() if v}
                
                if not partial_data:
                    flash('Please provide at least one product detail.', 'warning')
                    return render_template('ai_generator.html', form=form, ai_settings=active_settings)
                
                # Generate product data from partial data
                result = ai_service.generate_product_data(
                    input_type='partial_data',
                    input_data=partial_data,
                    num_variants=form.variant_count.data
                )
            
            # Calculate generation time
            generation_time = time.time() - start_time
            
            # Extract generated data
            csv_data = result['csv_data']
            
            # Store the data in the session for preview and download
            # Convert DataFrame to CSV string and store in session
            csv_string = csv_data.to_csv(index=False)
            
            # Create a temporary file with the CSV data
            temp_csv_fd, temp_csv_path = tempfile.mkstemp(suffix='.csv')
            with os.fdopen(temp_csv_fd, 'w') as f:
                f.write(csv_string)
            
            # Store paths and metadata in session
            session['ai_generated_csv_path'] = temp_csv_path
            session['ai_generated_product_data'] = json.dumps(result, default=str)
            session['ai_generation_stats'] = {
                'product_count': result.get('product_count', 1),
                'variant_count': result.get('variant_count', 0),
                'image_count': result.get('image_count', 0),
                'generation_time': generation_time
            }
            
            # If image URLs were extracted, store them in the session
            if 'image_urls' in result:
                session['ai_generated_image_urls'] = result['image_urls']
            
            # Redirect to the preview page
            return redirect(url_for('main.ai_preview'))
            
        except Exception as e:
            logger.error(f"Error generating product data: {str(e)}")
            flash(f'Error generating product data: {str(e)}', 'danger')
            return render_template('ai_generator.html', form=form, ai_settings=active_settings)
    
    return render_template('ai_generator.html', form=form, ai_settings=active_settings)

@app.route('/ai/preview')
def ai_preview():
    """Route for previewing AI-generated product data"""
    # Check if AI settings exist in the database
    active_settings = AISettings.query.filter_by(is_active=True).first()
    
    # Check if generated data exists in the session
    if 'ai_generated_product_data' not in session:
        flash('No generated data found. Please generate product data first.', 'warning')
        return redirect(url_for('main.ai_generator'))
    
    try:
        # Load the generated data from the session
        product_data = json.loads(session['ai_generated_product_data'])
        
        # Get the CSV path
        csv_path = session.get('ai_generated_csv_path')
        if not csv_path or not os.path.exists(csv_path):
            flash('CSV file not found. Please generate product data again.', 'warning')
            return redirect(url_for('main.ai_generator'))
        
        # Read the CSV file for preview
        df = pd.read_csv(csv_path)
        
        # Prepare CSV preview data (first 5 rows)
        csv_preview = df.head(5).values.tolist()
        csv_columns = df.columns.tolist()
        
        # Get generation stats
        generation_stats = session.get('ai_generation_stats', {
            'product_count': 1,
            'variant_count': 0,
            'image_count': 0,
            'generation_time': 0
        })
        
        # Get image URLs if available
        image_urls = session.get('ai_generated_image_urls', [])
        
        return render_template('ai_preview.html', 
                               product_data=product_data,
                               csv_preview=csv_preview,
                               csv_columns=csv_columns,
                               generation_stats=generation_stats,
                               image_urls=image_urls,
                               ai_settings=active_settings)
    except Exception as e:
        logger.error(f"Error previewing generated data: {str(e)}")
        flash(f'Error previewing generated data: {str(e)}', 'danger')
        return redirect(url_for('main.ai_generator'))

@app.route('/ai/download_csv')
def download_generated_csv():
    """Route for downloading the AI-generated CSV file"""
    # Check if CSV path exists in session
    if 'ai_generated_csv_path' not in session:
        flash('No generated CSV found. Please generate product data first.', 'warning')
        return redirect(url_for('main.ai_generator'))
    
    csv_path = session.get('ai_generated_csv_path')
    if not csv_path or not os.path.exists(csv_path):
        flash('CSV file not found. Please generate product data again.', 'warning')
        return redirect(url_for('main.ai_generator'))
    
    try:
        # Generate a filename based on the product data
        if 'ai_generated_product_data' in session:
            product_data = json.loads(session['ai_generated_product_data'])
            product_title = product_data.get('product_title', 'product').lower()
            # Clean up product title for filename
            filename = f"{product_title.replace(' ', '_')[:30]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            filename = f"shopify_product_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Send the file to the client
        return send_file(csv_path, 
                        mimetype='text/csv',
                        as_attachment=True,
                        download_name=filename)
    except Exception as e:
        logger.error(f"Error downloading CSV: {str(e)}")
        flash(f'Error downloading CSV: {str(e)}', 'danger')
        return redirect(url_for('main.ai_preview'))

@app.route('/ai/upload_to_shopify')
def upload_generated_product():
    """Route for uploading the AI-generated product to Shopify"""
    # Check if CSV path exists in session
    if 'ai_generated_csv_path' not in session:
        flash('No generated data found. Please generate product data first.', 'warning')
        return redirect(url_for('main.ai_generator'))
    
    # Check if Shopify settings exist in the database
    active_settings = ShopifySettings.query.filter_by(is_active=True).first()
    if not active_settings:
        flash('Please configure your Shopify API settings first.', 'warning')
        return redirect(url_for('main.settings'))
    
    try:
        # Get the CSV path
        csv_path = session.get('ai_generated_csv_path')
        if not csv_path or not os.path.exists(csv_path):
            flash('CSV file not found. Please generate product data again.', 'warning')
            return redirect(url_for('main.ai_generator'))
        
        # Read the CSV file
        df = pd.read_csv(csv_path)
        
        # Create an upload history record
        upload_history = UploadHistory(
            filename="AI_Generated_Product.csv",
            file_type="csv",
            record_count=len(df),
            settings_id=active_settings.id
        )
        db.session.add(upload_history)
        db.session.commit()
        
        # Initialize Shopify client
        shopify_client = ShopifyClient(
            active_settings.api_key,
            active_settings.password,
            active_settings.store_url,
            active_settings.api_version
        )
        
        # Process and upload the data to Shopify
        results = process_data(df, shopify_client)
        
        # Update the upload history with success/error counts
        success_count = sum(1 for result in results if result['status'] == 'success')
        error_count = sum(1 for result in results if result['status'] == 'error')
        
        upload_history.success_count = success_count
        upload_history.error_count = error_count
        db.session.commit()
        
        # Store the results in the database
        upload_id = upload_history.id
        for result in results:
            row_number = result.get('row', 0)
            row_index = row_number - 2  # Adjust for 0-indexing and header
            
            # Extract SEO data from the row if it exists
            seo_data = {}
            if 0 <= row_index < len(df):
                row_data = df.iloc[row_index]
                seo_data = {
                    'meta_title': row_data.get('meta_title', None),
                    'meta_description': row_data.get('meta_description', None),
                    'meta_keywords': row_data.get('meta_keywords', None),
                    'url_handle': row_data.get('url_handle', None),
                    'category_hierarchy': row_data.get('category_hierarchy', None)
                }
            
            # Create a product upload result record
            product_result = ProductUploadResult(
                upload_id=upload_id,
                product_title=result.get('product_title', 'Unknown'),
                status=result.get('status', 'unknown'),
                message=result.get('message', ''),
                row_number=row_number,
                shopify_product_id=result.get('product_id', None),
                meta_title=seo_data.get('meta_title'),
                meta_description=seo_data.get('meta_description'),
                meta_keywords=seo_data.get('meta_keywords'),
                url_handle=seo_data.get('url_handle'),
                category_hierarchy=seo_data.get('category_hierarchy')
            )
            db.session.add(product_result)
        
        db.session.commit()
        
        # Clear the AI-generated data from session
        session.pop('ai_generated_csv_path', None)
        session.pop('ai_generated_product_data', None)
        session.pop('ai_generation_stats', None)
        session.pop('ai_generated_image_urls', None)
        
        # Render the results page
        return render_template('results.html', results=results, upload=upload_history)
        
    except Exception as e:
        logger.error(f"Error uploading generated product to Shopify: {str(e)}")
        flash(f'Error uploading to Shopify: {str(e)}', 'danger')
        return redirect(url_for('main.ai_preview'))

@app.route('/ai/regenerate')
def regenerate_product():
    """Route for regenerating product data with different parameters"""
    # Simply redirect to the generator page
    # The user will need to input their parameters again
    flash('Please adjust your parameters and generate new product data.', 'info')
    return redirect(url_for('main.ai_generator'))

# Blog Post Generator Routes

@app.route('/blog/generator', methods=['GET', 'POST'])
def blog_generator():
    """Route for the AI blog post generator"""
    # Check if AI settings exist in the database
    active_settings = AISettings.query.filter_by(is_active=True).first()
    form = BlogPostGeneratorForm()
    
    # Get blog post statistics for the sidebar
    stats = {
        'total_posts': BlogPost.query.count(),
        'published_posts': BlogPost.query.filter_by(status='published').count(),
        'draft_posts': BlogPost.query.filter_by(status='draft').count()
    }
    
    if form.validate_on_submit():
        if not active_settings:
            flash('Please configure your AI API settings first.', 'warning')
            return redirect(url_for('main.ai_settings'))
        
        try:
            # Initialize the AI Service
            ai_service = AIService(api_key=active_settings.api_key, 
                                 api_provider=active_settings.api_provider)
            
            # Record the start time for performance tracking
            start_time = time.time()
            
            # Extract form data
            blog_params = {
                'title': form.title.data,
                'topic': form.topic.data,
                'keywords': form.keywords.data,
                'content_type': form.content_type.data,
                'tone': form.tone.data,
                'target_audience': form.target_audience.data,
                'word_count': form.word_count.data or 1000,
                'include_sections': form.include_sections.data,
                'include_faq': form.include_faq.data,
                'include_cta': form.include_cta.data,
                'reference_products': form.reference_products.data,
                'seo_optimize': form.seo_optimize.data
            }
            
            # Generate the blog post content
            blog_data = ai_service.generate_blog_post(blog_params)
            
            # Generate featured image if requested
            if form.generate_image.data:
                featured_image_url = ai_service.generate_blog_image(
                    blog_data.get('title', ''), 
                    blog_data.get('summary', '')
                )
                if featured_image_url:
                    blog_data['featured_image_url'] = featured_image_url
            
            # Create a new BlogPost record in the database
            blog_post = BlogPost(
                title=blog_data.get('title', ''),
                content=blog_data.get('content', ''),
                summary=blog_data.get('summary', ''),
                featured_image_url=blog_data.get('featured_image_url'),
                status='draft',
                meta_title=blog_data.get('meta_title', ''),
                meta_description=blog_data.get('meta_description', ''),
                meta_keywords=blog_data.get('meta_keywords', ''),
                url_handle=blog_data.get('url_handle', ''),
                tags=','.join(blog_data.get('tags', [])) if isinstance(blog_data.get('tags'), list) else blog_data.get('tags', ''),
                category=blog_data.get('category', ''),
                topic=form.topic.data,
                keywords=form.keywords.data,
                tone=form.tone.data,
                target_audience=form.target_audience.data,
                word_count=form.word_count.data,
                created_at=datetime.utcnow()
            )
            
            db.session.add(blog_post)
            db.session.commit()
            
            # Store generation metadata
            generation_time = time.time() - start_time
            
            # Store blog data in session for display
            session['blog_post_id'] = blog_post.id
            session['blog_generation_time'] = generation_time
            session['blog_generation_stats'] = {
                'word_count': blog_data.get('word_count', form.word_count.data or 1000),
                'estimated_reading_time': blog_data.get('estimated_reading_time', 5),
                'has_featured_image': bool(blog_data.get('featured_image_url')),
                'generation_time': generation_time
            }
            
            # Redirect to the preview page
            return redirect(url_for('main.blog_preview', post_id=blog_post.id))
            
        except Exception as e:
            logger.error(f"Error generating blog post: {str(e)}")
            flash(f'Error generating blog post: {str(e)}', 'danger')
            return render_template('blog_generator.html', form=form, stats=stats)
    
    return render_template('blog_generator.html', form=form, stats=stats)

@app.route('/blog/preview/<int:post_id>')
def blog_preview(post_id):
    """Route for previewing the AI-generated blog post"""
    # Retrieve the blog post from the database
    blog_post = BlogPost.query.get_or_404(post_id)
    
    # Get generation stats from session if available
    generation_stats = session.get('blog_generation_stats', {})
    
    return render_template('blog_preview.html', 
                          blog_post=blog_post, 
                          generation_stats=generation_stats)

@app.route('/blog/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_blog_post(post_id):
    """Route for editing a blog post before publishing"""
    # Retrieve the blog post from the database
    blog_post = BlogPost.query.get_or_404(post_id)
    
    # Todo: Implement the edit page
    # For now, redirect to preview
    flash('Blog post editing will be implemented in the next update.', 'info')
    return redirect(url_for('main.blog_preview', post_id=post_id))

@app.route('/blog/publish/<int:post_id>')
def publish_blog_post(post_id):
    """Route for publishing the blog post to Shopify"""
    # Retrieve the blog post from the database
    blog_post = BlogPost.query.get_or_404(post_id)
    
    # Check if Shopify settings exist
    active_settings = ShopifySettings.query.filter_by(is_active=True).first()
    if not active_settings:
        flash('Please configure your Shopify API settings first.', 'warning')
        return redirect(url_for('main.settings'))
    
    try:
        # Initialize Shopify client
        shopify_client = ShopifyClient(
            active_settings.api_key,
            active_settings.password,
            active_settings.store_url,
            active_settings.api_version
        )
        
        # First, check if we need to get the blog ID or if already have it
        blog_id = None
        if blog_post.shopify_blog_id:
            blog_id = blog_post.shopify_blog_id
        else:
            # Get available blogs from the shop
            blogs_response = shopify_client.get_blogs()
            
            if blogs_response and 'blogs' in blogs_response and blogs_response['blogs']:
                # Use the first blog by default
                blog_id = blogs_response['blogs'][0]['id']
                
                # Or try to find a blog with a name that contains 'blog', 'news', or 'article'
                for blog in blogs_response['blogs']:
                    blog_title = blog.get('title', '').lower()
                    if 'blog' in blog_title or 'news' in blog_title or 'article' in blog_title:
                        blog_id = blog['id']
                        break
            
            # If no blogs found, create one
            if not blog_id:
                new_blog_data = {
                    'blog': {
                        'title': 'Store Blog',
                        'commentable': 'moderate'
                    }
                }
                blog_response = shopify_client.create_blog(new_blog_data)
                if blog_response and 'blog' in blog_response:
                    blog_id = blog_response['blog']['id']
                else:
                    raise Exception("Failed to create a blog in Shopify")
        
        # Prepare the article data
        article_data = {
            'article': {
                'title': blog_post.title,
                'author': blog_post.author or 'Store Admin',
                'body_html': blog_post.content,
                'published': True,
                'published_at': blog_post.publish_date.isoformat() if blog_post.publish_date else datetime.utcnow().isoformat(),
                'summary_html': blog_post.summary or '',
                'tags': blog_post.tags or '',
                'handle': blog_post.url_handle or None,
                'metafields': []
            }
        }
        
        # Add metafields for SEO if available
        if blog_post.meta_title:
            article_data['article']['metafields'].append({
                'namespace': 'global',
                'key': 'title_tag',
                'value': blog_post.meta_title,
                'type': 'single_line_text_field'
            })
            
        if blog_post.meta_description:
            article_data['article']['metafields'].append({
                'namespace': 'global',
                'key': 'description_tag',
                'value': blog_post.meta_description,
                'type': 'single_line_text_field'
            })
        
        # Add featured image if available
        if blog_post.featured_image_url:
            article_data['article']['image'] = {
                'src': blog_post.featured_image_url
            }
        
        # Create or update the article in Shopify
        if blog_post.shopify_post_id:
            # Update existing post
            response = shopify_client.update_article(
                blog_id, 
                blog_post.shopify_post_id, 
                article_data
            )
        else:
            # Create new post
            response = shopify_client.create_article(blog_id, article_data)
        
        # Update local data with Shopify IDs
        if response and 'article' in response:
            blog_post.shopify_blog_id = str(blog_id)
            blog_post.shopify_post_id = str(response['article']['id'])
            blog_post.status = 'published'
            blog_post.publish_date = datetime.utcnow()
            blog_post.settings_id = active_settings.id
            db.session.commit()
            
            flash('Blog post published to Shopify successfully!', 'success')
        else:
            raise Exception("Failed to publish article to Shopify")
        
        return redirect(url_for('main.blog_preview', post_id=post_id))
        
    except Exception as e:
        logger.error(f"Error publishing blog post to Shopify: {str(e)}")
        flash(f'Error publishing to Shopify: {str(e)}', 'danger')
        return redirect(url_for('main.blog_preview', post_id=post_id))

@app.route('/blog/regenerate/<int:post_id>')
def regenerate_blog_post(post_id=None):
    """Route for regenerating a blog post with different parameters"""
    # If a post ID is provided, store its parameters for pre-filling the form
    if post_id:
        blog_post = BlogPost.query.get_or_404(post_id)
        # Todo: Store parameters in session for pre-filling the form
    
    # Redirect to the generator page
    flash('Please adjust your parameters and generate a new blog post.', 'info')
    return redirect(url_for('main.blog_generator'))

# Page Content Generator Routes
@app.route('/page/generator', methods=['GET', 'POST'])
def page_generator():
    """Route for the page content generator form"""
    # Check if AI settings exist in the database
    active_settings = AISettings.query.filter_by(is_active=True).first()
    form = PageGeneratorForm()
    
    if form.validate_on_submit():
        if not active_settings:
            flash('Please configure your AI API settings first.', 'warning')
            return redirect(url_for('main.ai_settings'))
        
        try:
            # Initialize the AI Service
            ai_service = AIService(api_key=active_settings.api_key, 
                                  api_provider=active_settings.api_provider)
            
            # Record the start time for performance tracking
            start_time = time.time()
            
            # Collect all form data into a dictionary
            page_params = {
                'page_type': form.page_type.data,
                'title': form.title.data,
                'company_name': form.company_name.data,
                'company_description': form.company_description.data,
                'industry': form.industry.data,
                'founding_year': form.founding_year.data,
                'location': form.location.data,
                'values': form.values.data,
                'contact_email': form.contact_email.data,
                'contact_phone': form.contact_phone.data,
                'contact_address': form.contact_address.data,
                'social_media': form.social_media.data,
                'faq_topics': form.faq_topics.data,
                'tone': form.tone.data,
                'target_audience': form.target_audience.data,
                'seo_optimize': form.seo_optimize.data,
                'generate_image': form.generate_image.data
            }
            
            # Generate page content
            result = ai_service.generate_page_content(page_params)
            
            # Calculate generation time
            generation_time = time.time() - start_time
            
            # Create a new PageContent record
            page_content = PageContent(
                page_type=page_params['page_type'],
                title=result.get('title', ''),
                content=result.get('content', ''),
                meta_title=result.get('meta_title', ''),
                meta_description=result.get('meta_description', ''),
                meta_keywords=result.get('meta_keywords', ''),
                published=False,
                generation_time=generation_time,
                image_url=result.get('image_url', '')
            )
            
            # Save the original parameters as JSON for potential regeneration
            page_content.parameters = json.dumps(page_params)
            
            # Save to database
            db.session.add(page_content)
            db.session.commit()
            
            # Redirect to the preview page
            return redirect(url_for('main.page_preview', page_id=page_content.id))
            
        except Exception as e:
            logger.error(f"Error generating page content: {str(e)}")
            flash(f'Error generating page content: {str(e)}', 'danger')
    
    return render_template('page_generator.html', form=form, ai_settings=active_settings)

@app.route('/page/preview/<int:page_id>')
def page_preview(page_id):
    """Route for previewing generated page content"""
    # Get the page content record
    page_content = PageContent.query.get_or_404(page_id)
    
    # Check if shopify settings exist for the publish button
    has_shopify_settings = ShopifySettings.query.filter_by(is_active=True).first() is not None
    
    return render_template('page_preview.html', 
                          page=page_content, 
                          has_shopify_settings=has_shopify_settings)

@app.route('/page/publish/<int:page_id>')
def publish_page(page_id):
    """Route for publishing a page to Shopify"""
    # Get the page content record
    page_content = PageContent.query.get_or_404(page_id)
    
    # Get the Shopify settings
    active_settings = ShopifySettings.query.filter_by(is_active=True).first()
    if not active_settings:
        flash('Please configure your Shopify API settings first.', 'warning')
        return redirect(url_for('main.settings'))
    
    try:
        # Initialize Shopify client
        shopify_client = ShopifyClient(
            active_settings.api_key,
            active_settings.password,
            active_settings.store_url,
            active_settings.api_version
        )
        
        # Create page data for Shopify
        page_data = {
            'title': page_content.title,
            'body_html': page_content.content,
            'published': True,
            'metafields': [
                {
                    'namespace': 'global',
                    'key': 'title_tag',
                    'value': page_content.meta_title,
                    'type': 'single_line_text_field'
                },
                {
                    'namespace': 'global',
                    'key': 'description_tag',
                    'value': page_content.meta_description,
                    'type': 'single_line_text_field'
                }
            ]
        }
        
        # Publish to Shopify
        result = shopify_client.create_page(page_data)
        
        # Update the page record with Shopify page ID and published status
        page_content.shopify_page_id = result.get('id')
        page_content.published = True
        page_content.publish_date = datetime.utcnow()
        db.session.commit()
        
        flash('Page successfully published to Shopify!', 'success')
        return redirect(url_for('main.page_preview', page_id=page_id))
        
    except Exception as e:
        logger.error(f"Error publishing page to Shopify: {str(e)}")
        flash(f'Error publishing to Shopify: {str(e)}', 'danger')
        return redirect(url_for('main.page_preview', page_id=page_id))

@app.route('/page/regenerate/<int:page_id>')
def regenerate_page(page_id=None):
    """Route for regenerating a page with different parameters"""
    # If a page ID is provided, store its parameters for pre-filling the form
    if page_id:
        page = PageContent.query.get_or_404(page_id)
        # Todo: Store parameters in session for pre-filling the form
    
    # Redirect to the generator page
    flash('Please adjust your parameters and generate a new page.', 'info')
    return redirect(url_for('main.page_generator'))

# Image Caption Generator Routes
@app.route('/image-captions/generator', methods=['GET', 'POST'])
def image_caption_generator():
    """Route for the Image Caption Generator form"""
    # Check if AI settings exist in the database
    active_ai_settings = AISettings.query.filter_by(is_active=True).first()
    
    # Check if Shopify settings exist for Shopify integration options
    has_shopify_settings = ShopifySettings.query.filter_by(is_active=True).first() is not None
    
    form = ImageCaptionGeneratorForm()
    
    if form.validate_on_submit():
        if not active_ai_settings:
            flash('Please configure your AI API settings first.', 'warning')
            return redirect(url_for('main.ai_settings'))
        
        try:
            # Create a new batch record
            batch = ImageBatch(
                name=form.batch_name.data,
                source_type=form.source_type.data,
                source_detail=form.source_detail.data if form.source_detail.data else None,
                status='pending',
                export_format=form.export_format.data
            )
            
            # If Shopify is involved, add Shopify settings reference
            if form.source_type.data == 'shopify' or form.export_format.data == 'shopify_update':
                shopify_settings = ShopifySettings.query.filter_by(is_active=True).first()
                if not shopify_settings:
                    flash('Shopify settings are required for this operation.', 'warning')
                    return render_template('image_caption_generator.html', form=form, 
                                          ai_settings=active_ai_settings,
                                          has_shopify_settings=has_shopify_settings)
                batch.settings_id = shopify_settings.id
            
            db.session.add(batch)
            db.session.commit()
            
            # Process based on source type
            if form.source_type.data == 'url':
                # Process URL input - can be a single URL or multiple URLs
                urls = form.source_detail.data.strip().split('\n')
                urls = [url.strip() for url in urls if url.strip()]
                
                if not urls:
                    flash('Please provide at least one valid URL.', 'warning')
                    db.session.delete(batch)
                    db.session.commit()
                    return render_template('image_caption_generator.html', form=form, 
                                          ai_settings=active_ai_settings,
                                          has_shopify_settings=has_shopify_settings)
                
                batch.total_count = len(urls)
                db.session.commit()
                
                # Create image items for each URL
                for url in urls:
                    image_item = ImageItem(
                        batch_id=batch.id,
                        url=url,
                        status='pending'
                    )
                    db.session.add(image_item)
                
                db.session.commit()
                
            elif form.source_type.data == 'upload':
                # Process file upload - implemented in separate route
                session['batch_id'] = batch.id
                return redirect(url_for('main.upload_images'))
                
            elif form.source_type.data == 'shopify':
                # Process Shopify product images
                shopify_settings = ShopifySettings.query.filter_by(is_active=True).first()
                shopify_client = ShopifyClient(
                    shopify_settings.api_key,
                    shopify_settings.password,
                    shopify_settings.store_url,
                    shopify_settings.api_version
                )
                
                # Fetch product images from Shopify - this would be implemented in the ShopifyClient
                product_images = shopify_client.get_product_images(
                    product_id=form.shopify_product_id.data if form.shopify_product_id.data else None,
                    collection_id=form.shopify_collection_id.data if form.shopify_collection_id.data else None,
                    limit=form.shopify_limit.data if form.shopify_limit.data else 50
                )
                
                if not product_images:
                    flash('No images found in the specified Shopify products.', 'warning')
                    db.session.delete(batch)
                    db.session.commit()
                    return render_template('image_caption_generator.html', form=form, 
                                          ai_settings=active_ai_settings,
                                          has_shopify_settings=has_shopify_settings)
                
                batch.total_count = len(product_images)
                db.session.commit()
                
                # Create image items for each Shopify image
                for image in product_images:
                    image_item = ImageItem(
                        batch_id=batch.id,
                        url=image['src'],
                        shopify_product_id=image['product_id'],
                        shopify_image_id=image['id'],
                        status='pending'
                    )
                    db.session.add(image_item)
                
                db.session.commit()
            
            # Update batch status
            batch.status = 'ready_to_process'
            db.session.commit()
            
            # Redirect to processing page
            return redirect(url_for('main.process_image_batch', batch_id=batch.id))
            
        except Exception as e:
            logger.error(f"Error setting up image batch: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
            return render_template('image_caption_generator.html', form=form, 
                                  ai_settings=active_ai_settings,
                                  has_shopify_settings=has_shopify_settings)
    
    return render_template('image_caption_generator.html', form=form, 
                          ai_settings=active_ai_settings,
                          has_shopify_settings=has_shopify_settings)

@app.route('/image-captions/upload', methods=['GET', 'POST'])
def upload_images():
    """Route for uploading images for caption generation"""
    if 'batch_id' not in session:
        flash('No active batch. Please start a new batch.', 'warning')
        return redirect(url_for('main.image_caption_generator'))
    
    batch_id = session['batch_id']
    batch = ImageBatch.query.get_or_404(batch_id)
    
    if request.method == 'POST':
        if 'images' not in request.files:
            flash('No files selected.', 'warning')
            return redirect(request.url)
        
        files = request.files.getlist('images')
        if not files or files[0].filename == '':
            flash('No files selected.', 'warning')
            return redirect(request.url)
        
        # Set up the upload folder
        upload_folder = os.path.join(UPLOAD_FOLDER, f'image_batch_{batch_id}')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Process each uploaded file
        file_count = 0
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                
                # Create image item record
                image_item = ImageItem(
                    batch_id=batch_id,
                    filename=filename,
                    file_path=file_path,
                    mimetype=file.content_type,
                    filesize=os.path.getsize(file_path),
                    status='pending'
                )
                db.session.add(image_item)
                file_count += 1
        
        # Update batch information
        batch.total_count = file_count
        batch.status = 'ready_to_process'
        db.session.commit()
        
        # Clean up session
        session.pop('batch_id', None)
        
        flash(f'{file_count} images uploaded successfully.', 'success')
        return redirect(url_for('main.process_image_batch', batch_id=batch_id))
    
    return render_template('image_upload.html', batch=batch)

@app.route('/image-captions/process/<int:batch_id>')
def process_image_batch(batch_id):
    """Route for processing an image batch"""
    # Get the batch record
    batch = ImageBatch.query.get_or_404(batch_id)
    
    # Get AI settings
    active_ai_settings = AISettings.query.filter_by(is_active=True).first()
    if not active_ai_settings:
        flash('Please configure your AI API settings first.', 'warning')
        return redirect(url_for('main.ai_settings'))
    
    # Initialize AI service
    ai_service = AIService(api_key=active_ai_settings.api_key, 
                         api_provider=active_ai_settings.api_provider)
    
    # Get unprocessed images
    pending_images = ImageItem.query.filter_by(batch_id=batch_id, status='pending').all()
    
    if not pending_images:
        flash('No pending images found in this batch.', 'info')
        return redirect(url_for('main.image_caption_results', batch_id=batch_id))
    
    # Update batch status
    batch.status = 'processing'
    db.session.commit()
    
    try:
        # Process each image
        for image in pending_images:
            # Set image status to processing
            image.status = 'processing'
            db.session.commit()
            
            try:
                # Determine the image source to use
                image_source = None
                if image.file_path and os.path.exists(image.file_path):
                    # Use local file path
                    image_source = {'type': 'file', 'path': image.file_path}
                elif image.url:
                    # Use URL
                    image_source = {'type': 'url', 'url': image.url}
                
                if not image_source:
                    raise ValueError("No valid image source found")
                
                # Generate captions using AI service
                caption_data = ai_service.generate_image_captions(
                    image_source=image_source,
                    include_alt_text=True,
                    include_seo=True,
                    include_tags=True,
                    include_product_suggestions=True
                )
                
                # Update image with generated captions
                image.alt_text = caption_data.get('alt_text')
                image.caption = caption_data.get('caption')
                image.tags = caption_data.get('tags')
                image.detailed_description = caption_data.get('detailed_description')
                image.seo_keywords = caption_data.get('seo_keywords')
                image.seo_title = caption_data.get('seo_title')
                image.product_suggested_name = caption_data.get('product_name')
                image.product_category = caption_data.get('product_category')
                image.status = 'completed'
                image.processed_at = datetime.utcnow()
                
                # Update batch counter
                batch.processed_count += 1
                
                # If this is a Shopify update and we have Shopify details
                if batch.export_format == 'shopify_update' and image.shopify_product_id and image.shopify_image_id:
                    # Get Shopify settings
                    shopify_settings = ShopifySettings.query.get(batch.settings_id)
                    if shopify_settings:
                        # Initialize Shopify client
                        shopify_client = ShopifyClient(
                            shopify_settings.api_key,
                            shopify_settings.password, 
                            shopify_settings.store_url,
                            shopify_settings.api_version
                        )
                        
                        # Update image in Shopify
                        update_result = shopify_client.update_product_image(
                            product_id=image.shopify_product_id,
                            image_id=image.shopify_image_id,
                            alt_text=image.alt_text
                        )
                        
                        if update_result:
                            image.shopify_updated = True
                
                db.session.commit()
                
            except Exception as e:
                logger.error(f"Error processing image {image.id}: {str(e)}")
                image.status = 'failed'
                image.error_message = str(e)
                db.session.commit()
        
        # Update batch status
        if batch.processed_count == batch.total_count:
            batch.status = 'completed'
        else:
            # There might have been failures
            failed_count = ImageItem.query.filter_by(batch_id=batch_id, status='failed').count()
            if failed_count > 0:
                batch.status = 'completed_with_errors'
            else:
                batch.status = 'partially_completed'
        
        db.session.commit()
        
        # If export format is CSV, generate and save the export file
        if batch.export_format == 'csv':
            export_path = os.path.join(UPLOAD_FOLDER, f'image_captions_batch_{batch_id}.csv')
            # Create a pandas DataFrame from the image items
            # Include all relevant fields for the CSV export
            # Save the CSV file
            # Update the batch with the export path
            batch.export_path = export_path
            db.session.commit()
        
        return redirect(url_for('main.image_caption_results', batch_id=batch_id))
        
    except Exception as e:
        logger.error(f"Error processing batch {batch_id}: {str(e)}")
        batch.status = 'failed'
        db.session.commit()
        flash(f'Error processing batch: {str(e)}', 'danger')
        return redirect(url_for('main.image_caption_generator'))

@app.route('/image-captions/results/<int:batch_id>')
def image_caption_results(batch_id):
    """Route for viewing the results of an image caption batch"""
    # Get the batch record
    batch = ImageBatch.query.get_or_404(batch_id)
    
    # Get the images associated with this batch
    images = ImageItem.query.filter_by(batch_id=batch_id).all()
    
    # Get statistics
    stats = {
        'total': batch.total_count,
        'processed': batch.processed_count,
        'success': ImageItem.query.filter_by(batch_id=batch_id, status='completed').count(),
        'failed': ImageItem.query.filter_by(batch_id=batch_id, status='failed').count()
    }
    
    return render_template('image_caption_results.html', batch=batch, images=images, stats=stats)

@app.route('/image-captions/download/<int:batch_id>')
def download_image_captions(batch_id):
    """Route for downloading image captions as a CSV file"""
    # Get the batch record
    batch = ImageBatch.query.get_or_404(batch_id)
    
    if batch.export_format != 'csv' or not batch.export_path or not os.path.exists(batch.export_path):
        # If the export hasn't been created yet, generate it on-the-fly
        images = ImageItem.query.filter_by(batch_id=batch_id).all()
        
        # Convert to a list of dictionaries for DataFrame
        image_data = []
        for img in images:
            image_data.append({
                'filename': img.filename,
                'url': img.url,
                'alt_text': img.alt_text,
                'caption': img.caption,
                'tags': img.tags,
                'detailed_description': img.detailed_description,
                'seo_keywords': img.seo_keywords,
                'seo_title': img.seo_title,
                'product_suggested_name': img.product_suggested_name,
                'product_category': img.product_category,
                'status': img.status,
                'shopify_product_id': img.shopify_product_id,
                'shopify_image_id': img.shopify_image_id,
                'shopify_updated': img.shopify_updated
            })
        
        # Create a pandas DataFrame
        import pandas as pd
        df = pd.DataFrame(image_data)
        
        # Create a temporary CSV file
        export_path = os.path.join(UPLOAD_FOLDER, f'image_captions_batch_{batch_id}.csv')
        df.to_csv(export_path, index=False)
        
        # Update the batch with the export path
        batch.export_path = export_path
        db.session.commit()
    
    # Send the file
    return send_file(
        batch.export_path,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'image_captions_batch_{batch_id}.csv'
    )

# =====================================
# Dropshipping Agent Routes
# =====================================

@app.route('/api/dropshipping/trend-analysis', methods=['POST'])
def api_dropshipping_trend_analysis():
    """API endpoint for starting trend analysis"""
    # Get request data
    data = request.json or {}
    sources = data.get('sources', [])
    keywords = data.get('keywords', [])
    
    # Create the agent
    agent = DropshippingAgent()
    
    # Start the analysis
    try:
        result = agent.start_trend_analysis(sources=sources, keywords=keywords)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in trend analysis API: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/dropshipping/source-products', methods=['POST'])
def api_dropshipping_source_products():
    """API endpoint for product sourcing"""
    # Get request data
    data = request.json or {}
    trend_ids = data.get('trend_ids', [])
    urls = data.get('urls', [])
    
    # Create the agent
    agent = DropshippingAgent()
    
    # Start the product sourcing
    try:
        result = agent.source_products(trend_ids=trend_ids, urls=urls)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in product sourcing API: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/dropshipping/evaluate-products', methods=['POST'])
def api_dropshipping_evaluate_products():
    """API endpoint for product evaluation"""
    # Get request data
    data = request.json or {}
    product_ids = data.get('product_ids', [])
    
    # Create the agent
    agent = DropshippingAgent()
    
    # Start the product evaluation
    try:
        result = agent.evaluate_products(product_ids=product_ids)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in product evaluation API: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/dropshipping/discover-niches', methods=['POST'])
def api_dropshipping_discover_niches():
    """API endpoint for niche discovery"""
    # Get request data
    data = request.json or {}
    keywords = data.get('keywords', [])
    
    # Create the agent
    agent = DropshippingAgent()
    
    # Start the niche discovery
    try:
        result = agent.discover_niches(keywords=keywords)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in niche discovery API: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

# =====================================
# Store Agent Routes
# =====================================

@app.route('/api/stores', methods=['GET'])
def api_get_stores():
    """API endpoint for getting all stores"""
    try:
        # Get all stores from the database
        stores = StoreSetup.query.all()
        
        # Convert to list of dictionaries
        stores_data = []
        for store in stores:
            stores_data.append({
                'id': store.id,
                'name': store.store_name,
                'store_url': store.store_url,
                'status': store.status,
                'theme_id': store.theme_id,
                'created_at': store.created_at.isoformat() if store.created_at else None,
                'updated_at': store.updated_at.isoformat() if store.updated_at else None
            })
        
        return jsonify(stores_data)
    
    except Exception as e:
        logger.error(f"Error in get stores API: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/store/create', methods=['POST'])
def api_store_create():
    """API endpoint for creating a store"""
    # Get request data
    data = request.json or {}
    store_params = data.get('store_params', {})
    user_id = data.get('user_id')
    settings_id = data.get('settings_id')
    
    # Log incoming parameters for debugging
    logger.debug(f"Store creation params: {store_params}")
    
    # Get Shopify and AI settings
    shopify_settings = None
    if settings_id:
        shopify_settings = ShopifySettings.query.get(settings_id)
    else:
        shopify_settings = ShopifySettings.query.filter_by(is_active=True).first()
    
    if not shopify_settings:
        return jsonify({'status': 'error', 'error': 'No Shopify settings available'}), 400
    
    ai_settings = AISettings.query.filter_by(is_active=True).first()
    
    # Create the agents
    shopify_client = ShopifyClient(
        shopify_settings.api_key,
        shopify_settings.password,
        shopify_settings.store_url,
        shopify_settings.api_version
    )
    
    ai_service = None
    if ai_settings:
        ai_service = AIService(api_key=ai_settings.api_key, api_provider=ai_settings.api_provider)
    
    store_agent = StoreAgent(shopify_client=shopify_client, ai_service=ai_service)
    
    # Create the store
    try:
        result = store_agent.create_store(
            store_params=store_params,
            user_id=user_id,
            settings_id=settings_id or shopify_settings.id
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in store creation API: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/store/add-products', methods=['POST'])
def api_store_add_products():
    """API endpoint for adding products to a store"""
    # Get request data
    data = request.json or {}
    store_id = data.get('store_id')
    product_ids = data.get('product_ids', [])
    product_sources = data.get('product_sources', [])
    
    # Validate store ID
    if not store_id:
        return jsonify({'status': 'error', 'error': 'Store ID is required'}), 400
    
    # Check if store exists
    store = StoreSetup.query.get(store_id)
    if not store:
        return jsonify({'status': 'error', 'error': f'Store with ID {store_id} not found'}), 404
    
    # Get Shopify and AI settings
    shopify_settings = ShopifySettings.query.get(store.settings_id)
    if not shopify_settings:
        return jsonify({'status': 'error', 'error': 'No Shopify settings available for this store'}), 400
    
    ai_settings = AISettings.query.filter_by(is_active=True).first()
    
    # Create the agents
    shopify_client = ShopifyClient(
        shopify_settings.api_key,
        shopify_settings.password,
        shopify_settings.store_url,
        shopify_settings.api_version
    )
    
    ai_service = None
    if ai_settings:
        ai_service = AIService(api_key=ai_settings.api_key, api_provider=ai_settings.api_provider)
    
    store_agent = StoreAgent(shopify_client=shopify_client, ai_service=ai_service)
    
    # Add products
    try:
        result = store_agent.add_products(
            store_id=store_id,
            product_ids=product_ids,
            product_sources=product_sources
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in adding products API: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/store/theme-customize', methods=['POST'])
def api_store_customize_theme():
    """API endpoint for customizing store theme"""
    # Get request data
    data = request.json or {}
    store_id = data.get('store_id')
    theme_settings = data.get('theme_settings', {})
    
    # Validate store ID
    if not store_id:
        return jsonify({'status': 'error', 'error': 'Store ID is required'}), 400
    
    # Check if store exists
    store = StoreSetup.query.get(store_id)
    if not store:
        return jsonify({'status': 'error', 'error': f'Store with ID {store_id} not found'}), 404
    
    # Get Shopify and AI settings
    shopify_settings = ShopifySettings.query.get(store.settings_id)
    if not shopify_settings:
        return jsonify({'status': 'error', 'error': 'No Shopify settings available for this store'}), 400
    
    ai_settings = AISettings.query.filter_by(is_active=True).first()
    
    # Create the agents
    shopify_client = ShopifyClient(
        shopify_settings.api_key,
        shopify_settings.password,
        shopify_settings.store_url,
        shopify_settings.api_version
    )
    
    ai_service = None
    if ai_settings:
        ai_service = AIService(api_key=ai_settings.api_key, api_provider=ai_settings.api_provider)
    
    store_agent = StoreAgent(shopify_client=shopify_client, ai_service=ai_service)
    
    # Customize theme
    try:
        result = store_agent.customize_theme(
            store_id=store_id,
            theme_settings=theme_settings
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in theme customization API: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/store/publish', methods=['POST'])
def api_store_publish():
    """API endpoint for publishing store content (products and pages)"""
    # Get request data
    data = request.json or {}
    store_id = data.get('store_id')
    publish_products = data.get('publish_products', True)
    publish_pages = data.get('publish_pages', True)
    product_ids = data.get('product_ids', [])  # Optional specific product IDs
    page_ids = data.get('page_ids', [])  # Optional specific page IDs
    
    # Validate store ID
    if not store_id:
        return jsonify({'status': 'error', 'error': 'Store ID is required'}), 400
    
    # Check if store exists
    store = StoreSetup.query.get(store_id)
    if not store:
        return jsonify({'status': 'error', 'error': f'Store with ID {store_id} not found'}), 404
    
    # Get Shopify and AI settings
    shopify_settings = ShopifySettings.query.get(store.settings_id)
    if not shopify_settings:
        return jsonify({'status': 'error', 'error': 'No Shopify settings available for this store'}), 400
    
    ai_settings = AISettings.query.filter_by(is_active=True).first()
    
    # Create the agents
    shopify_client = ShopifyClient(
        shopify_settings.api_key,
        shopify_settings.password,
        shopify_settings.store_url,
        shopify_settings.api_version
    )
    
    ai_service = None
    if ai_settings:
        ai_service = AIService(api_key=ai_settings.api_key, api_provider=ai_settings.api_provider)
    
    store_agent = StoreAgent(shopify_client=shopify_client, ai_service=ai_service)
    
    # Publish content
    results = {}
    try:
        if publish_products:
            product_result = store_agent.publish_products(
                store_id=store_id,
                product_ids=product_ids if product_ids else None
            )
            results['products'] = product_result
            
        if publish_pages:
            page_result = store_agent.publish_pages(
                store_id=store_id,
                page_ids=page_ids if page_ids else None
            )
            results['pages'] = page_result
            
        return jsonify({
            'status': 'completed',
            'results': results
        })
    except Exception as e:
        logger.error(f"Error in publishing store content API: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/store/from-dropshipping', methods=['POST'])
def api_store_from_dropshipping():
    """API endpoint for creating a complete store from dropshipping results"""
    # Get request data
    data = request.json or {}
    niche_id = data.get('niche_id')
    product_ids = data.get('product_ids', [])
    user_id = data.get('user_id')
    settings_id = data.get('settings_id')
    store_name = data.get('store_name')
    
    # Get Shopify and AI settings
    shopify_settings = None
    if settings_id:
        shopify_settings = ShopifySettings.query.get(settings_id)
    else:
        shopify_settings = ShopifySettings.query.filter_by(is_active=True).first()
    
    if not shopify_settings:
        return jsonify({'status': 'error', 'error': 'No Shopify settings available'}), 400
    
    ai_settings = AISettings.query.filter_by(is_active=True).first()
    
    # Create the agents
    shopify_client = ShopifyClient(
        shopify_settings.api_key,
        shopify_settings.password,
        shopify_settings.store_url,
        shopify_settings.api_version
    )
    
    ai_service = None
    if ai_settings:
        ai_service = AIService(api_key=ai_settings.api_key, api_provider=ai_settings.api_provider)
    
    store_agent = StoreAgent(shopify_client=shopify_client, ai_service=ai_service)
    
    # Create the store from dropshipping results
    try:
        result = store_agent.create_store_from_dropshipping_results(
            niche_id=niche_id,
            product_ids=product_ids,
            user_id=user_id,
            settings_id=settings_id or shopify_settings.id,
            store_name=store_name
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in creating store from dropshipping results API: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

# Status endpoints for agent tasks
@app.route('/api/agent-task/<int:task_id>', methods=['GET'])
def api_agent_task_status(task_id):
    """API endpoint to get the status of an agent task"""
    task = AgentTask.query.get(task_id)
    
    if not task:
        return jsonify({'status': 'error', 'error': f'Task with ID {task_id} not found'}), 404
    
    response = {
        'id': task.id,
        'task_type': task.task_type,
        'status': task.status,
        'progress': task.progress,
        'created_at': task.created_at.isoformat(),
        'updated_at': task.updated_at.isoformat()
    }
    
    # Include error message if task failed
    if task.status == 'failed' and task.error_message:
        response['error'] = task.error_message
    
    # Include result information if available
    if task.result_id and task.result_type:
        response['result'] = {
            'type': task.result_type,
            'id': task.result_id
        }
    
    return jsonify(response)

# =====================================
# Agent UI Routes
# =====================================

@app.route('/dropshipping', methods=['GET'])
def dropshipping_page():
    """Render the dropshipping agent interface"""
    return render_template('dropshipping.html')

@app.route('/store-agent', methods=['GET'])
def store_agent_page():
    """Render the store agent interface"""
    return render_template('store_agent.html')