from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, URL

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
