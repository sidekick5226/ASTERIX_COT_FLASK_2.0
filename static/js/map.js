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
            
            // Try to initialize iTwin Platform integration
            await this.initializeiTwinIntegration();
            
            // Basic lighting 
            this.cesiumViewer.scene.globe.enableLighting = true;
            this.cesiumViewer.scene.globe.showWaterEffect = true;
            
            // Allow close zoom
            this.cesiumViewer.scene.screenSpaceCameraController.minimumZoomDistance = 10.0;
            
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
    
    async initializeiTwinIntegration() {
        try {
            // Configure iTwin Platform if available
            if (typeof Cesium.ITwinPlatform !== 'undefined') {
                // This would be configured with your actual iTwin credentials
                // For demo purposes, we'll use a placeholder
                console.log('iTwin Platform detected, attempting integration...');
                
                // You would set your actual share key here
                // Cesium.ITwinPlatform.defaultShareKey = "your-actual-share-key";
                
                // Define known iTwin datasets for major cities
                this.iTwinDatasets = {
                    // Philadelphia example (from your code)
                    'philadelphia': {
                        iTwinId: "535a24a3-9b29-4e23-bb5d-9cedb524c743",
                        realityMeshId: "85897090-3bcc-470b-bec7-20bb639cc1b9",
                        position: {
                            longitude: -75.1652,
                            latitude: 39.9526,
                            height: 500
                        }
                    },
                    // Add more cities as you get their iTwin IDs
                    'newyork': {
                        iTwinId: "example-itwin-id",
                        realityMeshId: "example-mesh-id", 
                        position: {
                            longitude: -74.0060,
                            latitude: 40.7128,
                            height: 500
                        }
                    }
                };
                
                console.log('iTwin integration configured with datasets for:', Object.keys(this.iTwinDatasets));
            } else {
                console.log('iTwin Platform not available, using standard terrain');
                this.setupStandardTerrain();
            }
        } catch (error) {
            console.error('Error initializing iTwin integration:', error);
            this.setupStandardTerrain();
        }
    }
    
    setupStandardTerrain() {
        // Fallback to standard imagery when iTwin is not available
        this.cesiumViewer.scene.imageryLayers.removeAll();
        this.cesiumViewer.scene.imageryLayers.addImageryProvider(
            new Cesium.TileMapServiceImageryProvider({
                url: Cesium.buildModuleUrl('Assets/Textures/NaturalEarthII')
            })
        );
    }
    
    async loadiTwinDataForLocation(latitude, longitude) {
        if (!this.iTwinDatasets || typeof Cesium.ITwinPlatform === 'undefined') {
            return false;
        }
        
        try {
            // Find the closest iTwin dataset to the given coordinates
            let closestDataset = null;
            let minDistance = Infinity;
            
            for (const [city, dataset] of Object.entries(this.iTwinDatasets)) {
                const distance = this.calculateDistance(
                    latitude, longitude,
                    dataset.position.latitude, dataset.position.longitude
                );
                
                if (distance < minDistance && distance < 50) { // Within 50km
                    minDistance = distance;
                    closestDataset = dataset;
                }
            }
            
            if (closestDataset) {
                console.log('Loading iTwin reality mesh for location...');
                
                const tileset = await Cesium.ITwinData.createTilesetForRealityDataId(
                    closestDataset.iTwinId,
                    closestDataset.realityMeshId
                );
                
                if (tileset) {
                    this.cesiumViewer.scene.primitives.add(tileset);
                    tileset.maximumScreenSpaceError = 2;
                    
                    // Add labels if available
                    try {
                        const labelImageryLayer = Cesium.ImageryLayer.fromProviderAsync(
                            Cesium.IonImageryProvider.fromAssetId(2411391)
                        );
                        tileset.imageryLayers.add(labelImageryLayer);
                    } catch (labelError) {
                        console.log('Labels not available for this iTwin dataset');
                    }
                    
                    console.log('iTwin reality mesh loaded successfully');
                    return true;
                }
            }
            
            return false;
        } catch (error) {
            console.error('Error loading iTwin data:', error);
            return false;
        }
    }
    
    calculateDistance(lat1, lon1, lat2, lon2) {
        // Calculate distance between two points using Haversine formula
        const R = 6371; // Earth's radius in kilometers
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }
    
    createSimpleBuildings() {
        // Create a few simple buildings for demonstration
        const buildings = [
            { lat: 40.7128, lon: -74.0060, height: 100 }, // New York
            { lat: 34.0522, lon: -118.2437, height: 80 }, // Los Angeles
            { lat: 41.8781, lon: -87.6298, height: 120 }, // Chicago
        ];
        
        buildings.forEach((building, index) => {
            this.cesiumViewer.entities.add({
                position: Cesium.Cartesian3.fromDegrees(
                    building.lon,
                    building.lat,
                    building.height / 2
                ),
                box: {
                    dimensions: new Cesium.Cartesian3(50, 50, building.height),
                    material: Cesium.Color.GRAY.withAlpha(0.8),
                    outline: true,
                    outlineColor: Cesium.Color.BLACK
                }
            });
        });
        
        console.log('Simple 3D buildings created');
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
    
    async focusOnTrack(trackId) {
        const track = this.tracks.find(t => t.track_id === trackId);
        if (!track) return;
        
        if (this.is3DMode && this.cesiumViewer) {
            // Try to load iTwin data for this location first
            const iTwinLoaded = await this.loadiTwinDataForLocation(track.latitude, track.longitude);
            
            if (iTwinLoaded) {
                console.log('Using high-resolution iTwin data for track location');
            }
            
            // Focus on track in 3D
            this.cesiumViewer.camera.flyTo({
                destination: Cesium.Cartesian3.fromDegrees(
                    track.longitude, 
                    track.latitude, 
                    iTwinLoaded ? 500 : 10000  // Closer zoom if we have detailed data
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
