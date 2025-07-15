"""
UDP Receiver for ASTERIX CAT-48 Data
Receives ASTERIX data from Colasoft Packet Player and processes it through the surveillance system.
"""

import socket
import threading
import time
import struct
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from asterix_cat48 import AsterixCAT48Processor
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UDPAsterixReceiver:
    """
    UDP receiver for ASTERIX CAT-48 data from Colasoft Packet Player.
    """
    
    def __init__(self, host='0.0.0.0', port=8080, app=None, db=None, socketio=None, Track=None, Event=None):
        """
        Initialize UDP receiver.
        
        Args:
            host: IP address to bind to (default: all interfaces)
            port: Port to listen on (default: 8080)
            app: Flask app instance (optional)
            db: SQLAlchemy database instance (optional)
            socketio: SocketIO instance (optional)
            Track: Track model class (optional)
            Event: Event model class (optional)
        """
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.receive_thread = None
        self.processor = AsterixCAT48Processor()
        
        # Flask dependencies (optional)
        self.app = app
        self.db = db
        self.socketio = socketio
        self.Track = Track
        self.Event = Event
        
        # Statistics
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'tracks_updated': 0,
            'errors': 0,
            'start_time': None,
            'last_message_time': None
        }
        
        # Track cache for performance
        self.track_cache = {}
        
    def start(self):
        """Start the UDP receiver."""
        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.settimeout(1.0)  # 1 second timeout for clean shutdown
            
            self.running = True
            self.stats['start_time'] = datetime.now(timezone.utc)
            
            # Start receive thread
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            logger.info(f"UDP ASTERIX receiver started on {self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start UDP receiver: {e}")
            return False
    
    def stop(self):
        """Stop the UDP receiver."""
        try:
            self.running = False
            
            if self.socket:
                self.socket.close()
                self.socket = None
            
            if self.receive_thread and self.receive_thread.is_alive():
                self.receive_thread.join(timeout=5)
            
            logger.info("UDP ASTERIX receiver stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping UDP receiver: {e}")
            return False
    
    def _receive_loop(self):
        """Main receive loop for UDP data."""
        buffer_size = 65536  # 64KB buffer
        
        logger.info(f"UDP receiver listening on {self.host}:{self.port}")
        logger.info("Waiting for ASTERIX data...")
        
        while self.running:
            try:
                # Check if socket is still valid
                if not self.socket:
                    logger.error("Socket is None, stopping receive loop")
                    break
                
                # Receive UDP data
                data, addr = self.socket.recvfrom(buffer_size)
                
                if not data:
                    continue
                
                logger.info(f"Received {len(data)} bytes from {addr}")
                logger.debug(f"Raw data: {data[:50].hex()}")  # First 50 bytes in hex
                
                self.stats['messages_received'] += 1
                self.stats['last_message_time'] = datetime.now(timezone.utc)
                
                # Process ASTERIX data
                self._process_asterix_data(data, addr)
                
            except socket.timeout:
                continue  # Normal timeout, continue loop
            except OSError as e:
                if self.running:
                    logger.warning(f"Socket/OS error: {e}")
                    # Check if socket is still valid
                    if not self.socket:
                        logger.error("Socket became None during operation")
                        break
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Unexpected error in receive loop: {e}")
                self.stats['errors'] += 1
                time.sleep(0.1)
    
    def _process_asterix_data(self, data: bytes, addr: tuple):
        """
        Process received ASTERIX data.
        
        Args:
            data: Raw ASTERIX data
            addr: Source address (IP, port)
        """
        try:
            # Check if this looks like ASTERIX data
            if len(data) < 3:
                logger.warning(f"Received too short message from {addr}: {len(data)} bytes")
                return
            
            # Extract category from first byte
            category = data[0]
            
            # Process based on category
            if category == 48:
                # Use specialized CAT-48 processor
                targets = self.processor.process_cat48_message(data)
                
                if targets:
                    logger.info(f"Processed {len(targets)} CAT-48 targets from {addr}")
                    
                    # Debug: Log the first target's data
                    if targets and logger.isEnabledFor(logging.DEBUG):
                        first_target = targets[0]
                        logger.debug(f"First target data: {first_target}")
                        logger.debug(f"  Track ID: {first_target.get('track_id')}")
                        logger.debug(f"  Coordinates: lat={first_target.get('latitude')}, lon={first_target.get('longitude')}")
                        logger.debug(f"  Data items: {first_target.get('data_items', {})}")
                    
                    self._update_tracks(targets)
                    self.stats['messages_processed'] += 1
                else:
                    logger.warning(f"No targets extracted from CAT-48 message from {addr}")
                    logger.debug(f"Raw message data: {data.hex()}")
                    
                    # Try to extract basic info for debugging
                    if len(data) >= 3:
                        category = data[0]
                        length = struct.unpack('>H', data[1:3])[0]
                        logger.debug(f"Message: category={category}, length={length}, actual_length={len(data)}")
                    
            else:
                # Log unknown category
                logger.warning(f"Received unknown ASTERIX category {category} from {addr}")
                
        except Exception as e:
            logger.error(f"Error processing ASTERIX data from {addr}: {e}")
            self.stats['errors'] += 1
    
    def _update_tracks(self, targets: List[Dict[str, Any]]):
        """
        Update database tracks from processed targets.
        
        Args:
            targets: List of processed target dictionaries
        """
        # Skip database updates if Flask dependencies are not available
        if not self.app or not self.db or not self.Track:
            logger.warning("Flask dependencies not available - skipping database update")
            logger.info(f"Received {len(targets)} targets:")
            for i, target in enumerate(targets):
                logger.info(f"  Target {i+1}: {target}")
            return
            
        try:
            # Ensure we have Flask app context
            if not self.app.app_context:
                logger.warning("No Flask app context available - running in standalone mode")
                return
                
            with self.app.app_context():
                updated_tracks = []
                
                for target in targets:
                    target_id = target.get('track_id')
                    if not target_id:
                        logger.warning(f"Target missing track_id: {target}")
                        continue
                    
                    # Find existing track or create new one
                    track = self.Track.query.filter_by(track_id=str(target_id)).first()
                    if not track:
                        # Ensure required fields have valid defaults
                        lat = target.get('latitude', 0.0)
                        lon = target.get('longitude', 0.0)
                        
                        # Handle None values and provide sensible defaults
                        if lat is None:
                            lat = 0.0
                        if lon is None:
                            lon = 0.0
                            
                        # Log the extracted data for debugging
                        logger.debug(f"Creating new track {target_id}: lat={lat}, lon={lon}")
                        logger.debug(f"Full target data: {target}")
                            
                        track = self.Track()
                        track.track_id = str(target_id)
                        track.track_type = self._determine_track_type(target)
                        track.latitude = lat
                        track.longitude = lon
                        self.db.session.add(track)
                    else:
                        logger.debug(f"Updating existing track {target_id}")
                    
                    # Update track attributes with safe defaults
                    track.callsign = target.get('callsign') or track.callsign
                    track.track_type = self._determine_track_type(target) or track.track_type
                    
                    # Update coordinates with safe defaults
                    if target.get('latitude') is not None:
                        track.latitude = target.get('latitude')
                    if target.get('longitude') is not None:
                        track.longitude = target.get('longitude')
                    
                    # Update other optional fields with safe type checking
                    altitude = target.get('altitude')
                    if altitude is not None:
                        try:
                            track.altitude = float(altitude)
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid altitude value: {altitude}")
                    
                    heading = target.get('heading')
                    if heading is not None:
                        try:
                            track.heading = float(heading)
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid heading value: {heading}")
                    
                    speed = target.get('speed')
                    if speed is not None:
                        try:
                            track.speed = float(speed)
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid speed value: {speed}")
                    
                    track.status = 'Active'
                    track.last_updated = datetime.now(timezone.utc)
                    
                    updated_tracks.append(track)
                
                # Commit all changes
                self.db.session.commit()
                
                # Update statistics
                self.stats['tracks_updated'] += len(updated_tracks)
                
                # Broadcast updates via WebSocket if available
                if updated_tracks and self.socketio:
                    track_data = [track.to_dict() for track in updated_tracks]
                    self.socketio.emit('track_update', track_data)
                    
                    # Log track update event if Event model is available
                    if self.Event:
                        event = self.Event()
                        event.track_id = str(updated_tracks[0].track_id)
                        event.event_type = 'track_update'
                        event.description = f'Updated {len(updated_tracks)} tracks from ASTERIX CAT-48'
                        self.db.session.add(event)
                        self.db.session.commit()
                
        except Exception as e:
            logger.error(f"Error updating tracks: {e}")
            logger.error(f"Target data that caused error: {targets}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            try:
                if self.db:
                    self.db.session.rollback()
            except:
                pass  # Ignore rollback errors if no session
    
    def _determine_track_type(self, target: Dict[str, Any]) -> str:
        """
        Determine track type from ASTERIX data.
        
        Args:
            target: Target dictionary
            
        Returns:
            Track type string
        """
        # Check flight status or other indicators
        flight_status = target.get('flight_status', '')
        if 'ground' in flight_status.lower():
            return 'Ground Vehicle'
        elif 'airborne' in flight_status.lower():
            return 'Aircraft'
        else:
            # Safe altitude check - handle None values
            altitude = target.get('altitude')
            if altitude is not None and altitude > 100:
                return 'Aircraft'
            else:
                return 'Unknown'
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get receiver statistics."""
        stats = self.stats.copy()
        stats['running'] = self.running
        stats['uptime'] = None
        
        if stats['start_time']:
            uptime = datetime.now(timezone.utc) - stats['start_time']
            stats['uptime'] = str(uptime)
        
        return stats
    
    def reset_statistics(self):
        """Reset receiver statistics."""
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'tracks_updated': 0,
            'errors': 0,
            'start_time': datetime.now(timezone.utc) if self.running else None,
            'last_message_time': None
        }
    
    def is_running(self):
        """
        Check if the UDP receiver is running.
        
        Returns:
            bool: True if running, False otherwise
        """
        return self.running and self.receive_thread and self.receive_thread.is_alive()
    
    def get_stats(self):
        """
        Get current statistics.
        
        Returns:
            dict: Current statistics including uptime
        """
        stats = self.stats.copy()
        if self.stats['start_time']:
            uptime = (datetime.now(timezone.utc) - self.stats['start_time']).total_seconds()
            stats['uptime'] = uptime
        else:
            stats['uptime'] = 0
        return stats

# Global receiver instance for the Flask app
_global_receiver = None

def start_udp_receiver(app=None, db=None, socketio=None, Track=None, Event=None):
    """
    Start the global UDP receiver instance.
    
    Args:
        app: Flask app instance (optional)
        db: SQLAlchemy database instance (optional)
        socketio: SocketIO instance (optional)
        Track: Track model class (optional)
        Event: Event model class (optional)
    
    Returns:
        bool: True if started successfully, False otherwise
    """
    global _global_receiver
    
    try:
        if _global_receiver is None:
            _global_receiver = UDPAsterixReceiver(
                app=app, db=db, socketio=socketio, Track=Track, Event=Event
            )
        
        if not _global_receiver.is_running():
            _global_receiver.start()
            return True
        else:
            logger.warning("UDP receiver is already running")
            return False
            
    except Exception as e:
        logger.error(f"Failed to start UDP receiver: {e}")
        return False

def stop_udp_receiver():
    """
    Stop the global UDP receiver instance.
    
    Returns:
        bool: True if stopped successfully, False otherwise
    """
    global _global_receiver
    
    try:
        if _global_receiver and _global_receiver.is_running():
            _global_receiver.stop()
            return True
        else:
            logger.warning("UDP receiver is not running")
            return False
            
    except Exception as e:
        logger.error(f"Failed to stop UDP receiver: {e}")
        return False

def get_udp_receiver_status():
    """
    Get the status of the global UDP receiver instance.
    
    Returns:
        dict: Status information including running state and statistics
    """
    global _global_receiver
    
    if _global_receiver:
        return {
            'running': _global_receiver.is_running(),
            'stats': _global_receiver.get_stats(),
            'port': _global_receiver.port,
            'host': _global_receiver.host
        }
    else:
        return {
            'running': False,
            'stats': {
                'messages_received': 0,
                'messages_processed': 0,
                'tracks_updated': 0,
                'errors': 0,
                'start_time': None,
                'uptime': 0
            },
            'port': 8080,
            'host': '0.0.0.0'
        }

# Test function
if __name__ == '__main__':
    # Test with sample data - standalone mode
    logger.info("Starting UDP ASTERIX receiver test...")
    
    # Create a standalone receiver that doesn't use Flask app context
    receiver = UDPAsterixReceiver()
    
    if receiver.start():
        logger.info("UDP receiver started successfully")
        
        try:
            # Keep running
            while True:
                time.sleep(5)
                stats = receiver.get_stats()
                logger.info(f"Stats: received={stats['messages_received']}, "
                           f"processed={stats['messages_processed']}, "
                           f"errors={stats['errors']}")
                
        except KeyboardInterrupt:
            logger.info("Stopping UDP receiver...")
            receiver.stop()
            logger.info("UDP receiver stopped")
    else:
        logger.error("Failed to start UDP receiver")
