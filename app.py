# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

# app.py
from flask import Flask
from config import configure_app
from models import db
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_restful import Api
from resources.user.routes import user_bp
from resources.payments.routes import payments_bp
from resources.postgres_database.routes import postgress_db_bp
import logging
from dotenv import load_dotenv

def create_app():
    # Load environment variables
    load_dotenv()

    # Initialize logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    # Create Flask app
    app = Flask(__name__)
    configure_app(app)

    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)
    JWTManager(app)
    Mail(app)
    Api(app)

    # Register blueprints
    app.register_blueprint(user_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(postgress_db_bp)

    @app.route('/')
    def home():
        return "Hello, Flask"

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
