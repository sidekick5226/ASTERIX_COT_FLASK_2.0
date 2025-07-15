#!/usr/bin/env python3
"""
Test Track Calculator Flask Integration
"""

from app_init import app
from track_flask_integration import track_integrator
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info('Testing Flask integration with track calculator')

with app.app_context():
    try:
        # Check if track integrator is working
        if track_integrator:
            stats = track_integrator.get_track_statistics()
            logger.info(f'Track statistics: {stats}')
            
            current_tracks = track_integrator.get_current_tracks()
            logger.info(f'Current tracks: {len(current_tracks)}')
            
            # Test the API endpoint
            with app.test_client() as client:
                # Login first
                login_response = client.post('/login', data={'username': 'user', 'password': 'pass'})
                logger.info(f'Login response status: {login_response.status_code}')
                
                # Get tracks via API
                response = client.get('/api/tracks/current')
                logger.info(f'API response status: {response.status_code}')
                
                if response.status_code == 200:
                    data = response.get_json()
                    logger.info(f'API returned {data["count"]} tracks')
                    logger.info('SUCCESS: Flask integration working correctly')
                else:
                    logger.error(f'API error: {response.get_data(as_text=True)}')
        else:
            logger.error('Track integrator not initialized')
            
    except Exception as e:
        logger.error(f'Error: {e}')
        import traceback
        traceback.print_exc()
