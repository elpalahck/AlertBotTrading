import logging
import secrets
import string
import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import TelegramConfig, TradingViewAlert, NotificationLog, PriceAlert
from telegram_bot import test_telegram_connection
from price_scraper import start_alert_checker

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
config_bp = Blueprint('config', __name__, url_prefix='/config')

def generate_webhook_key(length=16):
    """Generate a random webhook key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@config_bp.route('/')
def dashboard():
    """Main dashboard page"""
    telegram_configs = TelegramConfig.query.all()
    alerts = TradingViewAlert.query.all()
    
    # Get recent logs (last 10)
    recent_logs = NotificationLog.query.order_by(
        NotificationLog.created_at.desc()
    ).limit(10).all()
    
    return render_template(
        'index.html', 
        telegram_configs=telegram_configs, 
        alerts=alerts,
        recent_logs=recent_logs
    )

@config_bp.route('/telegram', methods=['GET', 'POST'])
def telegram_config():
    """Manage Telegram configurations"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            bot_token = request.form.get('bot_token')
            chat_id = request.form.get('chat_id')
            
            if not bot_token or not chat_id:
                flash('Bot token and chat ID are required', 'danger')
                return redirect(url_for('config.telegram_config'))
                
            try:
                # Test the connection before saving
                test_result = test_telegram_connection(bot_token, chat_id)
                
                if not test_result.get('success'):
                    flash(f'Connection test failed: {test_result.get("error")}', 'danger')
                    return redirect(url_for('config.telegram_config'))
                
                # Create new configuration
                new_config = TelegramConfig(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    is_active=True
                )
                db.session.add(new_config)
                db.session.commit()
                
                flash('Telegram configuration added successfully', 'success')
                return redirect(url_for('config.telegram_config'))
            
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error adding Telegram configuration: {str(e)}")
                flash(f'Error adding configuration: {str(e)}', 'danger')
                
        elif action == 'edit':
            config_id = request.form.get('config_id')
            bot_token = request.form.get('bot_token')
            chat_id = request.form.get('chat_id')
            is_active = request.form.get('is_active') == 'on'
            
            try:
                config = TelegramConfig.query.get(config_id)
                if not config:
                    flash('Configuration not found', 'danger')
                    return redirect(url_for('config.telegram_config'))
                
                # Update config
                config.bot_token = bot_token
                config.chat_id = chat_id
                config.is_active = is_active
                config.updated_at = datetime.utcnow()
                
                db.session.commit()
                flash('Configuration updated successfully', 'success')
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error updating Telegram configuration: {str(e)}")
                flash(f'Error updating configuration: {str(e)}', 'danger')
                
        elif action == 'delete':
            config_id = request.form.get('config_id')
            
            try:
                config = TelegramConfig.query.get(config_id)
                if not config:
                    flash('Configuration not found', 'danger')
                    return redirect(url_for('config.telegram_config'))
                
                # Check if there are any alerts using this config
                if config.alerts:
                    flash('Cannot delete configuration with associated alerts', 'danger')
                    return redirect(url_for('config.telegram_config'))
                    
                db.session.delete(config)
                db.session.commit()
                flash('Configuration deleted successfully', 'success')
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error deleting Telegram configuration: {str(e)}")
                flash(f'Error deleting configuration: {str(e)}', 'danger')
        
        elif action == 'test':
            config_id = request.form.get('config_id')
            
            try:
                config = TelegramConfig.query.get(config_id)
                if not config:
                    flash('Configuration not found', 'danger')
                    return redirect(url_for('config.telegram_config'))
                
                # Test the connection
                test_result = test_telegram_connection(config.bot_token, config.chat_id)
                
                if test_result.get('success'):
                    flash('Connection test successful', 'success')
                else:
                    flash(f'Connection test failed: {test_result.get("error")}', 'danger')
                    
            except Exception as e:
                logger.error(f"Error testing Telegram configuration: {str(e)}")
                flash(f'Error testing configuration: {str(e)}', 'danger')
        
        return redirect(url_for('config.telegram_config'))
        
    # GET request - show the configurations
    telegram_configs = TelegramConfig.query.all()
    return render_template('configuration.html', telegram_configs=telegram_configs)

@config_bp.route('/alerts', methods=['GET', 'POST'])
def alerts_config():
    """Manage TradingView alert configurations"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form.get('name')
            telegram_config_id = request.form.get('telegram_config_id')
            message_template = request.form.get('message_template')
            
            if not name or not telegram_config_id:
                flash('Name and Telegram configuration are required', 'danger')
                return redirect(url_for('config.alerts_config'))
                
            try:
                # Generate a webhook key
                webhook_key = generate_webhook_key()
                
                # Create new alert
                new_alert = TradingViewAlert(
                    name=name,
                    webhook_key=webhook_key,
                    telegram_config_id=telegram_config_id,
                    is_active=True
                )
                
                if message_template:
                    new_alert.message_template = message_template
                
                db.session.add(new_alert)
                db.session.commit()
                
                flash('Alert configuration added successfully', 'success')
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error adding alert configuration: {str(e)}")
                flash(f'Error adding alert: {str(e)}', 'danger')
                
        elif action == 'edit':
            alert_id = request.form.get('alert_id')
            name = request.form.get('name')
            telegram_config_id = request.form.get('telegram_config_id')
            message_template = request.form.get('message_template')
            is_active = request.form.get('is_active') == 'on'
            
            try:
                alert = TradingViewAlert.query.get(alert_id)
                if not alert:
                    flash('Alert not found', 'danger')
                    return redirect(url_for('config.alerts_config'))
                
                # Update alert
                alert.name = name
                alert.telegram_config_id = telegram_config_id
                alert.message_template = message_template
                alert.is_active = is_active
                alert.updated_at = datetime.utcnow()
                
                db.session.commit()
                flash('Alert updated successfully', 'success')
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error updating alert configuration: {str(e)}")
                flash(f'Error updating alert: {str(e)}', 'danger')
                
        elif action == 'delete':
            alert_id = request.form.get('alert_id')
            
            try:
                alert = TradingViewAlert.query.get(alert_id)
                if not alert:
                    flash('Alert not found', 'danger')
                    return redirect(url_for('config.alerts_config'))
                    
                db.session.delete(alert)
                db.session.commit()
                flash('Alert deleted successfully', 'success')
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error deleting alert configuration: {str(e)}")
                flash(f'Error deleting alert: {str(e)}', 'danger')
                
        elif action == 'regenerate_webhook':
            alert_id = request.form.get('alert_id')
            
            try:
                alert = TradingViewAlert.query.get(alert_id)
                if not alert:
                    flash('Alert not found', 'danger')
                    return redirect(url_for('config.alerts_config'))
                
                # Generate a new webhook key
                alert.webhook_key = generate_webhook_key()
                alert.updated_at = datetime.utcnow()
                
                db.session.commit()
                flash('Webhook key regenerated successfully', 'success')
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error regenerating webhook key: {str(e)}")
                flash(f'Error regenerating webhook key: {str(e)}', 'danger')
        
        return redirect(url_for('config.alerts_config'))
        
    # GET request - show the alerts
    alerts = TradingViewAlert.query.all()
    telegram_configs = TelegramConfig.query.all()
    
    # Get the hostname for the webhook URL
    host_url = request.host_url.rstrip('/')
    
    return render_template(
        'configuration.html', 
        alerts=alerts, 
        telegram_configs=telegram_configs,
        host_url=host_url
    )

@config_bp.route('/price_alerts', methods=['GET', 'POST'])
def price_alerts():
    """Manage price-based alerts"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form.get('name')
            symbol = request.form.get('symbol')
            alert_type = request.form.get('alert_type')
            target_price = request.form.get('target_price')
            telegram_config_id = request.form.get('telegram_config_id')
            message_template = request.form.get('message_template')
            is_one_time = request.form.get('is_one_time') == 'true'
            
            if not name or not symbol or not alert_type or not target_price or not telegram_config_id:
                flash('All fields are required', 'danger')
                return redirect(url_for('config.price_alerts'))
                
            try:
                # Create new price alert
                new_alert = PriceAlert(
                    name=name,
                    symbol=symbol.upper(),
                    alert_type=alert_type,
                    target_price=float(target_price),
                    telegram_config_id=telegram_config_id,
                    is_active=True,
                    is_one_time=is_one_time
                )
                
                if message_template:
                    new_alert.message_template = message_template
                
                db.session.add(new_alert)
                db.session.commit()
                
                flash('Price alert added successfully', 'success')
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error adding price alert: {str(e)}")
                flash(f'Error adding alert: {str(e)}', 'danger')
                
        elif action == 'edit':
            alert_id = request.form.get('alert_id')
            name = request.form.get('name')
            symbol = request.form.get('symbol')
            alert_type = request.form.get('alert_type')
            target_price = request.form.get('target_price')
            telegram_config_id = request.form.get('telegram_config_id')
            message_template = request.form.get('message_template')
            is_one_time = request.form.get('is_one_time') == 'true'
            is_active = request.form.get('is_active') == 'true'
            reset_triggered = request.form.get('reset_triggered') == 'true'
            
            try:
                alert = PriceAlert.query.get(alert_id)
                if not alert:
                    flash('Alert not found', 'danger')
                    return redirect(url_for('config.price_alerts'))
                
                # Update alert
                alert.name = name
                alert.symbol = symbol.upper()
                alert.alert_type = alert_type
                alert.target_price = float(target_price)
                alert.telegram_config_id = telegram_config_id
                alert.message_template = message_template
                alert.is_active = is_active
                alert.is_one_time = is_one_time
                
                if reset_triggered:
                    alert.is_triggered = False
                    alert.last_triggered_at = None
                
                alert.updated_at = datetime.utcnow()
                
                db.session.commit()
                flash('Price alert updated successfully', 'success')
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error updating price alert: {str(e)}")
                flash(f'Error updating alert: {str(e)}', 'danger')
                
        elif action == 'delete':
            alert_id = request.form.get('alert_id')
            
            try:
                alert = PriceAlert.query.get(alert_id)
                if not alert:
                    flash('Alert not found', 'danger')
                    return redirect(url_for('config.price_alerts'))
                    
                db.session.delete(alert)
                db.session.commit()
                flash('Price alert deleted successfully', 'success')
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error deleting price alert: {str(e)}")
                flash(f'Error deleting alert: {str(e)}', 'danger')
        
        return redirect(url_for('config.price_alerts'))
        
    # GET request - show the price alerts
    price_alerts = PriceAlert.query.all()
    telegram_configs = TelegramConfig.query.all()
    
    return render_template('price_alerts.html', price_alerts=price_alerts, telegram_configs=telegram_configs)

@config_bp.route('/logs')
def view_logs():
    """View notification logs"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    logs_query = NotificationLog.query.order_by(NotificationLog.created_at.desc())
    
    # Filter by alert if specified
    alert_id = request.args.get('alert_id')
    if alert_id:
        logs_query = logs_query.filter_by(alert_id=alert_id)
    
    # Filter by status if specified
    status = request.args.get('status')
    if status:
        logs_query = logs_query.filter_by(status=status)
    
    # Paginate the results
    logs = logs_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Get all alerts for the filter dropdown
    alerts = TradingViewAlert.query.all()
    
    return render_template('logs.html', logs=logs, alerts=alerts, current_alert_id=alert_id, current_status=status)
