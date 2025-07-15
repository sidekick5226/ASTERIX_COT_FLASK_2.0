# Surveillance Sentry - ASTERIX Processing System

## Quick Start

### 🚀 Simple Start (Recommended)
```bash
python main.py
```
This starts the complete system with:
- Flask web application on http://localhost:5000
- UDP receiver listening on 0.0.0.0:8080
- Real-time WebSocket connections
- Default credentials: `user` / `pass`

### 🎯 With PCAP Replay (Full Demo)
```bash
python start_surveillance.py --pcap cat48-only-plot-capture.pcap
```
This provides a complete demo by:
- Starting the web application
- Automatically replaying PCAP data after 5 seconds
- Showing real-time ASTERIX CAT-48 processing
- Displaying live tracks on the dashboard

### ⚙️ Advanced Options

#### Enhanced Startup with Custom PCAP Settings
```bash
# Replay at 2x speed with 10-second delay
python start_surveillance.py --pcap cat48-only-plot-capture.pcap --pcap-speed 2.0 --pcap-delay 10

# Replay to custom port
python start_surveillance.py --pcap cat48-only-plot-capture.pcap --pcap-port 8081

# All options
python start_surveillance.py --pcap cat48-only-plot-capture.pcap --pcap-host 127.0.0.1 --pcap-port 8080 --pcap-speed 1.5 --pcap-delay 5
```

#### Manual PCAP Operations
```bash
# Analyze PCAP file contents
python pcap_parser.py analyze cat48-only-plot-capture.pcap

# Manual replay to UDP receiver
python pcap_parser.py replay cat48-only-plot-capture.pcap

# Custom replay settings
python pcap_parser.py replay cat48-only-plot-capture.pcap 127.0.0.1 8080 2.0
```

#### Component Testing
```bash
# Test UDP receiver only
python udp_receiver.py

# Test simple UDP receiver (no Flask dependencies)
python simple_udp_receiver.py

# Test system integration
python test_main_integration.py
```

### 🔧 System Architecture Options

| Start Method | Use Case | Features |
|--------------|----------|----------|
| `python main.py` | Production/Development | Full system with manual data input |
| `python start_surveillance.py --pcap <file>` | Demo/Testing | Automated PCAP replay with web interface |
| `python udp_receiver.py` | Component Testing | UDP receiver only (standalone) |
| `python pcap_parser.py` | Data Analysis | PCAP file analysis and manual replay |

### 🌐 Access Points
- **Web Dashboard**: http://localhost:5000
- **UDP Receiver**: 0.0.0.0:8080
- **Default Login**: `user` / `pass`
- **Database**: SQLite (surveillance.db)

### 📊 Available Commands

#### Start Surveillance Help
```bash
python start_surveillance.py --help
```

#### PCAP Parser Help
```bash
python pcap_parser.py
# Shows: analyze, replay commands with examples
```

## Overview

This is a surveillance Common Operating Picture (COP) dashboard built with Flask and Socket.IO for real-time monitoring of aircraft, vessels, and vehicle tracks. The application processes ASTERIX surveillance data and provides data conversion capabilities for military and emergency response formats including CoT (Cursor-on-Target) XML and KLV (Key-Length-Value) metadata.

## 🔧 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Kill existing Python processes
taskkill /f /im python.exe

# Or use different port
python start_surveillance.py --pcap cat48-only-plot-capture.pcap --pcap-port 8081
```

#### Import Errors
```bash
# Test system integration
python test_main_integration.py

# If Flask dependencies missing, install them
pip install flask flask-socketio flask-sqlalchemy
```

#### No Data Appearing
1. Check UDP receiver is running (should show in startup logs)
2. Verify PCAP replay is sending data (check terminal output)
3. Ensure ports match (default: 8080)
4. Check web browser console for WebSocket errors

#### Database Issues
```bash
# Delete database and restart (will recreate)
del surveillance.db
python main.py
```

### File Structure
```
├── main.py                    # 🚀 Main application entry point
├── start_surveillance.py      # 🎯 Enhanced startup with PCAP replay
├── app.py                     # Flask application setup
├── udp_receiver.py           # UDP ASTERIX receiver
├── pcap_parser.py            # PCAP file parser and replay
├── models.py                 # Database models
├── routes.py                 # Web routes and API endpoints
├── templates/                # Web interface templates
├── static/                   # CSS, JS, and other static files
├── cat48-only-plot-capture.pcap # Sample PCAP file
├── QUICKSTART.md             # Detailed quick start guide
└── README.md                 # This file
```

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with Socket.IO for real-time communication
- **Database**: SQLAlchemy ORM with PostgreSQL database (configured via DATABASE_URL environment variable)
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
- **AsterixConverter**: Multi-category ASTERIX processor with specialized handlers for:
  - CAT-10: Surface Movement Data
  - CAT-21: ADS-B Target Reports  
  - CAT-48: Monoradar Target Reports
- **CoTConverter**: Military standard XML format converter for situational awareness
- **KLVConverter**: MISB standard metadata processor for UAS and VMTi data
- **ADSBCoTConverter**: Specialized ADSB to CoT converter for aviation surveillance

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
- **Database**: PostgreSQL database configured via DATABASE_URL environment variable
- **Security**: Session secret configurable via SESSION_SECRET environment variable
- **Connection Pooling**: SQLAlchemy configured with connection recycling and health checks
- **Database Credentials**: PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE environment variables

### Production Considerations
- ProxyFix middleware configured for deployment behind reverse proxies
- CORS enabled for Socket.IO connections
- Database connection pooling with 300-second recycle time
- Automatic table creation on application startup

### Scalability Features
- Stateless design allows horizontal scaling
- Socket.IO supports multiple workers with proper configuration
- PostgreSQL database supports concurrent connections and high-performance operations
- Modular data processors can be deployed as separate services

## Recent Updates (July 2025)
- **Single Command Startup**: Complete system now runs with simple `python main.py` command
- **PCAP Integration**: Automated PCAP replay with `start_surveillance.py --pcap <file>` for instant demos
- **Circular Import Fix**: Resolved Flask app initialization issues for reliable startup
- **Enhanced UDP Receiver**: Improved error handling and standalone testing capabilities
- **Database Migration**: Upgraded from SQLite to PostgreSQL for better performance and concurrent access
- **Live Updates**: Implemented continuous track updates every second for real-time surveillance
- **Battle View 3D**: Fixed altitude positioning with realistic defaults (Aircraft: 10,000ft, Vessels: sea level, Vehicles: 100ft)
- **Selective Clearing**: "Stop & Clear" now preserves Event Log while clearing Active Tracks and Event Monitor
- **Responsive Interface**: Migrated from Bootstrap to Tailwind CSS with mobile-compatible sidebar and adaptive layouts
- **Advanced 3D CesiumJS**: Implemented comprehensive 3D mapping with quantized-mesh terrain, 3D buildings, and glTF unit models
- **CoT Integration**: Added CoT (Cursor-on-Target) XML processor for military standard data exchange and real-time WebSocket broadcasting
- **Camera Follow System**: Implemented chase cam, first-person, and orbital camera modes for tactical unit following
- **Event System Redesign**: Completely redesigned Event Monitor and Event Log to use reliable polling-based approach instead of WebSocket (July 10, 2025)
- **Real-time Event Display**: Event Monitor now shows live track updates with proper timestamps, track IDs, and descriptions using /api/monitor-events endpoint
- **Dual Polling Architecture**: Tracks update every 1 second, monitor events every 2 seconds for optimal performance and responsiveness
- **Camera System Simplified**: Removed camera mode toggle button - camera now follows tracks automatically on double-click and resets to optimal view when deselected (July 11, 2025)
- **Daily Event Log Export**: Automated daily CSV export of event logs to `export_log_hist` folder with automatic clearing after export at midnight (July 11, 2025)

### Advanced 3D Features
- **Terrain**: Quantized-mesh tiles with local server capability (currently using Cesium World Terrain as fallback)
- **Buildings**: 3D building models from OSM/LiDAR data (currently using Cesium OSM Buildings as fallback)
- **Units**: glTF model positioning via CoT lat/lon/heading coordinates with realistic altitude defaults
- **Follow Cameras**: Chase view, first-person drone, and orbital camera modes with smooth transitions
- **CoT Broadcasting**: Real-time WebSocket CoT XML updates for ASTERIX-to-CoT data conversion

The application now supports dual map modes (2D Leaflet standard and 3D CesiumJS advanced) with full responsive design adaptable to any screen size, making it suitable for both desktop surveillance operations and mobile tactical use.