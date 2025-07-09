from flask import render_template, request, jsonify
from flask_socketio import emit
from app import app, socketio, db
from models import Track, Event, NetworkConfig
from datetime import datetime
import json
import random
import threading
import time
from asterix_processor import AsterixProcessor
from cot_converter import CoTConverter
from klv_converter import KLVConverter

# Initialize processors
asterix_processor = AsterixProcessor()
cot_converter = CoTConverter()
klv_converter = KLVConverter()

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
                    # Simulate movement
                    track.latitude += random.uniform(-0.001, 0.001)
                    track.longitude += random.uniform(-0.001, 0.001)
                    track.heading = (track.heading + random.uniform(-5, 5)) % 360
                    track.speed = max(0, track.speed + random.uniform(-10, 10))
                    track.last_updated = datetime.utcnow()
                    
                    updated_tracks.append(track.to_dict())
                    
                    # Occasionally create events
                    if random.random() < 0.1:  # 10% chance
                        event = Event(
                            track_id=track.track_id,
                            event_type='Position Update',
                            description=f'Track {track.track_id} updated position'
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

# Initialize startup tasks when the module is imported
if not hasattr(app, '_startup_initialized'):
    app._startup_initialized = True
    with app.app_context():
        startup()
