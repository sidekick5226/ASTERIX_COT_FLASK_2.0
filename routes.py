from flask import render_template, request, jsonify
from flask_socketio import emit
from app import app, socketio, db
from models import Track, Event, NetworkConfig
from datetime import datetime
import json
import math
import random
import threading
import time
from asterix_processor import AsterixProcessor
from cot_converter import CoTConverter
from klv_converter import KLVConverter
from cot_processor import CoTProcessor

# Initialize processors
asterix_processor = AsterixProcessor()
cot_converter = CoTConverter()
klv_converter = KLVConverter()
cot_processor = CoTProcessor()

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
    """Get all events"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    events = Event.query.order_by(Event.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'events': [event.to_dict() for event in events.items],
        'total': events.total,
        'pages': events.pages,
        'current_page': page
    })

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

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected: {request.sid}')
    emit('status', {'msg': 'Connected to surveillance system'})
    # Send initial track data immediately
    tracks = Track.query.filter_by(status='Active').all()
    emit('track_update', [track.to_dict() for track in tracks])

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')

@socketio.on('request_track_update')
def handle_track_update_request():
    """Handle request for track updates"""
    tracks = Track.query.filter_by(status='Active').all()
    emit('track_update', [track.to_dict() for track in tracks])

# Simulated data generation for demonstration
def generate_simulated_track_data():
    """Generate simulated track data for demonstration"""
    track_types = ['Aircraft', 'Vessel', 'Vehicle']
    
    # Create some initial tracks if none exist
    if Track.query.count() == 0:
        for i in range(10):
            track = Track(
                track_id=f"TRK{1000 + i}",
                callsign=f"CALL{i:03d}",
                track_type=random.choice(track_types),
                latitude=40.0 + random.uniform(-2, 2),
                longitude=-74.0 + random.uniform(-2, 2),
                altitude=random.uniform(100, 40000) if random.choice(track_types) == 'Aircraft' else None,
                heading=random.uniform(0, 360),
                speed=random.uniform(50, 500),
                status='Active'
            )
            db.session.add(track)
        
        db.session.commit()

def update_tracks_realtime():
    """Update tracks in real-time and emit to clients"""
    while True:
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
                    
                    # Occasionally create events
                    if random.random() < 0.05:  # 5% chance
                        event_types = ['Position Update', 'Speed Change', 'Course Change']
                        event = Event(
                            track_id=track.track_id,
                            event_type=random.choice(event_types),
                            description=f'Track {track.track_id}: {random.choice(event_types).lower()}'
                        )
                        db.session.add(event)
                
                db.session.commit()
                
                # Emit updates to all connected clients
                socketio.emit('track_update', updated_tracks)
            
        except Exception as e:
            print(f"Error updating tracks: {e}")
        
        time.sleep(2)  # Update every 2 seconds

# Start background thread for real-time updates
def startup():
    """Initialize application startup tasks"""
    generate_simulated_track_data()
    thread = threading.Thread(target=update_tracks_realtime)
    thread.daemon = True
    thread.start()

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

# Initialize startup tasks when the module is imported
if not hasattr(app, '_startup_initialized'):
    app._startup_initialized = True
    with app.app_context():
        startup()
