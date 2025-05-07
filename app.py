import os
import logging

from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # Needed for url_for to generate with https

# Configure the database
database_url = os.environ.get("DATABASE_URL", "sqlite:///tradingview_telegram.db")
# Heroku-style fix for PostgreSQL URLs if needed
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

# Import routes after app is created to avoid circular imports
from webhook import webhook_bp
from config import config_bp
from telegram_bot import init_telegram_bot

app.register_blueprint(webhook_bp)
app.register_blueprint(config_bp)

# Initialize Telegram bot
with app.app_context():
    init_telegram_bot()

# Register routes
@app.route('/')
def index():
    return redirect(url_for('config.dashboard'))

# Import models and create tables
with app.app_context():
    import models
    db.create_all()
    logger.info("Database tables created")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
