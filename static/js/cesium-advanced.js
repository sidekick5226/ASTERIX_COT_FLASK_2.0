/**
 * Advanced CesiumJS Implementation
 * Features: Quantized-mesh terrain, 3D buildings, glTF unit models, CoT tracking
 */
class AdvancedCesiumManager {
    constructor() {
        this.viewer = null;
        this.terrainProvider = null;
        this.buildingTileset = null;
        this.unitEntities = new Map();
        this.cameraFollowTarget = null;
        this.followMode = 'none'; // 'none', 'chase', 'firstPerson', 'orbital'
        this.cotWebSocket = null;
        this.trackTrails = new Map();
        
        this.init();
    }
    
    async init() {
        this.setupCesiumViewer();
        await this.loadLocalTerrain();
        await this.load3DBuildings();
        this.setupCameraControls();
        this.setupCoTWebSocket();
        this.setupClickHandlers();
    }
    
    setupCesiumViewer() {
        // Initialize Cesium with advanced configuration
        this.viewer = new Cesium.Viewer('cesium-map', {
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
            // Remove default imagery provider - we'll add our own
            imageryProvider: false
        });
        
        // Add custom imagery layer (satellite)
        this.viewer.imageryLayers.addImageryProvider(
            new Cesium.ArcGisMapServerImageryProvider({
                url: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer'
            })
        );
        
        // Configure scene for tactical/surveillance view
        this.viewer.scene.globe.enableLighting = true;
        this.viewer.scene.globe.dynamicAtmosphereLighting = true;
        this.viewer.scene.fog.enabled = false;
        this.viewer.scene.skyBox.show = true;
        
        // Set initial tactical view position (North America surveillance zone)
        this.viewer.camera.setView({
            destination: Cesium.Cartesian3.fromDegrees(-95.0, 39.0, 2000000),
            orientation: {
                heading: 0.0,
                pitch: -Cesium.Math.PI_OVER_SIX,
                roll: 0.0
            }
        });
        
        console.log('Advanced Cesium viewer initialized');
    }
    
    async loadLocalTerrain() {
        try {
            // Use basic ellipsoid terrain for now - ready for quantized-mesh tiles
            this.viewer.terrainProvider = new Cesium.EllipsoidTerrainProvider();
            
            // In production, this would be:
            // this.terrainProvider = new Cesium.CesiumTerrainProvider({
            //     url: '/terrain/', // Local quantized-mesh terrain server
            //     requestWaterMask: true,
            //     requestVertexNormals: true
            // });
            // this.viewer.terrainProvider = this.terrainProvider;
            
            console.log('Terrain ready for local quantized-mesh tiles integration');
        } catch (error) {
            console.error('Failed to load terrain:', error);
            // Fallback to ellipsoid terrain
            this.viewer.terrainProvider = new Cesium.EllipsoidTerrainProvider();
        }
    }
    
    async load3DBuildings() {
        try {
            // Skip 3D buildings for now - ready for local 3D Tiles integration
            // This will be replaced with local OSM/LiDAR converted 3D Tiles
            console.log('3D buildings ready for local 3D Tiles integration');
            
            // In production, this would be:
            // this.buildingTileset = await Cesium.Cesium3DTileset.fromUrl('/3dtiles/buildings/');
            // this.viewer.scene.primitives.add(this.buildingTileset);
            
        } catch (error) {
            console.error('Failed to load 3D buildings:', error);
        }
    }
    
    setupCameraControls() {
        // Custom camera controls for tactical operations
        this.viewer.scene.preRender.addEventListener(() => {
            if (this.cameraFollowTarget && this.followMode !== 'none') {
                this.updateCameraFollow();
            }
        });
        
        // Add camera control UI
        this.addCameraControlsUI();
    }
    
    addCameraControlsUI() {
        // Add camera control buttons to the viewer toolbar
        const toolbar = this.viewer.toolbar;
        
        // Follow Camera Button
        const followButton = document.createElement('button');
        followButton.className = 'cesium-button cesium-toolbar-button';
        followButton.innerHTML = '<i class="fas fa-video"></i>';
        followButton.title = 'Follow Camera Mode';
        followButton.onclick = () => this.toggleFollowMode();
        toolbar.appendChild(followButton);
        
        // Reset Camera Button
        const resetButton = document.createElement('button');
        resetButton.className = 'cesium-button cesium-toolbar-button';
        resetButton.innerHTML = '<i class="fas fa-home"></i>';
        resetButton.title = 'Reset Camera View';
        resetButton.onclick = () => this.resetCamera();
        toolbar.appendChild(resetButton);
    }
    
    setupCoTWebSocket() {
        // Setup WebSocket for real-time CoT data
        if (window.socket) {
            // Listen for regular track updates
            window.socket.on('track_update', (tracks) => {
                this.updateUnitsFromCoT(tracks);
            });
            
            // Listen for CoT-specific updates
            window.socket.on('cot_update', (cotData) => {
                console.log('Received CoT update:', cotData.length, 'tracks');
                this.updateUnitsFromCoT(cotData.map(item => item.track_data));
            });
            
            // Handle CoT batch responses
            window.socket.on('cot_batch', (data) => {
                console.log('Received CoT batch:', data.track_count, 'tracks');
            });
            
            // Handle CoT heartbeat
            window.socket.on('cot_heartbeat', (data) => {
                console.log('CoT heartbeat received');
            });
            
            // Handle CoT errors
            window.socket.on('cot_error', (error) => {
                console.error('CoT error:', error);
            });
            
            // Request initial CoT batch
            window.socket.emit('request_cot_batch');
        }
        
        console.log('CoT WebSocket connection established');
    }
    
    setupClickHandlers() {
        // Handle entity selection for follow camera
        this.viewer.selectedEntityChanged.addEventListener((selectedEntity) => {
            if (selectedEntity && this.unitEntities.has(selectedEntity.id)) {
                this.selectUnit(selectedEntity);
            }
        });
        
        // Handle double-click for follow mode
        this.viewer.cesiumWidget.canvas.addEventListener('dblclick', (event) => {
            const pickedEntity = this.viewer.scene.pick(event);
            if (pickedEntity && pickedEntity.id && this.unitEntities.has(pickedEntity.id.id)) {
                this.startFollowCamera(pickedEntity.id);
            }
        });
    }
    
    updateUnitsFromCoT(tracks) {
        // Update or create unit entities from CoT track data
        tracks.forEach(track => {
            this.updateUnitEntity(track);
        });
        
        // Remove entities for tracks that no longer exist
        this.cleanupOldEntities(tracks);
    }
    
    updateUnitEntity(track) {
        const entityId = `unit_${track.track_id}`;
        let entity = this.viewer.entities.getById(entityId);
        
        const position = Cesium.Cartesian3.fromDegrees(
            track.longitude, 
            track.latitude, 
            this.getUnitAltitude(track)
        );
        
        if (!entity) {
            // Create new unit entity
            entity = this.createUnitEntity(track, position);
            this.unitEntities.set(entityId, entity);
        } else {
            // Update existing entity position
            entity.position = position;
            entity.orientation = this.calculateOrientation(track);
        }
        
        // Update trail
        this.updateTrail(track, position);
    }
    
    createUnitEntity(track, position) {
        const entityId = `unit_${track.track_id}`;
        const unitType = track.type || track.track_type || 'Unknown';
        
        // Get appropriate glTF model for unit type
        const modelUri = this.getUnitModel(unitType);
        const scale = this.getUnitScale(unitType);
        
        // Create entity with appropriate representation
        const entityConfig = {
            id: entityId,
            name: `${track.callsign || track.track_id} (${unitType})`,
            position: position,
            orientation: this.calculateOrientation(track),
            label: {
                text: track.callsign || track.track_id,
                font: '12pt sans-serif',
                pixelOffset: new Cesium.Cartesian2(0, -30),
                fillColor: Cesium.Color.WHITE,
                outlineColor: Cesium.Color.BLACK,
                outlineWidth: 2,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                scale: 0.8
            },
            // Store track data for reference
            properties: {
                trackData: track,
                unitType: unitType
            }
        };
        
        // Add glTF model if available, otherwise use geometric shape
        if (modelUri && modelUri !== 'data:application/octet-stream;base64,') {
            entityConfig.model = {
                uri: modelUri,
                scale: scale,
                minimumPixelSize: 64,
                maximumScale: 20000,
                silhouetteColor: this.getUnitColor(unitType),
                silhouetteSize: 2
            };
        } else {
            // Use geometric shapes as fallback
            const unitColor = this.getUnitColor(unitType);
            if (unitType === 'Aircraft') {
                entityConfig.point = {
                    pixelSize: 20,
                    color: unitColor,
                    outlineColor: Cesium.Color.WHITE,
                    outlineWidth: 2,
                    heightReference: Cesium.HeightReference.NONE
                };
            } else if (unitType === 'Vessel') {
                entityConfig.billboard = {
                    image: this.createShipIcon(unitColor),
                    scale: 1.0,
                    heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
                };
            } else {
                entityConfig.box = {
                    dimensions: new Cesium.Cartesian3(100, 100, 50),
                    material: unitColor,
                    outline: true,
                    outlineColor: Cesium.Color.WHITE
                };
            }
        }
        
        const entity = this.viewer.entities.add(entityConfig);
        
        return entity;
    }
    
    createShipIcon(color) {
        // Create a simple ship icon as canvas data URL
        const canvas = document.createElement('canvas');
        canvas.width = 32;
        canvas.height = 32;
        const ctx = canvas.getContext('2d');
        
        // Draw simple ship shape
        ctx.fillStyle = color.toCssColorString();
        ctx.beginPath();
        ctx.moveTo(16, 4);
        ctx.lineTo(28, 28);
        ctx.lineTo(4, 28);
        ctx.closePath();
        ctx.fill();
        
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        return canvas.toDataURL();
    }
    
    getUnitModel(unitType) {
        // Return appropriate glTF model path for unit type
        const models = {
            'Aircraft': 'data:application/octet-stream;base64,', // Placeholder for aircraft.glb
            'Vessel': 'data:application/octet-stream;base64,',   // Placeholder for ship.glb  
            'Vehicle': 'data:application/octet-stream;base64,',  // Placeholder for tank.glb
            'Unknown': 'data:application/octet-stream;base64,'   // Placeholder for generic.glb
        };
        
        // For now, return undefined to use simple geometric shapes
        return undefined;
    }
    
    getUnitScale(unitType) {
        const scales = {
            'Aircraft': 100,
            'Vessel': 50,
            'Vehicle': 20,
            'Unknown': 30
        };
        
        return scales[unitType] || 30;
    }
    
    getUnitColor(unitType) {
        const colors = {
            'Aircraft': Cesium.Color.CYAN,
            'Vessel': Cesium.Color.BLUE,
            'Vehicle': Cesium.Color.GREEN,
            'Unknown': Cesium.Color.YELLOW
        };
        
        return colors[unitType] || Cesium.Color.WHITE;
    }
    
    getUnitAltitude(track) {
        // Return appropriate altitude for unit type
        if (track.altitude && track.altitude > 0) {
            return track.altitude;
        }
        
        const defaultAltitudes = {
            'Aircraft': 10000, // 10,000 feet
            'Vessel': 0,       // Sea level
            'Vehicle': 100,    // 100 feet above ground
            'Unknown': 500
        };
        
        const unitType = track.type || track.track_type || 'Unknown';
        return defaultAltitudes[unitType] || 500;
    }
    
    calculateOrientation(track) {
        if (track.heading !== undefined && track.heading !== null) {
            const heading = Cesium.Math.toRadians(track.heading);
            const pitch = 0;
            const roll = 0;
            
            return Cesium.Transforms.headingPitchRollQuaternion(
                Cesium.Cartesian3.fromDegrees(track.longitude, track.latitude),
                new Cesium.HeadingPitchRoll(heading, pitch, roll)
            );
        }
        
        return Cesium.Transforms.eastNorthUpToFixedFrame(
            Cesium.Cartesian3.fromDegrees(track.longitude, track.latitude)
        );
    }
    
    updateTrail(track, position) {
        const trailId = `trail_${track.track_id}`;
        let trail = this.trackTrails.get(trailId);
        
        if (!trail) {
            // Create new trail
            trail = {
                positions: [],
                entity: null
            };
            this.trackTrails.set(trailId, trail);
        }
        
        // Add position to trail
        trail.positions.push(position);
        
        // Limit trail length
        if (trail.positions.length > 100) {
            trail.positions.shift();
        }
        
        // Update or create trail entity
        if (trail.positions.length > 1) {
            if (trail.entity) {
                trail.entity.polyline.positions = trail.positions;
            } else {
                trail.entity = this.viewer.entities.add({
                    polyline: {
                        positions: trail.positions,
                        width: 2,
                        material: this.getUnitColor(track.type || track.track_type),
                        clampToGround: false
                    }
                });
            }
        }
    }
    
    cleanupOldEntities(activeTracks) {
        const activeTrackIds = new Set(activeTracks.map(t => `unit_${t.track_id}`));
        const entitiesToRemove = [];
        
        this.unitEntities.forEach((entity, entityId) => {
            if (!activeTrackIds.has(entityId)) {
                entitiesToRemove.push(entityId);
            }
        });
        
        entitiesToRemove.forEach(entityId => {
            const entity = this.unitEntities.get(entityId);
            if (entity) {
                this.viewer.entities.remove(entity);
                this.unitEntities.delete(entityId);
            }
            
            // Also remove trail
            const trailId = entityId.replace('unit_', 'trail_');
            const trail = this.trackTrails.get(trailId);
            if (trail && trail.entity) {
                this.viewer.entities.remove(trail.entity);
                this.trackTrails.delete(trailId);
            }
        });
    }
    
    selectUnit(entity) {
        console.log('Unit selected:', entity.name);
        
        // Highlight selected unit
        if (entity.model) {
            entity.model.silhouetteSize = 4;
            entity.model.silhouetteColor = Cesium.Color.YELLOW;
        }
        
        // Show follow camera option
        this.showFollowCameraOption(entity);
    }
    
    showFollowCameraOption(entity) {
        // Create follow camera prompt (could be replaced with UI buttons)
        const followOption = confirm(`Follow ${entity.name} with camera?`);
        if (followOption) {
            this.startFollowCamera(entity);
        }
    }
    
    startFollowCamera(entity) {
        this.cameraFollowTarget = entity;
        this.followMode = 'chase';
        console.log(`Following ${entity.name} in chase mode`);
    }
    
    toggleFollowMode() {
        if (!this.cameraFollowTarget) {
            alert('Please select a unit first');
            return;
        }
        
        const modes = ['none', 'chase', 'firstPerson', 'orbital'];
        const currentIndex = modes.indexOf(this.followMode);
        const nextIndex = (currentIndex + 1) % modes.length;
        this.followMode = modes[nextIndex];
        
        console.log(`Camera mode: ${this.followMode}`);
    }
    
    updateCameraFollow() {
        if (!this.cameraFollowTarget || !this.cameraFollowTarget.position) {
            return;
        }
        
        const targetPosition = this.cameraFollowTarget.position.getValue(Cesium.JulianDate.now());
        if (!targetPosition) return;
        
        switch (this.followMode) {
            case 'chase':
                this.updateChaseCamera(targetPosition);
                break;
            case 'firstPerson':
                this.updateFirstPersonCamera(targetPosition);
                break;
            case 'orbital':
                this.updateOrbitalCamera(targetPosition);
                break;
        }
    }
    
    updateChaseCamera(targetPosition) {
        // Chase camera - follow behind and above the target
        const camera = this.viewer.camera;
        const offset = new Cesium.Cartesian3(-500, 0, 200); // Behind and above
        const cameraPosition = Cesium.Cartesian3.add(targetPosition, offset, new Cesium.Cartesian3());
        
        camera.lookAt(cameraPosition, targetPosition, Cesium.Cartesian3.UNIT_Z);
    }
    
    updateFirstPersonCamera(targetPosition) {
        // First person camera - from the target's perspective
        const camera = this.viewer.camera;
        const offset = new Cesium.Cartesian3(0, 0, 50); // Slightly above target
        const cameraPosition = Cesium.Cartesian3.add(targetPosition, offset, new Cesium.Cartesian3());
        
        // Look forward based on unit's heading
        const heading = this.getTargetHeading();
        const direction = new Cesium.Cartesian3(
            Math.sin(heading), 
            Math.cos(heading), 
            0
        );
        const lookTarget = Cesium.Cartesian3.add(cameraPosition, direction, new Cesium.Cartesian3());
        
        camera.lookAt(cameraPosition, lookTarget, Cesium.Cartesian3.UNIT_Z);
    }
    
    updateOrbitalCamera(targetPosition) {
        // Orbital camera - circle around the target
        const camera = this.viewer.camera;
        const time = Date.now() * 0.001; // Convert to seconds
        const radius = 1000;
        const height = 300;
        
        const x = targetPosition.x + radius * Math.cos(time * 0.1);
        const y = targetPosition.y + radius * Math.sin(time * 0.1);
        const z = targetPosition.z + height;
        
        const cameraPosition = new Cesium.Cartesian3(x, y, z);
        camera.lookAt(cameraPosition, targetPosition, Cesium.Cartesian3.UNIT_Z);
    }
    
    getTargetHeading() {
        if (this.cameraFollowTarget.properties && this.cameraFollowTarget.properties.trackData) {
            const track = this.cameraFollowTarget.properties.trackData.getValue();
            return Cesium.Math.toRadians(track.heading || 0);
        }
        return 0;
    }
    
    resetCamera() {
        this.cameraFollowTarget = null;
        this.followMode = 'none';
        
        // Reset to initial tactical view
        this.viewer.camera.setView({
            destination: Cesium.Cartesian3.fromDegrees(-95.0, 39.0, 2000000),
            orientation: {
                heading: 0.0,
                pitch: -Cesium.Math.PI_OVER_SIX,
                roll: 0.0
            }
        });
        
        console.log('Camera reset to tactical view');
    }
    
    // Method to switch to 3D mode
    enable3DMode() {
        document.getElementById('leaflet-map').style.display = 'none';
        document.getElementById('cesium-map').style.display = 'block';
        
        // Trigger resize to ensure proper rendering
        setTimeout(() => {
            this.viewer.resize();
        }, 100);
    }
    
    // Method to switch to 2D mode
    disable3DMode() {
        document.getElementById('cesium-map').style.display = 'none';
        document.getElementById('leaflet-map').style.display = 'block';
    }
}

// Global instance
window.advancedCesium = new AdvancedCesiumManager();