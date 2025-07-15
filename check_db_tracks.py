#!/usr/bin/env python3
"""
Database Track Analysis Script
Check the current state of tracks and events in the database
"""

import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database():
    """Check database structure and current data"""
    try:
        conn = sqlite3.connect('instance/surveillance.db')
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
        tables = cursor.fetchall()
        logger.info(f'Tables: {[table[0] for table in tables]}')
        
        # Check tracks table structure
        cursor.execute('PRAGMA table_info(track)')
        track_schema = cursor.fetchall()
        logger.info(f'Track table schema: {track_schema}')
        
        # Check number of tracks
        cursor.execute('SELECT COUNT(*) FROM track')
        track_count = cursor.fetchone()[0]
        logger.info(f'Total tracks: {track_count}')
        
        # Check recent tracks
        cursor.execute('SELECT track_id, callsign, latitude, longitude, last_updated, status FROM track ORDER BY last_updated DESC LIMIT 10')
        recent_tracks = cursor.fetchall()
        logger.info(f'Recent tracks: {recent_tracks}')
        
        # Check events table
        cursor.execute('SELECT COUNT(*) FROM event')
        event_count = cursor.fetchone()[0]
        logger.info(f'Total events: {event_count}')
        
        # Check recent events
        cursor.execute('SELECT id, timestamp, track_id FROM event ORDER BY timestamp DESC LIMIT 10')
        recent_events = cursor.fetchall()
        logger.info(f'Recent events: {recent_events}')
        
        # Check for orphaned tracks (tracks without recent events)
        cursor.execute('''
            SELECT t.track_id, t.status, t.last_updated, 
                   MAX(e.timestamp) as last_event
            FROM track t
            LEFT JOIN event e ON t.track_id = e.track_id
            WHERE t.status = 'Active'
            GROUP BY t.track_id
            ORDER BY t.last_updated DESC
            LIMIT 20
        ''')
        active_tracks = cursor.fetchall()
        logger.info(f'Active tracks with event info: {active_tracks}')
        
        conn.close()
        
    except Exception as e:
        logger.error(f'Database check error: {e}')

if __name__ == "__main__":
    check_database()
