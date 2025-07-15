from app import app, socketio
from models import db, Track, Event
from udp_receiver import start_udp_receiver
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_services():
    """Initialize all services including UDP receiver"""
    logger.info("Initializing services...")
    
    # Start UDP receiver with Flask dependencies
    if start_udp_receiver(app=app, db=db, socketio=socketio, Track=Track, Event=Event):
        logger.info("UDP receiver started successfully")
    else:
        logger.warning("Failed to start UDP receiver")
    
    logger.info("Services initialization complete")

if __name__ == '__main__':
    # Initialize services before starting the app
    initialize_services()
    
    logger.info("Starting Surveillance Sentry Flask application...")
    logger.info("Access the application at: http://localhost:5000")
    logger.info("UDP receiver listening on: 0.0.0.0:8080")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
