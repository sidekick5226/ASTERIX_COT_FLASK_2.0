import os
import logging
from flask import Flask
from flask_socketio import SocketIO
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "surveillance_secret_key_2025")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///surveillance.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Import models and initialize database
from models import db, User, Track, Event
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
setattr(login_manager, 'login_view', 'login')
setattr(login_manager, 'login_message', 'Please log in to access this page.')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

socketio = SocketIO(app, cors_allowed_origins="*", logger=False, engineio_logger=False, ping_timeout=180, ping_interval=60, async_mode='threading')

def create_default_user():
    """Create default user if none exists"""
    if not User.query.first():
        default_user = User()
        default_user.username = 'user'
        default_user.set_password('pass')
        db.session.add(default_user)
        db.session.commit()

def initialize_udp_receiver():
    """Initialize UDP receiver with Flask app dependencies"""
    from udp_receiver import start_udp_receiver
    logger = logging.getLogger(__name__)
    
    try:
        if start_udp_receiver(app=app, db=db, socketio=socketio, Track=Track, Event=Event):
            logger.info("UDP receiver started successfully on port 8080")
        else:
            logger.warning("Failed to start UDP receiver")
    except Exception as e:
        logger.error(f"Error starting UDP receiver: {e}")

def initialize_track_calculator():
    """Initialize track calculator with Flask app dependencies"""
    logger = logging.getLogger(__name__)
    
    try:
        from track_flask_integration import initialize_track_calculator_app
        if initialize_track_calculator_app(app):
            logger.info("Track calculator initialized successfully")
        else:
            logger.warning("Failed to initialize track calculator")
    except Exception as e:
        logger.error(f"Error initializing track calculator: {e}")

# Initialize database and create default user
with app.app_context():
    db.create_all()
    create_default_user()
    # Start UDP receiver automatically
    initialize_udp_receiver()
    # Initialize track calculator
    initialize_track_calculator()
