import os
from flask import Flask
import secrets
import datetime

from telegramtracker.core import database
from telegramtracker.web import routes

# Create Flask application
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate secure random secret key

def create_app():
    """Configure and return the Flask application."""
    
    # Initialize database
    database.init_db()
    
    # Register routes
    routes.register_routes(app)
    
    # Add datetime.now function to all templates
    @app.context_processor
    def inject_now():
        return {'now': datetime.datetime.now}
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    # Development server - Use waitress or gunicorn for production
    app.run(debug=True, host='0.0.0.0', port=5001) 