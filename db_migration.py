import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from main import app
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def alter_shopify_settings_table():
    """Add new columns to the shopify_settings table"""
    from sqlalchemy import text
    from app import db
    
    try:
        # Check if the is_valid column already exists
        with db.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='shopify_settings' AND column_name='is_valid'"
            ))
            if result.rowcount == 0:
                logger.info("Adding is_valid column to shopify_settings table")
                conn.execute(text(
                    "ALTER TABLE shopify_settings ADD COLUMN is_valid BOOLEAN DEFAULT FALSE"
                ))
                conn.commit()
            else:
                logger.info("is_valid column already exists")
                
        # Check if the shop_name column already exists
        with db.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='shopify_settings' AND column_name='shop_name'"
            ))
            if result.rowcount == 0:
                logger.info("Adding shop_name column to shopify_settings table")
                conn.execute(text(
                    "ALTER TABLE shopify_settings ADD COLUMN shop_name VARCHAR(255)"
                ))
                conn.commit()
            else:
                logger.info("shop_name column already exists")
                
        logger.info("Database migration completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        return False

if __name__ == '__main__':
    with app.app_context():
        alter_shopify_settings_table()