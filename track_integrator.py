"""
Track Calculator Integration for SurveillanceSentry
=================================================

This module integrates the track calculator with the existing surveillance system,
providing interfaces to convert ASTERIX data to track format and update the database.

Author: Generated for SurveillanceSentry
Date: 2024
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
import sqlite3
from track_calculator import TrackCalculator, PlotData, TrackData, create_default_config
from models import Track, Event, db

logger = logging.getLogger(__name__)


class TrackIntegrator:
    """
    Integrates track calculator with the surveillance system
    """
    
    def __init__(self, db_path: str = "instance/surveillance.db"):
        """
        Initialize track integrator
        
        Args:
            db_path: Path to surveillance database
        """
        self.db_path = db_path
        self.tracker = TrackCalculator(create_default_config())
        self.last_processed_id = 0
        
        # Process existing data on startup
        self._process_existing_data()
        
        logger.info("Track integrator initialized")
    
    
    def process_new_data(self) -> Dict:
        """
        Process new surveillance data and update tracks
        
        Returns:
            Processing results summary
        """
        try:
            # Get new events from database
            new_events = self._get_new_events()
            
            if not new_events:
                return {"status": "no_new_data", "processed": 0}
            
            # Convert events to plot data
            plots = self._convert_events_to_plots(new_events)
            
            # Process plots through track calculator
            updated_tracks = self.tracker.process_plot_batch(plots)
            
            # Update database with track information
            self._update_database_tracks(updated_tracks)
            
            # Update last processed ID
            if new_events:
                self.last_processed_id = max(event.id for event in new_events)
            
            result = {
                "status": "success",
                "processed": len(plots),
                "active_tracks": len(updated_tracks),
                "summary": self.tracker.get_track_summary()
            }
            
            logger.info(f"Processed {len(plots)} plots into {len(updated_tracks)} tracks")
            return result
            
        except Exception as e:
            logger.error(f"Error processing new data: {e}")
            return {"status": "error", "error": str(e)}
    
    
    def _get_new_events(self) -> List[Event]:
        """
        Get new events from database since last processing
        
        Returns:
            List of new events
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get events newer than last processed
                cursor.execute("""
                    SELECT id, timestamp, track_id, latitude, longitude, 
                           altitude, speed, heading, event_type
                    FROM event
                    WHERE id > ? AND event_type = 'asterix_plot'
                    ORDER BY timestamp ASC
                """, (self.last_processed_id,))
                
                events = []
                for row in cursor.fetchall():
                    # Create Event-like object with required fields
                    event_data = {
                        'id': row[0],
                        'timestamp': datetime.fromisoformat(row[1]) if row[1] else datetime.now(),
                        'track_id': row[2],
                        'latitude': row[3] or 0.0,
                        'longitude': row[4] or 0.0,
                        'altitude': row[5] or 0.0,
                        'speed_ms': row[6] or 0.0,
                        'heading_deg': row[7] or 0.0,
                        'event_type': row[8] or 'asterix_plot'
                    }
                    events.append(type('Event', (), event_data)())
                
                return events
                
        except Exception as e:
            logger.error(f"Error getting new events: {e}")
            return []
    
    
    def _convert_events_to_plots(self, events: List[Event]) -> List[PlotData]:
        """
        Convert surveillance events to plot data format
        
        Args:
            events: List of surveillance events
            
        Returns:
            List of plot data objects
        """
        plots = []
        
        for event in events:
            try:
                # Calculate range and azimuth from lat/lon
                range_m, azimuth_deg = self._calculate_range_azimuth(event.latitude, event.longitude)
                
                plot = PlotData(
                    timestamp=event.timestamp,
                    range_m=range_m,
                    azimuth_deg=azimuth_deg,
                    elevation_deg=0.0,  # Not available in current data
                    latitude=event.latitude,
                    longitude=event.longitude,
                    rcs=0.0,  # Not available in current data
                    plot_id=f"event_{event.id}",
                    quality=1.0  # Default quality
                )
                plots.append(plot)
                
            except Exception as e:
                logger.warning(f"Error converting event {event.id} to plot: {e}")
                continue
        
        return plots
    
    
    def _calculate_range_azimuth(self, lat: float, lon: float) -> tuple:
        """
        Calculate range and azimuth from radar location to target
        
        Args:
            lat, lon: Target latitude and longitude
            
        Returns:
            (range_m, azimuth_deg) tuple
        """
        import math
        
        # Melbourne FL radar location
        radar_lat = 28.0836
        radar_lon = -80.6081
        
        # Earth radius in meters
        R = 6378137.0
        
        # Calculate differences
        dlat = lat - radar_lat
        dlon = lon - radar_lon
        
        # Convert to meters
        x = dlon * R * math.cos(math.radians(radar_lat)) * math.pi / 180
        y = dlat * R * math.pi / 180
        
        # Calculate range
        range_m = math.sqrt(x**2 + y**2)
        
        # Calculate azimuth (0-360 degrees, North=0)
        azimuth_deg = (math.degrees(math.atan2(x, y)) + 360) % 360
        
        return range_m, azimuth_deg
    
    
    def _update_database_tracks(self, tracks: Dict[str, TrackData]):
        """
        Update database with calculated track information
        
        Args:
            tracks: Dictionary of track data
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Update tracks table
                for track_id, track_data in tracks.items():
                    if not track_data.position_history:
                        continue
                    
                    # Get latest position
                    latest_pos = track_data.position_history[-1]
                    
                    # Convert to lat/lon
                    lat, lon = self.tracker._cartesian_to_latlon(latest_pos[0], latest_pos[1])
                    
                    # Update or insert track
                    cursor.execute("""
                        INSERT OR REPLACE INTO track (
                            track_id, latitude, longitude, speed, heading,
                            last_updated, created_at, track_type, status, callsign
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        track_id,
                        lat,
                        lon,
                        track_data.speed_ms * 1.94384,  # Convert m/s to knots
                        track_data.heading_deg,
                        track_data.last_update.isoformat(),
                        track_data.created_time.isoformat(),
                        'Aircraft',  # Default track type
                        'Active',    # Default status
                        track_id     # Use track_id as callsign for now
                    ))
                
                conn.commit()
                logger.debug(f"Updated {len(tracks)} tracks in database")
                
        except Exception as e:
            logger.error(f"Error updating database tracks: {e}")
    
    
    def get_current_tracks(self) -> List[Dict]:
        """
        Get current tracks for display
        
        Returns:
            List of track dictionaries
        """
        return self.tracker.get_tracks_for_display()
    
    
    def get_track_statistics(self) -> Dict:
        """
        Get tracking statistics
        
        Returns:
            Statistics dictionary
        """
        return self.tracker.get_track_summary()
    
    
    def reset_tracking(self):
        """
        Reset tracking state (clear all tracks)
        """
        self.tracker.active_tracks.clear()
        self.tracker.terminated_tracks.clear()
        self.last_processed_id = 0
        logger.info("Tracking state reset")
    
    
    def configure_tracker(self, config: Dict):
        """
        Update tracker configuration
        
        Args:
            config: New configuration parameters
        """
        self.tracker = TrackCalculator(config)
        logger.info(f"Tracker reconfigured with {len(config)} parameters")


    def _determine_track_type(self, track_type: str, track_id: str) -> str:
        """
        Determine the track type based on available information
        
        Args:
            track_type: Original track type from database
            track_id: Track identifier
            
        Returns:
            Standardized track type
        """
        if not track_type or track_type == 'unknown':
            # Try to determine from track ID patterns
            if track_id.startswith('ADS-B'):
                return 'aircraft'
            elif track_id.startswith('RADAR'):
                return 'radar_target'
            elif track_id.startswith('MLAT'):
                return 'multilateration'
            elif any(char.isalpha() for char in track_id):
                # If contains letters, likely an aircraft callsign
                return 'aircraft'
            else:
                return 'unknown'
        
        # Normalize existing track types
        track_type_lower = track_type.lower()
        
        if track_type_lower in ['aircraft', 'airplane', 'plane']:
            return 'aircraft'
        elif track_type_lower in ['helicopter', 'heli']:
            return 'helicopter'
        elif track_type_lower in ['vehicle', 'ground', 'car', 'truck']:
            return 'ground_vehicle'
        elif track_type_lower in ['ship', 'boat', 'vessel']:
            return 'marine'
        elif track_type_lower in ['radar', 'primary']:
            return 'radar_target'
        elif track_type_lower in ['ads-b', 'adsb']:
            return 'aircraft'
        else:
            return track_type_lower


    def _process_existing_data(self):
        """
        Process existing tracks in the database on startup
        """
        try:
            # Get all current tracks that don't have a corresponding event
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all tracks that need to be processed
                cursor.execute("""
                    SELECT track_id, latitude, longitude, altitude, speed, heading, 
                           callsign, track_type, last_updated
                    FROM track 
                    WHERE status = 'Active'
                    ORDER BY last_updated DESC
                """)
                
                tracks_data = cursor.fetchall()
                
                if not tracks_data:
                    logger.info("No existing tracks to process")
                    return
                
                # Convert track data to plots
                plots = []
                for track_data in tracks_data:
                    try:
                        track_id, lat, lon, alt, speed, heading, callsign, track_type, last_updated = track_data
                        
                        # Calculate range and azimuth
                        range_m, azimuth_deg = self._calculate_range_azimuth(lat, lon)
                        
                        # Parse timestamp
                        timestamp = datetime.fromisoformat(last_updated) if last_updated else datetime.now()
                        
                        plot = PlotData(
                            timestamp=timestamp,
                            range_m=range_m,
                            azimuth_deg=azimuth_deg,
                            elevation_deg=0.0,
                            latitude=lat,
                            longitude=lon,
                            rcs=0.0,
                            plot_id=track_id,
                            quality=1.0,
                            track_type=self._determine_track_type(track_type, track_id)
                        )
                        plots.append(plot)
                        
                    except Exception as e:
                        logger.warning(f"Error processing track data: {e}")
                        continue
                
                if plots:
                    # Process through track calculator
                    logger.info(f"Processing {len(plots)} existing tracks")
                    updated_tracks = self.tracker.process_plot_batch(plots)
                    
                    # Update last processed ID to current max
                    cursor.execute("SELECT MAX(id) FROM event")
                    max_id = cursor.fetchone()[0]
                    if max_id:
                        self.last_processed_id = max_id
                        logger.info(f"Set last processed ID to {max_id}")
                    
                    logger.info(f"Processed {len(plots)} existing tracks into {len(updated_tracks)} calculated tracks")
                else:
                    logger.info("No valid plots created from existing tracks")
                    
        except Exception as e:
            logger.error(f"Error processing existing data: {e}")

def create_database_schema():
    """
    Create or update database schema for tracking
    """
    try:
        with sqlite3.connect("instance/surveillance.db") as conn:
            cursor = conn.cursor()
            
            # Create tracks table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_id TEXT UNIQUE NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    speed_ms REAL DEFAULT 0,
                    heading_deg REAL DEFAULT 0,
                    last_seen TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    plot_count INTEGER DEFAULT 0,
                    quality_score REAL DEFAULT 0,
                    state TEXT DEFAULT 'tentative',
                    velocity_x REAL DEFAULT 0,
                    velocity_y REAL DEFAULT 0
                )
            """)
            
            # Add indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tracks_track_id ON tracks(track_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tracks_last_seen ON tracks(last_seen)
            """)
            
            conn.commit()
            logger.info("Database schema created/updated")
            
    except Exception as e:
        logger.error(f"Error creating database schema: {e}")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Create database schema
    create_database_schema()
    
    # Initialize integrator
    integrator = TrackIntegrator()
    
    # Process new data
    result = integrator.process_new_data()
    print(f"Processing result: {result}")
    
    # Get current tracks
    tracks = integrator.get_current_tracks()
    print(f"Current tracks: {len(tracks)}")
    
    # Get statistics
    stats = integrator.get_track_statistics()
    print(f"Statistics: {stats}")
