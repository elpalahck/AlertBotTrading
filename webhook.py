import json
import logging
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify
from string import Template

from app import db
from models import TradingViewAlert, NotificationLog
from telegram_bot import send_telegram_message

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
webhook_bp = Blueprint('webhook', __name__, url_prefix='/webhook')

@webhook_bp.route('/<webhook_key>', methods=['POST'])
def receive_alert(webhook_key):
    """
    Endpoint for receiving TradingView webhook alerts
    
    TradingView will send a POST request to this endpoint with the alert data.
    The webhook_key is used to identify which alert configuration to use.
    """
    logger.debug(f"Received webhook request for key: {webhook_key}")
    
    try:
        # Find the alert configuration for this webhook key
        alert_config = TradingViewAlert.query.filter_by(webhook_key=webhook_key, is_active=True).first()
        
        if not alert_config:
            logger.warning(f"No active alert configuration found for webhook key: {webhook_key}")
            return jsonify({"status": "error", "message": "Invalid webhook key or alert is inactive"}), 404
        
        # Check if the Telegram configuration is active
        if not alert_config.telegram_config.is_active:
            logger.warning(f"Telegram configuration is inactive for alert: {alert_config.name}")
            return jsonify({"status": "error", "message": "Telegram configuration is inactive"}), 400
        
        # Parse the payload from TradingView
        payload = request.get_json(silent=True)
        if not payload:
            try:
                payload = json.loads(request.data.decode('utf-8'))
            except:
                payload = {"raw_data": request.data.decode('utf-8')}
        
        logger.debug(f"Received payload: {payload}")
        
        # Format the message using the template
        try:
            message_template = Template(alert_config.message_template)
            message = message_template.safe_substitute(payload)
        except Exception as e:
            logger.error(f"Error formatting message template: {str(e)}")
            message = f"TradingView Alert ({alert_config.name}): {json.dumps(payload)}"
        
        # Send the message to Telegram
        telegram_result = send_telegram_message(
            bot_token=alert_config.telegram_config.bot_token,
            chat_id=alert_config.telegram_config.chat_id,
            message=message
        )
        
        # Log the notification
        notification_log = NotificationLog(
            alert_id=alert_config.id,
            payload=json.dumps(payload),
            message_sent=message,
            status="success" if telegram_result.get("success") else "failed",
            error_message=telegram_result.get("error")
        )
        db.session.add(notification_log)
        db.session.commit()
        
        if telegram_result.get("success"):
            return jsonify({"status": "success", "message": "Alert sent to Telegram"}), 200
        else:
            return jsonify({
                "status": "error", 
                "message": f"Failed to send to Telegram: {telegram_result.get('error')}"
            }), 500
            
    except Exception as e:
        error_msg = f"Error processing webhook: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # Try to log the error if possible
        try:
            notification_log = NotificationLog(
                alert_id=alert_config.id if 'alert_config' in locals() else None,
                payload=json.dumps(request.get_json(silent=True)) if request.get_json(silent=True) else request.data.decode('utf-8'),
                status="failed",
                error_message=str(e)
            )
            db.session.add(notification_log)
            db.session.commit()
        except:
            logger.error("Could not log error to database")
        
        return jsonify({"status": "error", "message": error_msg}), 500
