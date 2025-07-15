"""
Flask Integration for Track Calculator
=====================================

This module integrates the track calculator with the Flask surveillance application,
providing API endpoints for real-time tracking updates.

Author: Generated for SurveillanceSentry
Date: 2024
"""

import logging
from flask import jsonify, request
from datetime import datetime
from track_integrator import TrackIntegrator, create_database_schema
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global track integrator instance
track_integrator = None
background_thread = None
background_running = False


def initialize_tracking():
    """
    Initialize the tracking system
    """
    global track_integrator
    
    try:
        # Create database schema
        create_database_schema()
        
        # Initialize track integrator
        track_integrator = TrackIntegrator()
        
        logger.info("Track calculator initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize track calculator: {e}")
        return False


def background_tracking_worker():
    """
    Background worker for continuous track processing
    """
    global track_integrator, background_running
    
    logger.info("Background tracking worker started")
    
    while background_running:
        try:
            if track_integrator:
                # Process new data
                result = track_integrator.process_new_data()
                
                if result['status'] == 'success' and result['processed'] > 0:
                    logger.info(f"Processed {result['processed']} plots, "
                               f"Active tracks: {result['active_tracks']}")
                
        except Exception as e:
            logger.error(f"Background tracking error: {e}")
        
        # Sleep for 1 second before next processing cycle
        time.sleep(1.0)
    
    logger.info("Background tracking worker stopped")


def start_background_tracking():
    """
    Start background tracking thread
    """
    global background_thread, background_running
    
    if background_thread and background_thread.is_alive():
        return
    
    background_running = True
    background_thread = threading.Thread(target=background_tracking_worker, daemon=True)
    background_thread.start()
    
    logger.info("Background tracking started")


def stop_background_tracking():
    """
    Stop background tracking thread
    """
    global background_running
    
    background_running = False
    if background_thread:
        background_thread.join(timeout=2.0)
    
    logger.info("Background tracking stopped")


def setup_track_calculator_routes(app):
    """
    Setup Flask routes for track calculator
    
    Args:
        app: Flask application instance
    """
    
    # Check if routes are already registered
    if '/api/tracks/current' in [rule.rule for rule in app.url_map.iter_rules()]:
        logger.info("Track calculator routes already registered, skipping")
        return
    
    @app.route('/api/tracks/current')
    def get_current_calculated_tracks():
        """
        Get current active tracks from track calculator
        """
        try:
            if not track_integrator:
                return jsonify({'error': 'Track calculator not initialized'}), 500
            
            tracks = track_integrator.get_current_tracks()
            return jsonify({
                'success': True,
                'tracks': tracks,
                'count': len(tracks),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting current tracks: {e}")
            return jsonify({'error': str(e)}), 500
    
    
    @app.route('/api/tracks/statistics')
    def get_track_statistics():
        """
        Get tracking statistics
        """
        try:
            if not track_integrator:
                return jsonify({'error': 'Track calculator not initialized'}), 500
            
            stats = track_integrator.get_track_statistics()
            return jsonify({
                'success': True,
                'statistics': stats,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting track statistics: {e}")
            return jsonify({'error': str(e)}), 500
    
    
    @app.route('/api/tracks/process', methods=['POST'])
    def process_tracks():
        """
        Manually trigger track processing
        """
        try:
            if not track_integrator:
                return jsonify({'error': 'Track calculator not initialized'}), 500
            
            result = track_integrator.process_new_data()
            return jsonify({
                'success': True,
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error processing tracks: {e}")
            return jsonify({'error': str(e)}), 500
    
    
    @app.route('/api/tracks/reset', methods=['POST'])
    def reset_tracking():
        """
        Reset tracking state
        """
        try:
            if not track_integrator:
                return jsonify({'error': 'Track calculator not initialized'}), 500
            
            track_integrator.reset_tracking()
            return jsonify({
                'success': True,
                'message': 'Tracking state reset',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error resetting tracking: {e}")
            return jsonify({'error': str(e)}), 500
    
    
    @app.route('/api/tracks/config', methods=['GET', 'POST'])
    def track_config():
        """
        Get or update tracking configuration
        """
        try:
            if not track_integrator:
                return jsonify({'error': 'Track calculator not initialized'}), 500
            
            if request.method == 'GET':
                # Return current configuration
                return jsonify({
                    'success': True,
                    'config': track_integrator.tracker.config,
                    'timestamp': datetime.now().isoformat()
                })
            
            elif request.method == 'POST':
                # Update configuration
                new_config = request.get_json()
                if not new_config:
                    return jsonify({'error': 'No configuration provided'}), 400
                
                track_integrator.configure_tracker(new_config)
                return jsonify({
                    'success': True,
                    'message': 'Configuration updated',
                    'config': new_config,
                    'timestamp': datetime.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Error with track config: {e}")
            return jsonify({'error': str(e)}), 500
    
    
    @app.route('/api/tracks/status')
    def get_tracking_status():
        """
        Get tracking system status
        """
        try:
            global background_running
            
            if not track_integrator:
                return jsonify({
                    'success': False,
                    'initialized': False,
                    'background_running': False,
                    'error': 'Track calculator not initialized'
                })
            
            stats = track_integrator.get_track_statistics()
            
            return jsonify({
                'success': True,
                'initialized': True,
                'background_running': background_running,
                'active_tracks': stats['active_tracks'],
                'terminated_tracks': stats['terminated_tracks'],
                'statistics': stats['statistics'],
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting tracking status: {e}")
            return jsonify({'error': str(e)}), 500


def initialize_track_calculator_app(app):
    """
    Initialize track calculator integration with Flask app
    
    Args:
        app: Flask application instance
    """
    logger.info("Initializing track calculator integration")
    
    # Initialize tracking system
    if not initialize_tracking():
        logger.error("Failed to initialize tracking system")
        return False
    
    # Setup routes
    setup_track_calculator_routes(app)
    
    # Start background processing
    start_background_tracking()
    
    logger.info("Track calculator integration initialized successfully")
    return True


# Example usage in your main Flask app
if __name__ == "__main__":
    from flask import Flask
    
    # Create Flask app
    app = Flask(__name__)
    
    # Initialize track calculator
    if initialize_track_calculator_app(app):
        logger.info("Track calculator ready")
        
        # Add a simple status endpoint
        @app.route('/')
        def index():
            return jsonify({
                'service': 'SurveillanceSentry Track Calculator',
                'status': 'running',
                'endpoints': [
                    '/api/tracks/current',
                    '/api/tracks/statistics', 
                    '/api/tracks/process',
                    '/api/tracks/reset',
                    '/api/tracks/config',
                    '/api/tracks/status'
                ]
            })
        
        # Run Flask app
        app.run(debug=True, host='0.0.0.0', port=5001)
    else:
        logger.error("Failed to initialize track calculator")
