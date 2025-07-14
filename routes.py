from flask import render_template, request, jsonify
from flask_socketio import emit
from app import app, socketio
from models import Track, Event, NetworkConfig, db
from datetime import datetime, timedelta
import json
import math
import random
import threading
import time
import csv
import os
import schedule
from asterix_processor import AsterixProcessor
from cot_converter import CoTConverter
from klv_converter import KLVConverter
from cot_processor import CoTProcessor

# Initialize processors
asterix_processor = AsterixProcessor()
cot_converter = CoTConverter()
klv_converter = KLVConverter()
cot_processor = CoTProcessor()

# Ensure export directory exists
EXPORT_DIR = os.path.join(os.path.dirname(__file__), 'export_log_hist')
os.makedirs(EXPORT_DIR, exist_ok=True)

def export_event_log_to_csv(clear_after_export=False):
    """Export all events to CSV with optional clearing"""
    try:
        # Get current date and time for filename to avoid overwriting
        current_datetime = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"event_log_{current_datetime}.csv"
        filepath = os.path.join(EXPORT_DIR, filename)
        
        # Get all events from the database
        events = Event.query.order_by(Event.timestamp.asc()).all()
        
        if events:
            # Write events to CSV
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['id', 'track_id', 'event_type', 'description', 'timestamp']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header
                writer.writeheader()
                
                # Write event data
                for event in events:
                    writer.writerow({
                        'id': event.id,
                        'track_id': event.track_id,
                        'event_type': event.event_type,
                        'description': event.description,
                        'timestamp': event.timestamp.isoformat() if event.timestamp else ''
                    })
            
            # Clear all events from database after successful export (only if requested)
            if clear_after_export:
                Event.query.delete()
                db.session.commit()
                print(f"Successfully exported {len(events)} events to {filepath} and cleared event log")
            else:
                print(f"Successfully exported {len(events)} events to {filepath} (log not cleared)")
            
            return filepath
            
        else:
            print(f"No events to export at {current_datetime}")
            return None
            
    except Exception as e:
        print(f"Error during event log export: {e}")
        db.session.rollback()
        return None

def export_daily_event_log():
    """Export all events to CSV and clear the event log (runs daily at midnight)"""
    result = export_event_log_to_csv(clear_after_export=True)
    return result is not None

def start_daily_export_scheduler():
    """Start the background scheduler for daily event log exports"""
    # Schedule daily export at midnight
    schedule.every().day.at("00:00").do(export_daily_event_log)
    
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    # Start scheduler in background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("Daily event log export scheduler started (runs at midnight)")

# Start the scheduler when the module loads
start_daily_export_scheduler()

@app.route('/')
def dashboard():
    """Main dashboard route"""
    return render_template('dashboard.html')

@app.route('/api/tracks')
def get_tracks():
    """Get all active tracks"""
    track_type = request.args.get('type', '')
    query = Track.query.filter_by(status='Active')
    
    if track_type:
        query = query.filter_by(track_type=track_type)
    
    tracks = query.all()
    return jsonify([track.to_dict() for track in tracks])

@app.route('/api/tracks/<track_id>')
def get_track(track_id):
    """Get specific track by ID"""
    track = Track.query.filter_by(track_id=track_id).first()
    if track:
        return jsonify(track.to_dict())
    return jsonify({'error': 'Track not found'}), 404

@app.route('/api/tracks/clear', methods=['POST'])
def clear_tracks():
    """Clear all tracks from the system"""
    try:
        # Delete all tracks
        Track.query.delete()
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'All tracks cleared'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/tracks/generate', methods=['POST'])
def generate_tracks():
    """Generate new simulated tracks"""
    try:
        # Clear existing tracks first
        Track.query.delete()
        
        # Generate new tracks
        generate_simulated_track_data()
        
        return jsonify({
            'status': 'success',
            'message': 'New tracks generated'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/events')
def get_events():
    """Get all events for Event Log with optional filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    event_type = request.args.get('event_type')
    
    # Build query with filters
    query = Event.query
    
    # Apply date filters
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date.replace('T', ' '))
            query = query.filter(Event.timestamp >= start_datetime)
        except ValueError:
            pass  # Invalid date format, ignore filter
    
    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date.replace('T', ' '))
            query = query.filter(Event.timestamp <= end_datetime)
        except ValueError:
            pass  # Invalid date format, ignore filter
    
    # Apply event type filter
    if event_type:
        query = query.filter(Event.event_type == event_type)
    
    # Execute query with pagination
    events = query.order_by(Event.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'events': [event.to_dict() for event in events.items],
        'total': events.total,
        'pages': events.pages,
        'current_page': page,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'event_type': event_type
        }
    })

@app.route('/api/monitor-events')
def get_monitor_events():
    """Get real-time monitor events for Event Monitor"""
    try:
        # Get active tracks and generate current monitor events
        tracks = Track.query.filter_by(status='Active').all()
        monitor_events = []
        
        from datetime import datetime
        current_time = datetime.utcnow().isoformat()
        
        for track in tracks:
            monitor_event = {
                'track_id': track.track_id,
                'event_type': 'Track Update',
                'track_type': track.track_type,
                'latitude': round(track.latitude, 4),
                'longitude': round(track.longitude, 4),
                'speed': round(track.speed, 1) if track.speed else 0,
                'altitude': round(track.altitude, 0) if track.altitude else 0,
                'timestamp': current_time,
                'is_realtime': True
            }
            monitor_events.append(monitor_event)
        
        return jsonify({
            'status': 'success',
            'events': monitor_events,
            'count': len(monitor_events)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'events': [],
            'count': 0
        }), 500

@app.route('/api/network-config', methods=['GET', 'POST'])
def network_config():
    """Get or update network configuration"""
    if request.method == 'POST':
        data = request.get_json()
        config = NetworkConfig.query.first()
        
        if not config:
            config = NetworkConfig()
            db.session.add(config)
        
        config.protocol = data.get('protocol', config.protocol)
        config.port = data.get('port', config.port)
        config.ip_address = data.get('ip_address', config.ip_address)
        config.is_active = data.get('is_active', config.is_active)
        
        db.session.commit()
        return jsonify({'success': True})
    
    config = NetworkConfig.query.first()
    if config:
        return jsonify({
            'protocol': config.protocol,
            'port': config.port,
            'ip_address': config.ip_address,
            'is_active': config.is_active
        })
    
    return jsonify({
        'protocol': 'TCP',
        'port': 8080,
        'ip_address': '127.0.0.1',
        'is_active': True
    })

@app.route('/api/export-events', methods=['POST'])
def manual_export_events():
    """Manually trigger event log export (does NOT clear the log)"""
    try:
        result = export_event_log_to_csv(clear_after_export=False)
        if result:
            return jsonify({
                'status': 'success',
                'message': 'Event log exported successfully (log not cleared)',
                'file_path': result
            })
        else:
            return jsonify({
                'status': 'success',
                'message': 'No events to export'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/export-history')
def get_export_history():
    """Get list of exported event log files"""
    try:
        files = []
        if os.path.exists(EXPORT_DIR):
            for filename in os.listdir(EXPORT_DIR):
                if filename.startswith('event_log_') and filename.endswith('.csv'):
                    filepath = os.path.join(EXPORT_DIR, filename)
                    stat = os.stat(filepath)
                    files.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        # Sort by creation date, newest first
        files.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({
            'status': 'success',
            'files': files,
            'export_directory': EXPORT_DIR
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('status', {'msg': 'Connected to surveillance system'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

@socketio.on('request_track_update')
def handle_track_update_request():
    """Handle request for track updates"""
    tracks = Track.query.filter_by(status='Active').all()
    emit('track_update', [track.to_dict() for track in tracks])

# Simulated data generation for demonstration
def generate_simulated_track_data():
    """Generate simulated track data for demonstration"""
    track_types = ['Aircraft', 'Vessel', 'Vehicle']
    
    try:
        # Always clear existing tracks first, then create new ones
        Track.query.delete()
        
        for i in range(10):
            # Generate tracks within a reasonable geographical area (Eastern US seaboard region)
            # This ensures all tracks are visible on the default map view
            track_type = random.choice(track_types)
            
            track = Track(
                track_id=f"TRK{1000 + i}",
                callsign=f"CALL{i:03d}",
                track_type=track_type,
                latitude=39.5 + random.uniform(-3, 3),    # NYC/Philadelphia area ±3 degrees
                longitude=-75.0 + random.uniform(-4, 4),  # Eastern seaboard ±4 degrees  
                altitude=random.uniform(100, 40000) if track_type == 'Aircraft' else (random.uniform(0, 100) if track_type == 'Vessel' else random.uniform(0, 1000)),
                heading=random.uniform(0, 360),
                speed=random.uniform(150, 600) if track_type == 'Aircraft' else (random.uniform(5, 40) if track_type == 'Vessel' else random.uniform(10, 80)),
                status='Active'
            )
            db.session.add(track)
        
        db.session.commit()
        print(f"Generated {10} tracks successfully")
    except Exception as e:
        print(f"Error generating tracks: {e}")
        db.session.rollback()
        raise

def update_tracks_realtime():
    """Update tracks in real-time and emit to clients"""
    global tracking_active
    
    while tracking_active:
        try:
            with app.app_context():
                tracks = Track.query.filter_by(status='Active').all()
                updated_tracks = []
                
                for track in tracks:
                    # Realistic movement based on speed and heading
                    speed_knots = track.speed or 100  # Default speed if None
                    heading_rad = math.radians(track.heading or 0)
                    
                    # Convert speed from knots to degrees per second
                    # 1 knot ≈ 0.000514444 degrees/second at equator
                    # Update every 2 seconds, so multiply by 2
                    speed_deg_per_update = (speed_knots * 0.000514444) * 2
                    
                    # Calculate movement based on heading
                    lat_change = speed_deg_per_update * math.cos(heading_rad)
                    lon_change = speed_deg_per_update * math.sin(heading_rad)
                    
                    # Apply movement with some randomness for realism
                    track.latitude += lat_change + random.uniform(-0.0002, 0.0002)
                    track.longitude += lon_change + random.uniform(-0.0002, 0.0002)
                    
                    # Gradual heading changes (like real vehicles)
                    heading_change = random.uniform(-3, 3)
                    track.heading = (track.heading + heading_change) % 360
                    
                    # More realistic speed changes
                    if track.track_type == 'Aircraft':
                        speed_change = random.uniform(-20, 20)
                        track.speed = max(150, min(600, track.speed + speed_change))
                    elif track.track_type == 'Vessel':
                        speed_change = random.uniform(-5, 5)
                        track.speed = max(5, min(40, track.speed + speed_change))
                    else:  # Vehicle
                        speed_change = random.uniform(-10, 10)
                        track.speed = max(10, min(80, track.speed + speed_change))
                    
                    track.last_updated = datetime.utcnow()
                    updated_tracks.append(track.to_dict())
                    
                    # Create real-time event for Event Monitor (always for each track update)
                    monitor_event = {
                        'track_id': track.track_id,
                        'event_type': 'Track Update',
                        'description': f'Track {track.track_id} updated - Position: {track.latitude:.4f}, {track.longitude:.4f}, Speed: {track.speed:.1f}',
                        'timestamp': datetime.utcnow().isoformat(),
                        'is_realtime': True
                    }
                    
                    # Occasionally create historical events for Event Log
                    if random.random() < 0.03:  # 3% chance for log events
                        log_event_types = ['Course Change', 'Speed Alert', 'Altitude Change', 'Communication']
                        event = Event(
                            track_id=track.track_id,
                            event_type=random.choice(log_event_types),
                            description=f'Track {track.track_id}: {random.choice(log_event_types).lower()} - {random.choice(["routine update", "deviation detected", "normal operation", "status change"])}'
                        )
                        db.session.add(event)
                
                db.session.commit()
                
                # Emit track updates to all connected clients
                socketio.emit('track_update', updated_tracks)
                
                # Create real-time monitor events for each active track
                monitor_events = []
                for track_dict in updated_tracks:
                    monitor_event = {
                        'track_id': track_dict['track_id'],
                        'event_type': 'Track Update',
                        'description': f"Track {track_dict['track_id']} - {track_dict.get('track_type', 'Unknown')} at {track_dict['latitude']:.4f}, {track_dict['longitude']:.4f}",
                        'timestamp': datetime.utcnow().isoformat(),
                        'is_realtime': True
                    }
                    monitor_events.append(monitor_event)
                
                # Emit real-time events to Event Monitor
                socketio.emit('monitor_events', monitor_events)
                print(f"Emitted {len(monitor_events)} monitor events")
            
        except Exception as e:
            print(f"Error updating tracks: {e}")
        
        time.sleep(2)  # Update every 2 seconds for better performance

# Background thread management
tracking_thread = None
tracking_active = False

def start_surveillance():
    """Start surveillance tracking and real-time updates"""
    global tracking_thread, tracking_active
    
    if not tracking_active:
        try:
            # Generate initial tracks only when surveillance starts
            generate_simulated_track_data()
            
            # Start real-time updates
            tracking_active = True
            tracking_thread = threading.Thread(target=update_tracks_realtime)
            tracking_thread.daemon = True
            tracking_thread.start()
            
            return True
        except Exception as e:
            print(f"Error starting surveillance: {e}")
            tracking_active = False
            return False
    return False

def stop_surveillance():
    """Stop surveillance tracking"""
    global tracking_active, tracking_thread
    
    # Stop tracking first
    tracking_active = False
    
    # Wait a moment for the thread to finish
    if tracking_thread and tracking_thread.is_alive():
        time.sleep(0.1)
    
    # Clear all tracks when stopping
    try:
        Track.query.delete()
        db.session.commit()
        
        # Emit empty track update immediately
        socketio.emit('track_update', [])
        
        return True
    except Exception as e:
        print(f"Error stopping surveillance: {e}")
        db.session.rollback()
        return False

# CoT WebSocket endpoints
@socketio.on('request_cot_batch')
def handle_cot_batch_request():
    """Handle request for batch CoT data"""
    try:
        tracks = Track.query.filter_by(status='Active').all()
        track_data = [track.to_dict() for track in tracks]
        
        # Generate batch CoT XML
        batch_cot = cot_processor.batch_tracks_to_cot(track_data)
        emit('cot_batch', {'batch_cot_xml': batch_cot, 'track_count': len(track_data)})
    except Exception as e:
        emit('cot_error', {'error': str(e)})

@socketio.on('request_cot_heartbeat')
def handle_cot_heartbeat():
    """Handle CoT heartbeat request"""
    try:
        heartbeat = cot_processor.create_heartbeat_message()
        emit('cot_heartbeat', {'heartbeat_xml': heartbeat})
    except Exception as e:
        emit('cot_error', {'error': str(e)})

# API endpoint for CoT data
@app.route('/api/cot/tracks')
def get_cot_tracks():
    """Get all tracks in CoT XML format"""
    try:
        tracks = Track.query.filter_by(status='Active').all()
        track_data = [track.to_dict() for track in tracks]
        
        cot_tracks = []
        for track in track_data:
            cot_xml = cot_processor.track_to_cot_xml(track)
            cot_tracks.append({
                'track_id': track['track_id'],
                'cot_xml': cot_xml
            })
        
        return jsonify({
            'status': 'success',
            'track_count': len(cot_tracks),
            'cot_tracks': cot_tracks
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/cot/batch')
def get_cot_batch():
    """Get batch CoT XML for all active tracks"""
    try:
        tracks = Track.query.filter_by(status='Active').all()
        track_data = [track.to_dict() for track in tracks]
        
        batch_xml = cot_processor.batch_tracks_to_cot(track_data)
        
        return jsonify({
            'status': 'success',
            'track_count': len(track_data),
            'batch_cot_xml': batch_xml
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# API endpoints for surveillance control
@app.route('/api/surveillance/start', methods=['POST'])
def start_surveillance_api():
    """Start surveillance tracking"""
    global tracking_active, tracking_thread
    
    if not tracking_active:
        try:
            # Generate tracks immediately and synchronously for faster response
            generate_simulated_track_data()
            
            # Start background tracking
            tracking_active = True
            if tracking_thread is None or not tracking_thread.is_alive():
                tracking_thread = threading.Thread(target=update_tracks_realtime)
                tracking_thread.daemon = True
                tracking_thread.start()
            
            return jsonify({
                'status': 'success',
                'message': 'Surveillance started'
            })
        except Exception as e:
            print(f"Error starting surveillance: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to start surveillance'
            }), 500
    else:
        return jsonify({
            'status': 'info',
            'message': 'Surveillance already running'
        })

@app.route('/api/surveillance/stop', methods=['POST'])
def stop_surveillance_api():
    """Stop surveillance tracking"""
    if stop_surveillance():
        return jsonify({
            'status': 'success',
            'message': 'Surveillance stopped and tracks cleared'
        })
    return jsonify({
        'status': 'error',
        'message': 'Error stopping surveillance'
    })
