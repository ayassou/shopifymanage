import os
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import pandas as pd
from forms import UploadForm, ShopifySettingsForm
from data_processor import process_data, validate_data
from shopify_client import ShopifyClient
from models import db, ShopifySettings, UploadHistory, ProductUploadResult

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