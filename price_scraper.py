import logging
import time
import json
import threading
import requests
from datetime import datetime
from flask import current_app

from app import db
from models import PriceAlert, NotificationLog
from telegram_bot import send_telegram_message

# Configure logging
logger = logging.getLogger(__name__)

def get_price_data(symbol):
    """
    Get current price data for a symbol.
    This uses a public API (Alpha Vantage, Yahoo Finance, etc.)
    
    Args:
        symbol (str): The trading symbol (e.g., 'SPX', 'AAPL', 'BTC/USD')
        
    Returns:
        dict: A dictionary with price information or None if error
    """
    try:
        # For demonstration, we're using Alpha Vantage's API
        # In production, you'd want to use a more robust solution or your preferred data source
        api_key = current_app.config.get('ALPHA_VANTAGE_API_KEY', '')
        if not api_key:
            logger.warning("No Alpha Vantage API key configured")
            # Fallback to a different API or method if no key available
            return get_price_from_alternative_source(symbol)
            
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if we have valid data
            if "Global Quote" in data and "05. price" in data["Global Quote"]:
                current_price = float(data["Global Quote"]["05. price"])
                return {
                    "symbol": symbol,
                    "price": current_price,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.warning(f"Invalid data format from Alpha Vantage for {symbol}: {data}")
                return None
        else:
            logger.error(f"Error fetching price data: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Exception fetching price data for {symbol}: {str(e)}")
        return None

def get_price_from_alternative_source(symbol):
    """
    Alternative method to get price when the primary method fails.
    You can implement different data sources here.
    
    Args:
        symbol (str): The trading symbol
        
    Returns:
        dict: A dictionary with price information or None if error
    """
    try:
        # Use Yahoo Finance API as an alternative (no API key required)
        # This is a simple example and might not work for all symbols
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract the current price from the response
            if "chart" in data and "result" in data["chart"] and len(data["chart"]["result"]) > 0:
                result = data["chart"]["result"][0]
                if "meta" in result and "regularMarketPrice" in result["meta"]:
                    current_price = float(result["meta"]["regularMarketPrice"])
                    return {
                        "symbol": symbol,
                        "price": current_price,
                        "timestamp": datetime.now().isoformat()
                    }
            
            logger.warning(f"Invalid data format from Yahoo Finance for {symbol}")
            return None
        else:
            logger.error(f"Error fetching price data from Yahoo: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Exception fetching alternative price data for {symbol}: {str(e)}")
        return None

def check_and_trigger_alerts():
    """
    Check all active price alerts and trigger notifications if conditions are met
    """
    logger.debug("Checking price alerts")
    
    try:
        # Get all active price alerts
        with current_app.app_context():
            alerts = PriceAlert.query.filter_by(is_active=True).all()
            
            if not alerts:
                logger.debug("No active price alerts found")
                return
                
            logger.info(f"Checking {len(alerts)} active price alerts")
            
            for alert in alerts:
                # Skip alerts that have already been triggered if one-time
                if alert.is_one_time and alert.is_triggered:
                    continue
                    
                # Get current price for this symbol
                price_data = get_price_data(alert.symbol)
                
                if not price_data:
                    logger.warning(f"Could not get price data for {alert.symbol}")
                    continue
                
                current_price = price_data["price"]
                logger.debug(f"Current price for {alert.symbol}: {current_price}")
                
                # Check if alert condition is met
                alert_triggered = False
                
                if alert.alert_type == "above" and current_price > alert.target_price:
                    alert_triggered = True
                elif alert.alert_type == "below" and current_price < alert.target_price:
                    alert_triggered = True
                
                if alert_triggered:
                    logger.info(f"Alert triggered for {alert.symbol} (Current: {current_price}, Target: {alert.target_price})")
                    
                    # Format the message
                    message = alert.message_template.replace("{{symbol}}", alert.symbol)
                    message = message.replace("{{current_price}}", str(current_price))
                    message = message.replace("{{target_price}}", str(alert.target_price))
                    message = message.replace("{{alert_type}}", alert.alert_type)
                    
                    # Send notification via Telegram
                    telegram_result = send_telegram_message(
                        bot_token=alert.telegram_config.bot_token,
                        chat_id=alert.telegram_config.chat_id,
                        message=message
                    )
                    
                    # Log the notification
                    notification_log = NotificationLog(
                        price_alert_id=alert.id,
                        payload=json.dumps(price_data),
                        message_sent=message,
                        status="success" if telegram_result.get("success") else "failed",
                        error_message=telegram_result.get("error")
                    )
                    db.session.add(notification_log)
                    
                    # Update alert status if it's a one-time alert
                    if alert.is_one_time:
                        alert.is_triggered = True
                        alert.last_triggered_at = datetime.utcnow()
                    
                    db.session.commit()
    
    except Exception as e:
        logger.error(f"Error checking price alerts: {str(e)}")

def start_alert_checker(app, check_interval=60):
    """
    Start a background thread to periodically check price alerts
    
    Args:
        app: The Flask application
        check_interval (int): Interval in seconds between checks
    """
    def run_checker():
        logger.info(f"Starting price alert checker (interval: {check_interval}s)")
        
        while True:
            try:
                with app.app_context():
                    check_and_trigger_alerts()
            except Exception as e:
                logger.error(f"Error in alert checker thread: {str(e)}")
                
            # Wait for the next check interval
            time.sleep(check_interval)
    
    # Start the checker in a background thread
    checker_thread = threading.Thread(target=run_checker, daemon=True)
    checker_thread.start()
    
    return checker_thread