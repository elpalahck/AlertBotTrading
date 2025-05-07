from datetime import datetime
from app import db

class TelegramConfig(db.Model):
    """Model for storing Telegram bot configuration"""
    id = db.Column(db.Integer, primary_key=True)
    bot_token = db.Column(db.String(100), nullable=False)
    chat_id = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<TelegramConfig {self.id}>'

class TradingViewAlert(db.Model):
    """Model for storing TradingView alert configurations"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    webhook_key = db.Column(db.String(50), nullable=False, unique=True)
    message_template = db.Column(db.Text, nullable=False, 
                               default="TradingView Alert: {{strategy}} - {{ticker}} - {{close}}")
    is_active = db.Column(db.Boolean, default=True)
    telegram_config_id = db.Column(db.Integer, db.ForeignKey('telegram_config.id'), nullable=False)
    telegram_config = db.relationship('TelegramConfig', backref=db.backref('tradingview_alerts', lazy=True))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<TradingViewAlert {self.name}>'

class PriceAlert(db.Model):
    """Model for storing price-based alerts"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(30), nullable=False)  # Trading symbol (e.g., SPX, AAPL)
    alert_type = db.Column(db.String(20), nullable=False)  # above, below
    target_price = db.Column(db.Float, nullable=False)
    message_template = db.Column(db.Text, nullable=False, 
                              default="Alerta de precio: {{symbol}} ha alcanzado {{current_price}}, objetivo: {{target_price}}")
    is_active = db.Column(db.Boolean, default=True)
    is_one_time = db.Column(db.Boolean, default=False)  # Whether the alert triggers only once
    is_triggered = db.Column(db.Boolean, default=False)  # Whether a one-time alert has been triggered
    last_triggered_at = db.Column(db.DateTime, nullable=True)  # When the alert was last triggered
    telegram_config_id = db.Column(db.Integer, db.ForeignKey('telegram_config.id'), nullable=False)
    telegram_config = db.relationship('TelegramConfig', backref=db.backref('price_alerts', lazy=True))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<PriceAlert {self.name} - {self.symbol} {self.alert_type} {self.target_price}>'

class NotificationLog(db.Model):
    """Model for logging notification history"""
    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.Integer, db.ForeignKey('trading_view_alert.id', name='fk_alert_id'), nullable=True)
    alert = db.relationship('TradingViewAlert', backref=db.backref('logs', lazy=True), foreign_keys=[alert_id])
    price_alert_id = db.Column(db.Integer, db.ForeignKey('price_alert.id', name='fk_price_alert_id'), nullable=True)
    price_alert = db.relationship('PriceAlert', backref=db.backref('logs', lazy=True), foreign_keys=[price_alert_id])
    payload = db.Column(db.Text, nullable=True)
    message_sent = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False)  # success, failed
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<NotificationLog {self.id} - {self.status}>'
