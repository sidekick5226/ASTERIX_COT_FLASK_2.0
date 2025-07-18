

import socket
import threading
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

try:
    from app_init import app, db, Event
except ImportError:
    app = None
    db = None
    Event = None

try:
    from asterix_cat48 import AsterixCAT48Processor
except ImportError:
    AsterixCAT48Processor = None

logger = logging.getLogger("udp_receiver")
logging.basicConfig(level=logging.INFO)

class UDPAsterixReceiver:
    def __init__(self, host="0.0.0.0", port=8080):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.processor = AsterixCAT48Processor() if AsterixCAT48Processor else None
        self.stats = {"messages_received": 0, "messages_processed": 0, "errors": 0}
        logger.info(f"UDPAsterixReceiver initialized on {self.host}:{self.port}")

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.running = True
        threading.Thread(target=self._receive_loop, daemon=True).start()
        logger.info(f"UDP receiver started on {self.host}:{self.port}")

    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()
        logger.info("UDP receiver stopped.")

    def _receive_loop(self):
        buffer_size = 65536
        while self.running:
            try:
                data, addr = self.socket.recvfrom(buffer_size)
                logger.info(f"Received {len(data)} bytes from {addr}")
                self.stats["messages_received"] += 1
                self._process_asterix_data(data, addr)
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                self.stats["errors"] += 1

    def _process_asterix_data(self, data: bytes, addr: tuple):
        if not data or len(data) < 3:
            logger.warning(f"Received too short message from {addr}: {len(data)} bytes")
            return
        category = data[0]
        if category == 48 and self.processor:
            try:
                targets = self.processor.process_cat48_message(data)
                logger.info(f"CAT-48 targets extracted: {targets}")
                if targets:
                    logger.info(f"Processed {len(targets)} CAT-48 plots from {addr}")
                    self._save_plots_to_db(targets)
                    self.stats["messages_processed"] += 1
                else:
                    logger.warning(f"No plots extracted from CAT-48 message from {addr}")
            except Exception as e:
                logger.error(f"Error processing CAT-48 data: {e}")
        else:
            logger.warning(f"Received unknown ASTERIX category {category} from {addr}")

    def _save_plots_to_db(self, plots: List[Dict[str, Any]]):
        if not (Event and app and db):
            logger.warning("Cannot save events - Flask dependencies not available")
            return
        for plot in plots:
            if plot.get("latitude") and plot.get("longitude"):
                try:
                    with app.app_context():
                        event = Event()
                        event.timestamp = datetime.now(timezone.utc)
                        event.track_id = plot.get("track_id", f"plot_{int(datetime.now().timestamp() * 1000000)}")
                        event.latitude = plot["latitude"]
                        event.longitude = plot["longitude"]
                        event.altitude = plot.get("altitude", 0)
                        event.speed = plot.get("speed", 0)
                        event.heading = plot.get("heading", 0)
                        event.event_type = "asterix_plot"
                        event.description = "ASTERIX CAT-48 plot from UDP receiver"
                        db.session.add(event)
                        db.session.commit()
                        logger.info(f"Added ASTERIX plot event for track integrator: {event.track_id}")
                except Exception as e:
                    logger.error(f"Error saving event to DB: {e}")
                    db.session.rollback()

udp_receiver_instance = None

def start_udp_receiver(host="0.0.0.0", port=8080):
    global udp_receiver_instance
    if udp_receiver_instance is None:
        udp_receiver_instance = UDPAsterixReceiver(host, port)
        udp_receiver_instance.start()
    return udp_receiver_instance
import socket
import threading
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

try:
    from app_init import app, db, Event
except ImportError:
    app = None
    db = None
    Event = None

try:
    from asterix_cat48 import AsterixCAT48Processor
except ImportError:
    AsterixCAT48Processor = None

logger = logging.getLogger("udp_receiver")
logging.basicConfig(level=logging.INFO)

class UDPAsterixReceiver:
    def __init__(self, host="0.0.0.0", port=8080):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.processor = AsterixCAT48Processor() if AsterixCAT48Processor else None
        self.stats = {"messages_received": 0, "messages_processed": 0, "errors": 0}
        logger.info(f"UDPAsterixReceiver initialized on {self.host}:{self.port}")

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.running = True
        threading.Thread(target=self._receive_loop, daemon=True).start()
        logger.info(f"UDP receiver started on {self.host}:{self.port}")

    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()
        logger.info("UDP receiver stopped.")

    def _receive_loop(self):
        buffer_size = 65536
        while self.running:
            try:
                data, addr = self.socket.recvfrom(buffer_size)
                logger.info(f"Received {len(data)} bytes from {addr}")
                self.stats["messages_received"] += 1
                self._process_asterix_data(data, addr)
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                self.stats["errors"] += 1

    def _process_asterix_data(self, data: bytes, addr: tuple):
        if not data or len(data) < 3:
            logger.warning(f"Received too short message from {addr}: {len(data)} bytes")
            return
        category = data[0]
        if category == 48 and self.processor:
            try:
                targets = self.processor.process_cat48_message(data)
                logger.info(f"CAT-48 targets extracted: {targets}")
                if targets:
                    logger.info(f"Processed {len(targets)} CAT-48 plots from {addr}")
                    self._save_plots_to_db(targets)
                    self.stats["messages_processed"] += 1
                else:
                    logger.warning(f"No plots extracted from CAT-48 message from {addr}")
            except Exception as e:
                logger.error(f"Error processing CAT-48 data: {e}")
        else:
            logger.warning(f"Received unknown ASTERIX category {category} from {addr}")

    def _save_plots_to_db(self, plots: List[Dict[str, Any]]):
        if not (Event and app and db):
            logger.warning("Cannot save events - Flask dependencies not available")
            return
        for plot in plots:
            if plot.get("latitude") and plot.get("longitude"):
                try:
                    with app.app_context():
                        event = Event()
                        event.timestamp = datetime.now(timezone.utc)
                        event.track_id = plot.get("track_id", f"plot_{int(datetime.now().timestamp() * 1000000)}")
                        event.latitude = plot["latitude"]
                        event.longitude = plot["longitude"]
                        event.altitude = plot.get("altitude", 0)
                        event.speed = plot.get("speed", 0)
                        event.heading = plot.get("heading", 0)
                        event.event_type = "asterix_plot"
                        event.description = "ASTERIX CAT-48 plot from UDP receiver"
                        db.session.add(event)
                        db.session.commit()
                        logger.info(f"Added ASTERIX plot event for track integrator: {event.track_id}")
                except Exception as e:
                    logger.error(f"Error saving event to DB: {e}")
                    db.session.rollback()

udp_receiver_instance = None

def start_udp_receiver(host="0.0.0.0", port=8080):
    global udp_receiver_instance
    if udp_receiver_instance is None:
        udp_receiver_instance = UDPAsterixReceiver(host, port)
        udp_receiver_instance.start()
    return udp_receiver_instance
                
                # Process ASTERIX data
                self._process_asterix_data(data, addr)
                
    
    def _process_asterix_data(self, data: bytes, addr: tuple):
        """
        Process received ASTERIX data through track calculator.
        
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
                # Use specialized CAT-48 processor to extract plot data
                targets = self.processor.process_cat48_message(data)
                
                if targets:
                    logger.info(f"Processed {len(targets)} CAT-48 plots from {addr}")
                    print(f"UDPReceiver: CAT-48 targets extracted: {targets}")
                    # Send plot data to track calculator instead of directly to database
                    self._send_plots_to_track_calculator(targets)
                    self.stats['messages_processed'] += 1
                else:
                    logger.warning(f"No plots extracted from CAT-48 message from {addr}")
                    
            else:
                # Log unknown category
                logger.warning(f"Received unknown ASTERIX category {category} from {addr}")
                
                    print(f"UDPReceiver: No plots extracted from CAT-48 message from {addr}")
        except Exception as e:
            logger.error(f"Error processing ASTERIX data from {addr}: {e}")
            self.stats['errors'] += 1
    
    def _send_plots_to_track_calculator(self, plots: List[Dict[str, Any]]):
        """
        Send plot data to the central track integrator for processing.
        
        Args:
            plots: List of plot dictionaries from ASTERIX processor
        """
        try:
            # Get the global track integrator instance
            from track_flask_integration import track_integrator
            
            if not track_integrator:
                logger.error("Track integrator not available")
                self._update_tracks(plots)
                return
            
            # Convert ASTERIX plots to database events that track integrator can process
            for plot in plots:
                if plot.get('latitude') and plot.get('longitude'):
                    # Create event record that will be picked up by track integrator
                    if self.Event and self.app and self.db:
                        try:
                            with self.app.app_context():
                                event = self.Event()
                                event.timestamp = datetime.now(timezone.utc)
                                event.track_id = plot.get('track_id', f"plot_{int(datetime.now().timestamp() * 1000000)}")
                                event.latitude = plot['latitude']
                                event.longitude = plot['longitude']
                                event.altitude = plot.get('altitude', 0)
                                event.speed = plot.get('speed', 0)
                                event.heading = plot.get('heading', 0)
                                event.event_type = 'asterix_plot'
                                event.description = f"ASTERIX CAT-48 plot from UDP receiver"
                                self.db.session.add(event)
                                self.db.session.commit()
                                
                                logger.debug(f"Added ASTERIX plot event for track integrator: {event.track_id}")
                        except Exception as e:
                            logger.error(f"Error creating event for track integrator: {e}")
                            if self.db:
                                self.db.session.rollback()
                                print(f"UDPReceiver: Added ASTERIX plot event for track integrator: {event.track_id}")
                    else:
                        logger.warning("Cannot create events - Flask dependencies not available")
            
            # Update statistics
            self.stats['tracks_updated'] += len(plots)
            logger.info(f"Sent {len(plots)} ASTERIX plots to track integrator via database events")
                
        except Exception as e:
            logger.error(f"Error sending plots to track integrator: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Fallback to direct database update if track integrator fails
            self._update_tracks(plots)
    
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
                    
            if category == 48:
                # Use specialized CAT-48 processor to extract plot data
                targets = self.processor.process_cat48_message(data)
                print(f"UDPReceiver: CAT-48 targets extracted: {targets}")
                if targets:
                    logger.info(f"Processed {len(targets)} CAT-48 plots from {addr}")
                    # Send plot data to track calculator instead of directly to database
                    self._send_plots_to_track_calculator(targets)
                    self.stats['messages_processed'] += 1
                else:
                    logger.warning(f"No plots extracted from CAT-48 message from {addr}")
                    print(f"UDPReceiver: No plots extracted from CAT-48 message from {addr}")
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
            for plot in plots:
                print(f"UDPReceiver: Processing plot for DB: {plot}")
                if plot.get('latitude') and plot.get('longitude'):
                    # Create event record that will be picked up by track integrator
                    if self.Event and self.app and self.db:
                        try:
                            with self.app.app_context():
                                event = self.Event()
                                event.timestamp = datetime.now(timezone.utc)
                                event.track_id = plot.get('track_id', f"plot_{int(datetime.now().timestamp() * 1000000)}")
                                event.latitude = plot['latitude']
                                event.longitude = plot['longitude']
                                event.altitude = plot.get('altitude', 0)
                                event.speed = plot.get('speed', 0)
                                event.heading = plot.get('heading', 0)
                                event.event_type = 'asterix_plot'
                                event.description = f"ASTERIX CAT-48 plot from UDP receiver"
                                self.db.session.add(event)
                                self.db.session.commit()
                                print(f"UDPReceiver: Added ASTERIX plot event for track integrator: {event.track_id}")
                                logger.debug(f"Added ASTERIX plot event for track integrator: {event.track_id}")
                        except Exception as e:
                            logger.error(f"Error creating event for track integrator: {e}")
                            if self.db:
                                self.db.session.rollback()
                    else:
                        logger.warning("Cannot create events - Flask dependencies not available")
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
