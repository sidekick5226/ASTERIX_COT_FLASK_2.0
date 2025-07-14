from datetime import datetime
from sqlalchemy import func
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class Track(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    track_id = db.Column(db.String(50), unique=True, nullable=False)
    callsign = db.Column(db.String(20))
    track_type = db.Column(db.String(20), nullable=False)  # Aircraft, Vessel, Vehicle
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    altitude = db.Column(db.Float)
    heading = db.Column(db.Float)
    speed = db.Column(db.Float)
    status = db.Column(db.String(20), default='Active')
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'track_id': self.track_id,
            'callsign': self.callsign,
            'track_type': self.track_type,  # Keep consistent field name
            'type': self.track_type,        # Also include 'type' for compatibility
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'heading': self.heading,
            'speed': self.speed,
            'status': self.status,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    track_id = db.Column(db.String(50), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    user_notes = db.Column(db.Text)  # User-editable notes/details
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'track_id': self.track_id,
            'event_type': self.event_type,
            'description': self.description,
            'user_notes': self.user_notes,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class NetworkConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    protocol = db.Column(db.String(20), default='TCP')
    port = db.Column(db.Integer, default=8080)
    ip_address = db.Column(db.String(45), default='127.0.0.1')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
