import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import pandas as pd
from forms import UploadForm, ShopifySettingsForm
from data_processor import process_data, validate_data
from shopify_client import ShopifyClient

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "shopify-uploader-secret-key")

# Allowed file extensions
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

# Temporary storage for uploaded files
UPLOAD_FOLDER = '/tmp'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    form = ShopifySettingsForm()
    
    if form.validate_on_submit():
        # Store the Shopify settings in session
        session['shopify_api_key'] = form.api_key.data
        session['shopify_password'] = form.password.data
        session['shopify_store_url'] = form.store_url.data
        session['shopify_api_version'] = form.api_version.data
        
        flash('Shopify settings saved successfully!', 'success')
        return redirect(url_for('upload'))
    
    # Pre-fill the form with existing settings if available
    if 'shopify_api_key' in session:
        form.api_key.data = session['shopify_api_key']
    if 'shopify_password' in session:
        form.password.data = session['shopify_password']
    if 'shopify_store_url' in session:
        form.store_url.data = session['shopify_store_url']
    if 'shopify_api_version' in session:
        form.api_version.data = session['shopify_api_version']
    
    return render_template('settings.html', form=form)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # Check if Shopify settings exist
    if not all(key in session for key in ['shopify_api_key', 'shopify_password', 'shopify_store_url']):
        flash('Please configure your Shopify API settings first.', 'warning')
        return redirect(url_for('settings'))
    
    form = UploadForm()
    
    if form.validate_on_submit():
        file = form.file.data
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                # Process the file based on its extension
                if filename.endswith('.csv'):
                    df = pd.read_csv(filepath)
                else:  # Excel file
                    df = pd.read_excel(filepath)
                
                # Validate the data
                validation_result = validate_data(df)
                if not validation_result['valid']:
                    flash(f"Data validation failed: {validation_result['errors']}", 'danger')
                    return render_template('upload.html', form=form)
                
                # Store the DataFrame in session for processing
                session['file_path'] = filepath
                
                # Process the data and upload to Shopify
                return redirect(url_for('process'))
                
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
    if 'file_path' not in session:
        flash('No file uploaded. Please upload a file first.', 'warning')
        return redirect(url_for('upload'))
    
    # Get Shopify credentials from session
    api_key = session.get('shopify_api_key')
    password = session.get('shopify_password')
    store_url = session.get('shopify_store_url')
    api_version = session.get('shopify_api_version', '2023-07')
    
    # Initialize Shopify client
    shopify_client = ShopifyClient(api_key, password, store_url, api_version)
    
    try:
        # Read the file
        file_path = session['file_path']
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:  # Excel file
            df = pd.read_excel(file_path)
        
        # Process and upload the data to Shopify
        results = process_data(df, shopify_client)
        
        # Remove the file path from session
        session.pop('file_path', None)
        
        # Render the results page
        return render_template('results.html', results=results)
        
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        flash(f'Error processing data: {str(e)}', 'danger')
        return redirect(url_for('upload'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
