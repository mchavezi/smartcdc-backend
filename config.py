# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

# config.py
import os
from flask_cors import CORS
from datetime import timedelta

class Config:
    SECRET_KEY = 'your_secret_key'
    JWT_SECRET_KEY = 'your_jwt_secret_key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # MySQL configuration
    DB_USER = os.getenv('DB_USER', 'DB_USER NOT SET!')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'DB_PASSWORD NOT SET!')
    DB_HOST = os.getenv('DB_HOST', 'DB_HOST NOT SET!')
    DB_NAME = os.getenv('DB_NAME', 'DB_NAME NOT SET!')
    SQLALCHEMY_DATABASE_URI = f'mysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'

		# Frontend React App URL 
		# ex: https://app.smart-cdc.space-rocket.com
    FRONTEND_APP_URL = os.getenv('FRONTEND_APP_URL', 'FRONTEND_APP_URL NOT SET!')

    # Mail configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.getenv('EMAIL_USER', 'EMAIL_USER NOT SET!')
    MAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'EMAIL_PASSWORD NOT SET!')
    MAIL_DEFAULT_SENDER = ('SmartCDC', os.getenv('EMAIL_USER', 'EMAIL_USER NOT SET!'))
    MAIL_DEBUG = True


    # Session and CORS configuration
    ENV = os.getenv('ENV', 'local')
    SESSION_COOKIE_SECURE = ENV != 'local'
    SESSION_COOKIE_SAMESITE = 'None' if ENV != 'local' else 'Lax'
    SESSION_COOKIE_HTTPONLY = True

    if ENV != 'local':
        CORS_ORIGINS = [
            'https://app.smart-cdc.space-rocket.com',
        ]
    else:
        CORS_ORIGINS = [
            'https://app.smart-cdc.space-rocket.com',
            'http://localhost:3000',
        ]

    # Stripe configuration
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    
def configure_app(app):
    """Apply configuration and setup CORS."""
    app.config.from_object(Config)
    CORS(app, resources={r"/*": {"origins": app.config['CORS_ORIGINS']}}, supports_credentials=True)
