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
    
    async init() {
        console.log('Initializing MapManager...');
        // Initialize both map views
        this.initLeafletMap();
        await this.initCesiumMap();
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
    
    async initCesiumMap() {
        // Initialize Cesium map (3D) with default configuration
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
                shouldAnimate: true
            });
            
            // Set initial camera position over North America
            this.cesiumViewer.camera.setView({
                destination: Cesium.Cartesian3.fromDegrees(-95.0, 39.0, 2000000),
                orientation: {
                    heading: 0.0,
                    pitch: -Cesium.Math.PI_OVER_SIX,
                    roll: 0.0
                }
            });
            
            // Ensure the globe and atmosphere are visible
            this.cesiumViewer.scene.globe.show = true;
            this.cesiumViewer.scene.skyBox.show = true;
            this.cesiumViewer.scene.skyAtmosphere.show = true;
            
            // Add high-resolution satellite imagery
            this.cesiumViewer.scene.imageryLayers.removeAll();
            
            // Use Bing Maps for high-resolution satellite imagery
            this.cesiumViewer.scene.imageryLayers.addImageryProvider(
                new Cesium.BingMapsImageryProvider({
                    url: 'https://dev.virtualearth.net',
                    mapStyle: Cesium.BingMapsStyle.AERIAL_WITH_LABELS,
                    credit: 'Bing Maps'
                })
            );
            
            // Add world terrain for realistic 3D surface
            try {
                this.cesiumViewer.terrainProvider = Cesium.createWorldTerrain({
                    requestWaterMask: true,
                    requestVertexNormals: true
                });
            } catch (terrainError) {
                console.log('World terrain not available, using default');
            }
            
            // Enhanced lighting and visual effects
            this.cesiumViewer.scene.globe.enableLighting = true;
            this.cesiumViewer.scene.globe.showWaterEffect = true;
            this.cesiumViewer.scene.globe.dynamicAtmosphereLighting = true;
            
            // Enable depth testing for proper 3D layering
            this.cesiumViewer.scene.globe.depthTestAgainstTerrain = true;
            
            // Allow very close zoom for detailed inspection (1 meter minimum)
            this.cesiumViewer.scene.screenSpaceCameraController.minimumZoomDistance = 1.0;
            
            // Enable high-quality rendering
            this.cesiumViewer.scene.postProcessStages.fxaa.enabled = true;
            this.cesiumViewer.scene.highDynamicRange = true;
            
            // Configure for high detail rendering
            this.cesiumViewer.scene.globe.maximumScreenSpaceError = 0.5;
            this.cesiumViewer.scene.globe.tileCacheSize = 2000;
            
            // Wait for the globe to load before creating buildings
            setTimeout(() => {
                this.createSimpleBuildings();
            }, 1000);
            
            console.log('Cesium 3D Map initialized successfully');
            
            // Force a render to ensure the globe appears
            this.cesiumViewer.scene.requestRender();
            
        } catch (error) {
            console.error('Error initializing Cesium map:', error);
            this.cesiumViewer = null;
        }
    }
    
    async createSimpleBuildings() {
        // Try to load real 3D buildings from Cesium Ion
        try {
            const osmBuildings = await Cesium.Cesium3DTileset.fromIonAssetId(96188);
            this.cesiumViewer.scene.primitives.add(osmBuildings);
            
            // Style buildings for better visibility
            osmBuildings.style = new Cesium.Cesium3DTileStyle({
                color: 'rgb(200, 200, 200)',
                show: true
            });
            
            console.log('Real 3D buildings loaded');
        } catch (error) {
            console.log('Real buildings not available, creating procedural ones');
            
            // Create detailed building clusters in major cities
            const cities = [
                { name: 'New York', lat: 40.7128, lon: -74.0060, count: 100 },
                { name: 'Los Angeles', lat: 34.0522, lon: -118.2437, count: 80 },
                { name: 'Chicago', lat: 41.8781, lon: -87.6298, count: 60 },
                { name: 'Houston', lat: 29.7604, lon: -95.3698, count: 50 },
                { name: 'Phoenix', lat: 33.4484, lon: -112.0740, count: 40 }
            ];
            
            cities.forEach(city => {
                for (let i = 0; i < city.count; i++) {
                    const latOffset = (Math.random() - 0.5) * 0.03;
                    const lonOffset = (Math.random() - 0.5) * 0.03;
                    const height = Math.random() * 300 + 30;
                    
                    this.cesiumViewer.entities.add({
                        position: Cesium.Cartesian3.fromDegrees(
                            city.lon + lonOffset,
                            city.lat + latOffset,
                            height / 2
                        ),
                        box: {
                            dimensions: new Cesium.Cartesian3(
                                Math.random() * 60 + 20,
                                Math.random() * 60 + 20,
                                height
                            ),
                            material: Cesium.Color.fromRandom({
                                red: 0.6,
                                green: 0.6,
                                blue: 0.6,
                                alpha: 0.9
                            }),
                            outline: true,
                            outlineColor: Cesium.Color.BLACK
                        }
                    });
                }
            });
            
            console.log('Procedural 3D buildings created');
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
        
        // Always update both views to keep them synchronized
        if (this.leafletMap) {
            this.updateLeafletTracks(tracks);
        }
        
        if (this.cesiumViewer) {
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
        
        // Clear track entities only (preserve buildings)
        const entities = this.cesiumViewer.entities.values;
        for (let i = entities.length - 1; i >= 0; i--) {
            const entity = entities[i];
            if (entity.id && entity.id.startsWith('TRK')) {
                this.cesiumViewer.entities.remove(entity);
            }
        }
        
        // Add new track entities
        tracks.forEach(track => {
            const trackId = track.track_id;
            
            // Determine altitude based on track type with realistic values
            let altitude = 0;
            if (track.type === 'Aircraft') {
                altitude = track.altitude || 10000; // Default 10,000 feet for aircraft
            } else if (track.type === 'Vessel') {
                altitude = 0; // Sea level for vessels
            } else if (track.type === 'Vehicle') {
                altitude = 100; // 100 feet for ground vehicles
            }
            
            // Create entity positioned on the terrain
            const position = Cesium.Cartesian3.fromDegrees(
                track.longitude,
                track.latitude,
                altitude
            );
            
            const entity = {
                id: trackId,
                position: position,
                point: {
                    pixelSize: 12,
                    color: this.getCesiumColor(track.type),
                    outlineColor: Cesium.Color.WHITE,
                    outlineWidth: 2,
                    heightReference: altitude > 0 ? Cesium.HeightReference.NONE : Cesium.HeightReference.CLAMP_TO_GROUND,
                    disableDepthTestDistance: Number.POSITIVE_INFINITY
                },
                label: {
                    text: `${track.track_id}\n${track.callsign || 'Unknown'}`,
                    font: '10pt monospace',
                    style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                    fillColor: Cesium.Color.WHITE,
                    outlineColor: Cesium.Color.BLACK,
                    outlineWidth: 2,
                    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                    pixelOffset: new Cesium.Cartesian2(0, -10),
                    heightReference: altitude > 0 ? Cesium.HeightReference.NONE : Cesium.HeightReference.CLAMP_TO_GROUND,
                    disableDepthTestDistance: Number.POSITIVE_INFINITY
                },
                description: `
                    <div style="font-family: monospace; font-size: 12px;">
                        <strong>Track ID:</strong> ${track.track_id}<br>
                        <strong>Callsign:</strong> ${track.callsign || 'Unknown'}<br>
                        <strong>Type:</strong> ${track.type}<br>
                        <strong>Position:</strong> ${track.latitude.toFixed(4)}, ${track.longitude.toFixed(4)}<br>
                        <strong>Altitude:</strong> ${altitude} ft<br>
                        <strong>Heading:</strong> ${track.heading ? track.heading.toFixed(1) + '°' : 'Unknown'}<br>
                        <strong>Speed:</strong> ${track.speed ? track.speed.toFixed(1) + ' knots' : 'Unknown'}<br>
                        <strong>Status:</strong> ${track.status}
                    </div>
                `
            };
            
            this.cesiumViewer.entities.add(entity);
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
        document.getElementById('leaflet-map').style.display = 'none';
        document.getElementById('cesium-map').style.display = 'block';
        
        // Update map mode display
        const modeDisplay = document.getElementById('map-mode-display');
        if (modeDisplay) {
            modeDisplay.textContent = '3D Battle Mode';
        }
        
        // Check if Cesium viewer exists
        if (!this.cesiumViewer) {
            console.error('Cesium viewer not initialized - attempting to reinitialize...');
            this.initCesiumMap();
        }
        
        // Resize and update Cesium viewer
        if (this.cesiumViewer) {
            console.log('Resizing Cesium viewer and updating tracks...');
            setTimeout(() => {
                try {
                    this.cesiumViewer.resize();
                    this.cesiumViewer.scene.requestRender();
                    // Force update with current tracks to ensure synchronization
                    if (this.tracks && this.tracks.length > 0) {
                        this.updateCesiumTracks(this.tracks);
                        console.log(`Updated 3D Battle View with ${this.tracks.length} tracks`);
                    }
                    console.log('3D Battle View activated successfully');
                } catch (error) {
                    console.error('Error activating 3D view:', error);
                }
            }, 200);
        } else {
            console.error('Failed to initialize 3D Battle View - WebGL may not be supported');
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
