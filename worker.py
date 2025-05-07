import os
import time
import logging
from app import app
from price_scraper import start_alert_checker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Set up Alpha Vantage API key
    app.config['ALPHA_VANTAGE_API_KEY'] = os.environ.get('ALPHA_VANTAGE_API_KEY', '')
    
    logger.info("Starting price alert checker worker")
    
    # Start the price alert checker
    checker_thread = start_alert_checker(app, check_interval=60)
    
    # Keep the worker running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")