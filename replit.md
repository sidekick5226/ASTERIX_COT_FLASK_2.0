# Surveillance COP Dashboard

## Overview

This is a surveillance Common Operating Picture (COP) dashboard built with Flask and Socket.IO for real-time monitoring of aircraft, vessels, and vehicle tracks. The application processes ASTERIX surveillance data and provides data conversion capabilities for military and emergency response formats including CoT (Cursor-on-Target) XML and KLV (Key-Length-Value) metadata.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with Socket.IO for real-time communication
- **Database**: SQLAlchemy ORM with SQLite as default (configurable via DATABASE_URL environment variable)
- **Real-time Communication**: WebSocket connections using Flask-SocketIO for live track updates
- **Data Processing**: Modular processors for ASTERIX surveillance data, CoT XML conversion, and KLV metadata handling

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 for responsive UI
- **Mapping**: Dual mapping system supporting both 2D (Leaflet) and 3D (Cesium) visualization
- **Real-time Updates**: JavaScript WebSocket client for live data streaming
- **UI Framework**: Bootstrap 5 with custom CSS for military/surveillance styling

### Data Processing Pipeline
- **ASTERIX Processor**: Handles multiple ASTERIX categories (1, 2, 8, 10, 19, 20, 21, etc.) for radar and multilateration data
- **CoT Converter**: Transforms track data to military CoT XML format with proper affiliation and type codes
- **KLV Converter**: Supports MISB ST 0601 and ST 0902 standards for metadata encoding/decoding

## Key Components

### Models (models.py)
- **Track**: Core entity storing track ID, position (lat/lon), altitude, heading, speed, and metadata
- **Event**: Event logging system for track activities and system alerts
- **NetworkConfig**: Configuration management for network protocols and endpoints

### Data Processors
- **AsterixProcessor**: Simulates processing of EUROCONTROL surveillance data exchange format
- **CoTConverter**: Military standard XML format converter for situational awareness
- **KLVConverter**: MISB standard metadata processor for UAS and VMTi data

### Web Interface
- **Dashboard**: Real-time map display with track visualization and filtering
- **Event Monitor**: Live event stream with filtering capabilities
- **Event Log**: Historical event data with pagination and export functionality

## Data Flow

1. **Track Ingestion**: ASTERIX data is processed and converted to internal track format
2. **Database Storage**: Tracks and events are persisted using SQLAlchemy models
3. **Real-time Broadcasting**: Socket.IO broadcasts track updates to connected clients
4. **Map Visualization**: Frontend receives updates and renders tracks on Leaflet/Cesium maps
5. **Data Export**: Tracks can be converted to CoT XML or KLV metadata for external systems

## External Dependencies

### Python Packages
- Flask ecosystem (Flask, Flask-SocketIO, Flask-SQLAlchemy)
- SQLAlchemy with declarative base
- Werkzeug ProxyFix for deployment behind reverse proxies

### Frontend Libraries
- Bootstrap 5 for responsive UI components
- Font Awesome for icons
- Leaflet for 2D mapping
- Cesium for 3D globe visualization
- Socket.IO client for real-time communication

### Standards Support
- ASTERIX (All Purpose Structured Eurocontrol Surveillance Information Exchange)
- CoT (Cursor-on-Target) XML for military systems
- MISB KLV standards (ST 0601, ST 0902) for metadata

## Deployment Strategy

### Environment Configuration
- **Database**: Configurable via DATABASE_URL environment variable (defaults to SQLite)
- **Security**: Session secret configurable via SESSION_SECRET environment variable
- **Connection Pooling**: SQLAlchemy configured with connection recycling and health checks

### Production Considerations
- ProxyFix middleware configured for deployment behind reverse proxies
- CORS enabled for Socket.IO connections
- Database connection pooling with 300-second recycle time
- Automatic table creation on application startup

### Scalability Features
- Stateless design allows horizontal scaling
- Socket.IO supports multiple workers with proper configuration
- Database abstraction allows easy migration from SQLite to PostgreSQL/MySQL
- Modular data processors can be deployed as separate services

The application is designed as a real-time surveillance monitoring system with military/emergency response integration capabilities, supporting multiple data formats and providing both 2D and 3D visualization options.