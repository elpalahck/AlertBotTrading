import os
import logging
from app import app  # noqa: F401
from price_scraper import start_alert_checker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set up Alpha Vantage API key if available
app.config['ALPHA_VANTAGE_API_KEY'] = os.environ.get('ALPHA_VANTAGE_API_KEY', '')

# Start the price alert checker
# Iniciar el verificador de alertas de precio en un hilo en segundo plano
start_alert_checker(app, check_interval=60)  # Comprobar cada minuto

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
