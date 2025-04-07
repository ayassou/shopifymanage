import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Create a Flask app
app = Flask(__name__)

# Configure flask app
app.secret_key = os.environ.get("SESSION_SECRET", "shopify-product-uploader-secret")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate https URLs

# Configure the database connection
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Import models and initialize database
from models import db, ShopifySettings, UploadHistory, ProductUploadResult, AISettings, BlogPost, PageContent

# Initialize the app with the database
db.init_app(app)

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

# Import the application routes
import app as application_routes

# Register routes with the app
app.register_blueprint(application_routes.app)

# For local development
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)