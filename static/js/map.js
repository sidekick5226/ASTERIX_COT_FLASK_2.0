// Map management functionality
class MapManager {
    constructor() {
        this.leafletMap = null;
        this.cesiumViewer = null;
        this.trackMarkers = new Map();
        this.trackTrails = new Map(); // Store track trails for movement visualization
        this.is3DMode = false;
        this.tracks = [];
        this.showTrails = true; // ATAK-CIV style movement trails
        
        this.init();
    }
    
    init() {
        this.initLeafletMap();
        // Don't initialize basic Cesium - use AdvancedCesiumManager instead
        // this.initCesiumMap();
    }
    
    // Alias method for compatibility
    initMaps() {
        this.init();
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
        // Initialize Cesium map (3D) with reliable configuration
        try {
            this.cesiumViewer = new Cesium.Viewer('cesium-map', {
                baseLayerPicker: false,
                geocoder: false,
                homeButton: false,
                sceneModePicker: false,
                navigationHelpButton: false,
                animation: false,
                timeline: false,
                fullscreenButton: false,
                vrButton: false,
                infoBox: true,
                selectionIndicator: true,
                shouldAnimate: true,
                // Use Esri World Imagery for satellite view
                imageryProvider: new Cesium.ArcGisMapServerImageryProvider({
                    url: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer',
                    credit: 'Esri, DigitalGlobe, GeoEye, Earthstar Geographics, CNES/Airbus DS, USDA, USGS, AeroGRID, IGN, and the GIS User Community'
                })
            });
            
            // Set initial camera position over North America for surveillance
            this.cesiumViewer.camera.setView({
                destination: Cesium.Cartesian3.fromDegrees(-95.0, 39.0, 2000000), // Center of North America
                orientation: {
                    heading: 0.0,
                    pitch: -Cesium.Math.PI_OVER_SIX, // Less steep angle for better view
                    roll: 0.0
                }
            });
            
            // Enable lighting for realistic satellite view
            this.cesiumViewer.scene.globe.enableLighting = true;
            this.cesiumViewer.scene.globe.dynamicAtmosphereLighting = true;
            this.cesiumViewer.scene.globe.atmosphereHueShift = 0.0;
            this.cesiumViewer.scene.globe.atmosphereSaturationShift = 0.1;
            this.cesiumViewer.scene.globe.atmosphereBrightnessShift = 0.1;
            
            // Configure for satellite surveillance view
            this.cesiumViewer.scene.skyBox.show = true;
            this.cesiumViewer.scene.sun.show = true;
            this.cesiumViewer.scene.moon.show = true;
            this.cesiumViewer.scene.skyAtmosphere.show = true;
            this.cesiumViewer.scene.fog.enabled = false; // Disable fog for clearer satellite view
            
        } catch (error) {
            console.error('Error initializing Cesium:', error);
            console.log('Trying fallback Cesium configuration...');
            
            // Fallback: Use satellite imagery with basic configuration
            try {
                this.cesiumViewer = new Cesium.Viewer('cesium-map', {
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
                    selectionIndicator: false,
                    shouldAnimate: false,
                    // Use satellite imagery even in fallback
                    imageryProvider: new Cesium.ArcGisMapServerImageryProvider({
                        url: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer'
                    })
                });
                
                // Set basic camera view
                this.cesiumViewer.camera.setView({
                    destination: Cesium.Cartesian3.fromDegrees(-95.0, 39.0, 2000000)
                });
                
                console.log('Cesium initialized with fallback configuration');
                
                // Test if viewer is actually working
                setTimeout(() => {
                    if (this.cesiumViewer && this.cesiumViewer.scene) {
                        console.log('Cesium scene verified - 3D mode ready');
                    } else {
                        console.error('Cesium scene not available');
                    }
                }, 1000);
                
            } catch (fallbackError) {
                console.error('Cesium fallback also failed:', fallbackError);
                console.log('3D Battle View unavailable - WebGL support required');
                this.cesiumViewer = null;
            }
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
        console.log(`Updating ${tracks.length} tracks in ${this.is3DMode ? '3D Battle' : '2D Standard'} view`);
        this.tracks = tracks;
        
        // Update 2D map when in 2D mode or always keep it synchronized
        if (!this.is3DMode && this.leafletMap) {
            this.updateLeafletTracks(tracks);
        }
        
        // Update 3D map when in 3D mode using Advanced Cesium Manager
        if (this.is3DMode && window.advancedCesium && window.advancedCesium.viewer) {
            window.advancedCesium.updateTracks(tracks);
        }
        
        // Also update basic Cesium viewer if it exists (fallback)
        if (this.cesiumViewer && !this.is3DMode) {
            this.updateCesiumTracks(tracks);
        }
    }
    
    updateLeafletTracks(tracks) {
        tracks.forEach(track => {
            const trackId = track.track_id;
            const newPosition = [track.latitude, track.longitude];
            
            // Handle existing marker
            if (this.trackMarkers.has(trackId)) {
                const marker = this.trackMarkers.get(trackId);
                
                // Update marker position
                marker.setLatLng(newPosition);
                
                // Update popup content  
                const popupContent = this.createPopupContent(track);
                marker.setPopupContent(popupContent);
            } else {
                // Create new marker
                const marker = this.createLeafletMarker(track);
                marker.addTo(this.leafletMap);
                this.trackMarkers.set(trackId, marker);
            }
        });
        
        // Remove markers for tracks that no longer exist
        const activeTrackIds = new Set(tracks.map(t => t.track_id));
        this.trackMarkers.forEach((marker, trackId) => {
            if (!activeTrackIds.has(trackId)) {
                this.leafletMap.removeLayer(marker);
                this.trackMarkers.delete(trackId);
            }
        });
    }
    
    createLeafletMarker(track) {
        const icon = this.getTrackIcon(track.type);
        const color = this.getTrackColor(track.type);
        
        // Calculate arrow properties based on heading and speed
        const heading = track.heading || 0;
        const speed = track.speed || 0;
        
        // Arrow length based on speed (normalize speed to arrow length 10-40px)
        const minArrowLength = 15;
        const maxArrowLength = 45;
        const speedRange = { min: 5, max: 600 }; // Min/max expected speeds
        const normalizedSpeed = Math.max(0, Math.min(1, (speed - speedRange.min) / (speedRange.max - speedRange.min)));
        const arrowLength = minArrowLength + (normalizedSpeed * (maxArrowLength - minArrowLength));
        
        // Calculate icon border position based on heading
        const iconRadius = 18; // Distance from center to icon border
        const headingRadians = heading * Math.PI / 180;
        
        // Start point at icon border (where arrow attaches to icon)
        const startX = 30 + iconRadius * Math.sin(headingRadians);
        const startY = 30 - iconRadius * Math.cos(headingRadians);
        
        // End point for arrow (extending from icon border)
        const endX = startX + arrowLength * Math.sin(headingRadians);
        const endY = startY - arrowLength * Math.cos(headingRadians);
        
        // Create arrow SVG
        const arrowSvg = `
            <svg width="60" height="60" style="position: absolute; top: -30px; left: -30px; pointer-events: none;">
                <defs>
                    <marker id="arrowhead-${track.track_id}" markerWidth="6" markerHeight="4" 
                            refX="6" refY="2" orient="auto" fill="${color}">
                        <polygon points="0 0, 6 2, 0 4" />
                    </marker>
                </defs>
                <line x1="${startX}" y1="${startY}" 
                      x2="${endX}" y2="${endY}" 
                      stroke="${color}" 
                      stroke-width="2" 
                      marker-end="url(#arrowhead-${track.track_id})" />
            </svg>
        `;
        
        // Create custom HTML marker with icon and directional arrow
        const customIcon = L.divIcon({
            html: `<div style="position: relative;">
                     ${arrowSvg}
                     <div style="color: ${color}; font-size: 16px; text-align: center; position: relative; z-index: 10;">
                         <i class="${icon}"></i>
                         <div style="font-size: 10px; font-weight: bold; margin-top: 2px;">${track.track_id}</div>
                     </div>
                   </div>`,
            iconSize: [60, 60],
            iconAnchor: [30, 30],
            className: 'custom-track-marker'
        });
        
        const marker = L.marker([track.latitude, track.longitude], { 
            icon: customIcon,
            title: `${track.track_id} - ${track.type} - ${Math.round(heading)}° @ ${Math.round(speed)} kts`
        });
        
        // Add popup with track details
        const popupContent = this.createPopupContent(track);
        marker.bindPopup(popupContent);
        return marker;
    }
    
    createPopupContent(track) {
        return `
            <div style="color: #000; min-width: 200px;">
                <h6 style="color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px;">
                    ${track.callsign || track.track_id}
                </h6>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem;">
                    <div>
                        <strong>Type:</strong><br>${track.track_type || track.type}
                    </div>
                    <div>
                        <strong>Status:</strong><br><span style="color: ${track.status === 'Active' ? '#10b981' : '#ef4444'}">${track.status}</span>
                    </div>
                    <div>
                        <strong>Position:</strong><br>${track.latitude.toFixed(4)}, ${track.longitude.toFixed(4)}
                    </div>
                    ${track.altitude ? `<div><strong>Altitude:</strong><br>${Math.round(track.altitude)} ft</div>` : ''}
                    ${track.speed ? `<div><strong>Speed:</strong><br>${Math.round(track.speed)} kts</div>` : ''}
                    ${track.heading ? `<div><strong>Heading:</strong><br>${Math.round(track.heading)}°</div>` : ''}
                </div>
                <div style="margin-top: 10px; padding-top: 5px; border-top: 1px solid #e2e8f0; font-size: 0.75rem; color: #64748b;">
                    Last Update: ${new Date(track.last_updated).toLocaleString()}
                </div>
            </div>
        `;
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
        // Use reasonable altitude defaults for 3D view
        let altitude = 0;
        if (track.altitude && track.altitude > 0 && track.altitude < 100000) {
            altitude = track.altitude;
        } else {
            // Set default altitudes based on track type for better 3D visualization
            if ((track.track_type || track.type) === 'Aircraft') {
                altitude = 10000; // 10,000 feet for aircraft
            } else if ((track.track_type || track.type) === 'Vessel') {
                altitude = 0; // Sea level for vessels
            } else if ((track.track_type || track.type) === 'Vehicle') {
                altitude = 100; // 100 feet for ground vehicles
            }
        }
        
        const position = Cesium.Cartesian3.fromDegrees(
            track.longitude, 
            track.latitude, 
            altitude
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
                    <p><strong>Type:</strong> ${track.track_type || track.type}</p>
                    <p><strong>Status:</strong> ${track.status}</p>
                    <p><strong>Position:</strong> ${track.latitude.toFixed(4)}, ${track.longitude.toFixed(4)}</p>
                    <p><strong>Altitude:</strong> ${altitude} ft</p>
                    ${track.speed ? `<p><strong>Speed:</strong> ${Math.round(track.speed)} kts</p>` : ''}
                    ${track.heading ? `<p><strong>Heading:</strong> ${Math.round(track.heading)}°</p>` : ''}
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
        const trackType = (type || '').toLowerCase();
        switch (trackType) {
            case 'aircraft': return '#3b82f6';
            case 'vessel': return '#10b981';
            case 'vehicle': return '#f59e0b';
            default: return '#6b7280';
        }
    }
    
    getCesiumColor(type) {
        const trackType = (type || '').toLowerCase();
        switch (trackType) {
            case 'aircraft': return Cesium.Color.BLUE;
            case 'vessel': return Cesium.Color.GREEN;
            case 'vehicle': return Cesium.Color.ORANGE;
            default: return Cesium.Color.GRAY;
        }
    }
    
    switchTo3D() {
        console.log('Switching to 3D Battle View...');
        this.is3DMode = true;
        
        // Hide Leaflet map and show Cesium map
        const leafletContainer = document.getElementById('leaflet-map');
        const cesiumContainer = document.getElementById('cesium-map');
        
        if (leafletContainer && cesiumContainer) {
            leafletContainer.classList.add('hidden');
            cesiumContainer.classList.remove('hidden');
        }
        
        // Update map mode display
        const modeDisplay = document.getElementById('map-mode-display');
        if (modeDisplay) {
            modeDisplay.textContent = '3D Battle';
        }
        
        // Destroy any existing MapManager Cesium viewer to prevent conflicts
        if (this.cesiumViewer) {
            try {
                this.cesiumViewer.destroy();
                this.cesiumViewer = null;
                console.log('Destroyed basic Cesium viewer to prevent conflicts');
            } catch (error) {
                console.warn('Error destroying basic Cesium viewer:', error);
            }
        }
        
        // Use the Advanced Cesium Manager instead
        if (window.advancedCesium && window.advancedCesium.viewer) {
            console.log('Activating Advanced Cesium 3D Battle View...');
            // Call show() method to trigger optimal view reset
            window.advancedCesium.show();
            
            setTimeout(() => {
                try {
                    // Update tracks using advanced Cesium
                    if (this.tracks && this.tracks.length > 0) {
                        window.advancedCesium.updateTracks(this.tracks);
                        console.log(`Updated 3D Battle View with ${this.tracks.length} tracks`);
                    }
                    console.log('3D Battle View activated successfully');
                } catch (error) {
                    console.error('Error activating advanced 3D view:', error);
                }
            }, 200);
        } else {
            console.error('Advanced Cesium Manager not available');
        }
    }
    
    switchTo2D() {
        console.log('Switching to 2D Standard View...');
        this.is3DMode = false;
        
        // Show Leaflet map and hide Cesium map
        const leafletContainer = document.getElementById('leaflet-map');
        const cesiumContainer = document.getElementById('cesium-map');
        
        if (leafletContainer && cesiumContainer) {
            leafletContainer.classList.remove('hidden');
            cesiumContainer.classList.add('hidden');
        }
        
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
                console.log('Resizing Leaflet map and updating tracks...');
            }, 100);
        }
    }
    
    clearAllTracks() {
        this.tracks = [];
        
        // Clear Leaflet markers
        if (this.leafletMap) {
            this.trackMarkers.forEach(marker => {
                this.leafletMap.removeLayer(marker);
            });
            this.trackMarkers.clear();
        }
        
        // Clear Cesium entities
        if (this.cesiumViewer) {
            this.cesiumViewer.entities.removeAll();
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
