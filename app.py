import os
import logging
import time
import json
import tempfile
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, Response
from werkzeug.utils import secure_filename
import pandas as pd
from forms import UploadForm, ShopifySettingsForm, AISettingsForm, AIGeneratorForm, BlogPostGeneratorForm, PageGeneratorForm
from data_processor import process_data, validate_data
from shopify_client import ShopifyClient
from ai_service import AIService
from web_scraper import ProductScraper
from models import db, ShopifySettings, AISettings, UploadHistory, ProductUploadResult, BlogPost, PageContent

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
        return redirect(url_for('main.upload'))
    
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
        return redirect(url_for('main.ai_generator'))
    
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