import os
import logging
from flask import Flask
from flask_socketio import SocketIO
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

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
from models import db, User
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

socketio = SocketIO(app, cors_allowed_origins="*", logger=False, engineio_logger=False, ping_timeout=180, ping_interval=60, async_mode='threading')

def create_default_user():
    """Create default user if none exists"""
    if not User.query.first():
        default_user = User(username='user')
        default_user.set_password('pass')
        db.session.add(default_user)
        db.session.commit()
        print("Default user created: username='user', password='pass'")

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()
    create_default_user()

# Import routes
import routes

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
