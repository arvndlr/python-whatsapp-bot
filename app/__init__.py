from flask import Flask
from app.config import load_configurations, configure_logging
from .views import webhook_blueprint
from dotenv import load_dotenv
import os


def create_app():
    load_dotenv()  # Load environment variables from .env file
    app = Flask(__name__)

    # Load configurations and logging settings
    load_configurations(app)
    configure_logging()

    # Import and register blueprints, if any
    app.register_blueprint(webhook_blueprint)

    return app
