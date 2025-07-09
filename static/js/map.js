// Map management functionality
class MapManager {
    constructor() {
        this.leafletMap = null;
        this.cesiumViewer = null;
        this.trackMarkers = new Map();
        this.is3DMode = false;
        this.tracks = [];
        
        this.init();
    }
    
    init() {
        this.initLeafletMap();
        this.initCesiumMap();
    }
    
    initLeafletMap() {
        // Initialize Leaflet map (2D)
        this.leafletMap = L.map('leaflet-map', {
            center: [40.0, -74.0], // New York area
            zoom: 8,
            zoomControl: true,
            attributionControl: true
        });
        
        // Add dark theme tile layer
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(this.leafletMap);
        
        // Add scale control
        L.control.scale({
            position: 'bottomleft',
            imperial: true,
            metric: true
        }).addTo(this.leafletMap);
        
        // Custom control for map info
        this.addMapInfoControl();
    }
    
    initCesiumMap() {
        // Initialize Cesium map (3D)
        try {
            this.cesiumViewer = new Cesium.Viewer('cesium-map', {
                terrainProvider: Cesium.createWorldTerrain(),
                imageryProvider: new Cesium.IonImageryProvider({ assetId: 3812 }),
                baseLayerPicker: false,
                geocoder: false,
                homeButton: false,
                sceneModePicker: false,
                navigationHelpButton: false,
                animation: false,
                timeline: false,
                fullscreenButton: false,
                vrButton: false,
                infoBox: false,
                selectionIndicator: false
            });
            
            // Set initial camera position
            this.cesiumViewer.camera.setView({
                destination: Cesium.Cartesian3.fromDegrees(-74.0, 40.0, 100000),
                orientation: {
                    heading: 0.0,
                    pitch: -Cesium.Math.PI_OVER_FOUR,
                    roll: 0.0
                }
            });
            
            // Disable default click behavior
            this.cesiumViewer.cesiumWidget.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK);
            
        } catch (error) {
            console.error('Error initializing Cesium:', error);
        }
    }
    
    addMapInfoControl() {
        const mapInfo = L.control({ position: 'topleft' });
        
        mapInfo.onAdd = function(map) {
            const div = L.DomUtil.create('div', 'map-info-control');
            div.style.cssText = `
                background: rgba(30, 41, 59, 0.95);
                border: 1px solid #3b4168;
                border-radius: 6px;
                padding: 10px;
                color: #ffffff;
                font-size: 0.85rem;
                min-width: 200px;
                backdrop-filter: blur(10px);
            `;
            div.innerHTML = `
                <div><strong>Map Mode:</strong> <span id="map-mode-display">2D Standard</span></div>
                <div><strong>Coordinates:</strong> <span id="mouse-coords">---, ---</span></div>
                <div><strong>Zoom:</strong> <span id="zoom-level">${map.getZoom()}</span></div>
            `;
            return div;
        };
        
        mapInfo.addTo(this.leafletMap);
        
        // Update coordinates on mouse move
        this.leafletMap.on('mousemove', (e) => {
            const coords = document.getElementById('mouse-coords');
            if (coords) {
                coords.textContent = `${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)}`;
            }
        });
        
        // Update zoom level
        this.leafletMap.on('zoomend', () => {
            const zoomDisplay = document.getElementById('zoom-level');
            if (zoomDisplay) {
                zoomDisplay.textContent = this.leafletMap.getZoom();
            }
        });
    }
    
    updateTracks(tracks) {
        this.tracks = tracks;
        
        if (this.is3DMode && this.cesiumViewer) {
            this.updateCesiumTracks(tracks);
        } else if (this.leafletMap) {
            this.updateLeafletTracks(tracks);
        }
    }
    
    updateLeafletTracks(tracks) {
        // Clear existing markers
        this.trackMarkers.forEach(marker => {
            this.leafletMap.removeLayer(marker);
        });
        this.trackMarkers.clear();
        
        // Add new markers
        tracks.forEach(track => {
            const marker = this.createLeafletMarker(track);
            marker.addTo(this.leafletMap);
            this.trackMarkers.set(track.track_id, marker);
        });
    }
    
    createLeafletMarker(track) {
        const icon = this.getTrackIcon(track.type);
        const color = this.getTrackColor(track.type);
        
        // Create custom HTML marker
        const customIcon = L.divIcon({
            html: `<div style="color: ${color}; font-size: 16px; text-align: center;">
                     <i class="${icon}"></i>
                     <div style="font-size: 10px; font-weight: bold; margin-top: 2px;">${track.track_id}</div>
                   </div>`,
            iconSize: [40, 40],
            iconAnchor: [20, 20],
            className: 'custom-track-marker'
        });
        
        const marker = L.marker([track.latitude, track.longitude], { 
            icon: customIcon,
            title: `${track.track_id} - ${track.type}`
        });
        
        // Add popup with track details
        const popupContent = `
            <div style="color: #000;">
                <h6>${track.track_id}</h6>
                <p><strong>Type:</strong> ${track.type}</p>
                <p><strong>Status:</strong> ${track.status}</p>
                <p><strong>Position:</strong> ${track.latitude.toFixed(4)}, ${track.longitude.toFixed(4)}</p>
                ${track.altitude ? `<p><strong>Altitude:</strong> ${track.altitude} ft</p>` : ''}
                ${track.speed ? `<p><strong>Speed:</strong> ${track.speed} kts</p>` : ''}
                ${track.heading ? `<p><strong>Heading:</strong> ${track.heading}°</p>` : ''}
                <p><strong>Last Update:</strong> ${new Date(track.last_updated).toLocaleString()}</p>
            </div>
        `;
        
        marker.bindPopup(popupContent);
        
        return marker;
    }
    
    updateCesiumTracks(tracks) {
        if (!this.cesiumViewer) return;
        
        // Clear existing entities
        this.cesiumViewer.entities.removeAll();
        
        // Add new entities
        tracks.forEach(track => {
            this.createCesiumEntity(track);
        });
    }
    
    createCesiumEntity(track) {
        const color = this.getCesiumColor(track.type);
        const position = Cesium.Cartesian3.fromDegrees(
            track.longitude, 
            track.latitude, 
            track.altitude || 0
        );
        
        this.cesiumViewer.entities.add({
            position: position,
            point: {
                pixelSize: 10,
                color: color,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2,
                heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
            },
            label: {
                text: track.track_id,
                font: '12pt sans-serif',
                fillColor: Cesium.Color.WHITE,
                outlineColor: Cesium.Color.BLACK,
                outlineWidth: 2,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                pixelOffset: new Cesium.Cartesian2(0, -40),
                distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0.0, 500000.0)
            },
            description: `
                <div>
                    <h4>${track.track_id}</h4>
                    <p><strong>Type:</strong> ${track.type}</p>
                    <p><strong>Status:</strong> ${track.status}</p>
                    <p><strong>Position:</strong> ${track.latitude.toFixed(4)}, ${track.longitude.toFixed(4)}</p>
                    ${track.altitude ? `<p><strong>Altitude:</strong> ${track.altitude} ft</p>` : ''}
                    ${track.speed ? `<p><strong>Speed:</strong> ${track.speed} kts</p>` : ''}
                    ${track.heading ? `<p><strong>Heading:</strong> ${track.heading}°</p>` : ''}
                    <p><strong>Last Update:</strong> ${new Date(track.last_updated).toLocaleString()}</p>
                </div>
            `
        });
    }
    
    getTrackIcon(type) {
        switch (type.toLowerCase()) {
            case 'aircraft': return 'fas fa-plane';
            case 'vessel': return 'fas fa-ship';
            case 'vehicle': return 'fas fa-car';
            default: return 'fas fa-question-circle';
        }
    }
    
    getTrackColor(type) {
        switch (type.toLowerCase()) {
            case 'aircraft': return '#3b82f6';
            case 'vessel': return '#10b981';
            case 'vehicle': return '#f59e0b';
            default: return '#6b7280';
        }
    }
    
    getCesiumColor(type) {
        switch (type.toLowerCase()) {
            case 'aircraft': return Cesium.Color.BLUE;
            case 'vessel': return Cesium.Color.GREEN;
            case 'vehicle': return Cesium.Color.ORANGE;
            default: return Cesium.Color.GRAY;
        }
    }
    
    switchTo3D() {
        this.is3DMode = true;
        document.getElementById('leaflet-map').style.display = 'none';
        document.getElementById('cesium-map').style.display = 'block';
        
        // Update map mode display
        const modeDisplay = document.getElementById('map-mode-display');
        if (modeDisplay) {
            modeDisplay.textContent = '3D Battle Mode';
        }
        
        // Resize Cesium viewer
        if (this.cesiumViewer) {
            setTimeout(() => {
                this.cesiumViewer.resize();
                this.updateCesiumTracks(this.tracks);
            }, 100);
        }
    }
    
    switchTo2D() {
        this.is3DMode = false;
        document.getElementById('cesium-map').style.display = 'none';
        document.getElementById('leaflet-map').style.display = 'block';
        
        // Update map mode display
        const modeDisplay = document.getElementById('map-mode-display');
        if (modeDisplay) {
            modeDisplay.textContent = '2D Standard';
        }
        
        // Refresh Leaflet map
        if (this.leafletMap) {
            setTimeout(() => {
                this.leafletMap.invalidateSize();
                this.updateLeafletTracks(this.tracks);
            }, 100);
        }
    }
    
    filterByType(type) {
        const filteredTracks = type ? this.tracks.filter(track => track.type === type) : this.tracks;
        this.updateTracks(filteredTracks);
    }
    
    focusOnTrack(trackId) {
        const track = this.tracks.find(t => t.track_id === trackId);
        if (!track) return;
        
        if (this.is3DMode && this.cesiumViewer) {
            // Focus on track in 3D
            this.cesiumViewer.camera.flyTo({
                destination: Cesium.Cartesian3.fromDegrees(
                    track.longitude, 
                    track.latitude, 
                    10000
                ),
                duration: 2.0
            });
        } else if (this.leafletMap) {
            // Focus on track in 2D
            this.leafletMap.setView([track.latitude, track.longitude], 12);
            
            // Open popup if marker exists
            const marker = this.trackMarkers.get(trackId);
            if (marker) {
                marker.openPopup();
            }
        }
    }
    
    invalidateSize() {
        if (this.leafletMap && !this.is3DMode) {
            this.leafletMap.invalidateSize();
        }
        if (this.cesiumViewer && this.is3DMode) {
            this.cesiumViewer.resize();
        }
    }
}

// Initialize map manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mapManager = new MapManager();
});
