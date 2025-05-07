import os
import logging
import requests
import json
from app import app

# Configure logging
logger = logging.getLogger(__name__)

def init_telegram_bot():
    """Initialize and validate the Telegram bot configuration"""
    logger.info("Initializing Telegram bot integration")
    
    # Nothing to initialize for now, but this function could be expanded
    # to validate tokens or set up webhook listeners if needed in the future
    
    return True

def send_telegram_message(bot_token, chat_id, message):
    """
    Send a message to a Telegram chat
    
    Args:
        bot_token (str): The Telegram bot token
        chat_id (str): The Telegram chat ID
        message (str): The message to send
        
    Returns:
        dict: A dictionary containing the success status and error message if any
    """
    logger.debug(f"Sending Telegram message to chat {chat_id}")
    
    try:
        # Construct the Telegram Bot API URL
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        # Prepare the payload
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        # Send the request
        response = requests.post(url, json=payload, timeout=10)
        
        # Check if the request was successful
        if response.status_code == 200:
            logger.info(f"Message sent successfully to Telegram chat {chat_id}")
            return {"success": True}
        else:
            error_msg = f"Failed to send message to Telegram. Status code: {response.status_code}, Response: {response.text}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        error_msg = f"Exception sending Telegram message: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

def test_telegram_connection(bot_token, chat_id):
    """
    Test the Telegram connection by sending a test message
    
    Args:
        bot_token (str): The Telegram bot token
        chat_id (str): The Telegram chat ID
        
    Returns:
        dict: A dictionary containing the success status and error message if any
    """
    logger.info(f"Testing Telegram connection to chat {chat_id}")
    
    test_message = "🔍 This is a test message from your TradingView-Telegram integration."
    return send_telegram_message(bot_token, chat_id, test_message)
