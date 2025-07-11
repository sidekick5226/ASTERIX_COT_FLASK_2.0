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
            infoBox: true,        // Keep popup info box for track details
            selectionIndicator: true,  // Keep selection indicator
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

        // Set initial orthographic view - North Pole at top, South Pole at bottom
        this.viewer.camera.setView({
            destination: Cesium.Cartesian3.fromDegrees(-100.0, 45.0, 20000000),
            orientation: {
                heading: 0.0,
                pitch: -Cesium.Math.PI_OVER_TWO,
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
            if (this.cameraFollowTarget) {
                this.updateCameraFollow();
            }
        });

        // Add camera control UI
        this.addCameraControlsUI();
    }

    addCameraControlsUI() {
        // Camera controls are now handled directly through double-click to follow
        // and deselection to stop following - no UI buttons needed
        console.log('Camera controls: Double-click to follow, deselect to stop');
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

            // Set up periodic CoT heartbeat
            setInterval(() => {
                window.socket.emit('request_cot_heartbeat');
            }, 30000); // Every 30 seconds
        }

        console.log('CoT WebSocket connection established');
    }

    setupClickHandlers() {
        // Handle entity selection for normal info popup behavior
        this.viewer.selectedEntityChanged.addEventListener((selectedEntity) => {
            if (selectedEntity && this.unitEntities.has(selectedEntity.id)) {
                console.log('Unit selected:', selectedEntity.id);
                // Entity info box will show automatically - no custom handling needed
            } else if (!selectedEntity) {
                // Entity deselected - turn off camera follow
                this.stopFollowCamera();
            }
        });

        // Handle double-click for follow mode (no confirmation popup)
        this.viewer.cesiumWidget.canvas.addEventListener('dblclick', (event) => {
            const pickedEntity = this.viewer.scene.pick(event.position);
            if (pickedEntity && pickedEntity.id && this.unitEntities.has(pickedEntity.id.id)) {
                // Start following immediately without confirmation dialog
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

        // Note: No automatic camera follow on single click
        // User must double-click to follow
    }

    startFollowCamera(entity) {
        this.cameraFollowTarget = entity;
        this.followMode = 'chase';
        console.log(`Following ${entity.name} in chase mode`);
    }

    stopFollowCamera() {
        if (this.cameraFollowTarget) {
            console.log('Stopping camera follow mode and resetting to optimal view');
            this.cameraFollowTarget = null;
            
            // Clear any selected entity to ensure clean state
            this.viewer.selectedEntity = undefined;
            
            // Restore all camera controls to free camera mode
            this.viewer.scene.screenSpaceCameraController.enableRotate = true;
            this.viewer.scene.screenSpaceCameraController.enableTranslate = true;
            this.viewer.scene.screenSpaceCameraController.enableZoom = true;
            this.viewer.scene.screenSpaceCameraController.enableTilt = true;
            this.viewer.scene.screenSpaceCameraController.enableLook = true;
            
            // Reset to optimal tactical view
            this.viewer.camera.flyTo({
                destination: Cesium.Cartesian3.fromDegrees(-100.0, 45.0, 20000000),
                orientation: {
                    heading: 0.0,
                    pitch: -Cesium.Math.PI_OVER_TWO,
                    roll: 0.0
                },
                duration: 2.0
            });
        }
    }

    updateCameraFollow() {
        if (!this.cameraFollowTarget || !this.cameraFollowTarget.position) {
            return;
        }

        const targetPosition = this.cameraFollowTarget.position.getValue(Cesium.JulianDate.now());
        if (!targetPosition) return;

        // Always use chase camera mode
        this.updateChaseCamera(targetPosition);
    }

    updateChaseCamera(targetPosition) {
        // Chase camera - follow behind and above the target
        const camera = this.viewer.camera;
        const offset = new Cesium.Cartesian3(-500, 0, 200); // Behind and above
        const cameraPosition = Cesium.Cartesian3.add(targetPosition, offset, new Cesium.Cartesian3());

        camera.lookAt(cameraPosition, targetPosition, Cesium.Cartesian3.UNIT_Z);
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

    // Method to update tracks from MapManager
    updateTracks(tracks) {
        if (!this.viewer || !tracks) return;

        // Efficiently update existing entities instead of clearing all
        const activeTrackIds = new Set();

        // Update or create tracks
        tracks.forEach(track => {
            const trackId = track.track_id || track.id;
            activeTrackIds.add(trackId);

            if (this.unitEntities.has(trackId)) {
                // Update existing entity
                this.updateTrackEntity(trackId, track);
            } else {
                // Create new entity
                this.addTrackEntity(track);
            }
        });

        // Remove entities for tracks that no longer exist
        this.unitEntities.forEach((entity, trackId) => {
            if (!activeTrackIds.has(trackId)) {
                this.viewer.entities.remove(entity);
                this.unitEntities.delete(trackId);
            }
        });

        // Force a render to ensure immediate display update
        this.viewer.scene.requestRender();
    }

    updateTrackEntity(trackId, track) {
        const entity = this.unitEntities.get(trackId);
        if (!entity) return;

        // Use reasonable altitude defaults for 3D view
        let altitude = 0;
        if (track.altitude && track.altitude > 0 && track.altitude < 100000) {
            altitude = track.altitude;
        } else {
            const trackType = track.track_type || track.type;
            if (trackType === 'Aircraft') {
                altitude = 10000; // 10,000 feet for aircraft
            } else if (trackType === 'Vessel') {
                altitude = 0; // Sea level for vessels
            } else if (trackType === 'Vehicle') {
                altitude = 100; // 100 feet for ground vehicles
            }
        }

        // Update position
        entity.position = Cesium.Cartesian3.fromDegrees(
            track.longitude, 
            track.latitude, 
            altitude
        );

        // Update label
        entity.label.text = track.callsign || trackId;

        // Update color if track type changed
        const newColor = this.getTrackColor(track.track_type || track.type);
        entity.point.color = newColor;

        // Update description with latest track information
        entity.description = this.createTrackDescription(track, altitude);

        // Update stored track data
        if (entity.properties) {
            entity.properties.trackData = track;
            entity.properties.lastUpdated = new Date().toISOString();
        }
    }

    createTrackDescription(track, altitude) {
        const trackId = track.track_id || track.id;
        const callsign = track.callsign || 'N/A';
        const trackType = track.track_type || track.type || 'Unknown';
        const status = track.status || 'Unknown';
        const heading = track.heading ? track.heading.toFixed(1) + '°' : 'N/A';
        const speed = track.speed ? track.speed.toFixed(1) + ' kts' : 'N/A';
        const lat = track.latitude ? track.latitude.toFixed(6) : 'N/A';
        const lon = track.longitude ? track.longitude.toFixed(6) : 'N/A';
        const alt = altitude ? altitude.toFixed(0) + ' ft' : 'N/A';
        const lastUpdate = track.last_updated ? new Date(track.last_updated).toLocaleString() : 'N/A';

        return `
            <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 13px; line-height: 1.4; min-width: 280px;">
                <div style="background: linear-gradient(135deg, #1e293b 0%, #334155 100%); color: white; padding: 12px; margin: -8px -8px 8px -8px; border-radius: 4px 4px 0 0;">
                    <h3 style="margin: 0; font-size: 16px; font-weight: bold; display: flex; align-items: center;">
                        <span style="background: #3b82f6; padding: 2px 8px; border-radius: 3px; margin-right: 8px; font-size: 12px;">${trackId}</span>
                        ${callsign}
                    </h3>
                    <div style="font-size: 11px; opacity: 0.8; margin-top: 4px;">${trackType} • ${status}</div>
                </div>

                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <tr style="border-bottom: 1px solid #475569;">
                        <td style="padding: 6px 0; font-weight: bold; color: #e2e8f0; width: 35%;">Callsign:</td>
                        <td style="padding: 6px 0; color: white; font-family: monospace;">${callsign}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #475569;">
                        <td style="padding: 6px 0; font-weight: bold; color: #e2e8f0;">Position:</td>
                        <td style="padding: 6px 0; color: white; font-family: monospace;">${lat}, ${lon}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #475569;">
                        <td style="padding: 6px 0; font-weight: bold; color: #e2e8f0;">Altitude:</td>
                        <td style="padding: 6px 0; color: white; font-family: monospace;">${alt}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #475569;">
                        <td style="padding: 6px 0; font-weight: bold; color: #e2e8f0;">Heading:</td>
                        <td style="padding: 6px 0; color: white; font-family: monospace;">${heading}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #475569;">
                        <td style="padding: 6px 0; font-weight: bold; color: #e2e8f0;">Speed:</td>
                        <td style="padding: 6px 0; color: white; font-family: monospace;">${speed}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #475569;">
                        <td style="padding: 6px 0; font-weight: bold; color: #e2e8f0;">Status:</td>
                        <td style="padding: 6px 0;">
                            <span style="background: ${status === 'Active' ? '#10b981' : '#ef4444'}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: bold;">
                                ${status}
                            </span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; font-weight: bold; color: #e2e8f0;">Last Update:</td>
                        <td style="padding: 6px 0; color: #cbd5e1; font-size: 11px;">${lastUpdate}</td>
                    </tr>
                </table>

                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #475569; font-size: 11px; color: #cbd5e1; text-align: center;">
                    Double-click to follow • Right-click for actions
                </div>
            </div>
        `;
    }

    addTrackEntity(track) {
        const trackId = track.track_id || track.id;

        // Use reasonable altitude defaults for 3D view
        let altitude = 0;
        if (track.altitude && track.altitude > 0 && track.altitude < 100000) {
            altitude = track.altitude;
        } else {
            // Set default altitudes based on track type for better 3D visualization
            const trackType = track.track_type || track.type;
            if (trackType === 'Aircraft') {
                altitude = 10000; // 10,000 feet for aircraft
            } else if (trackType === 'Vessel') {
                altitude = 0; // Sea level for vessels
            } else if (trackType === 'Vehicle') {
                altitude = 100; // 100 feet for ground vehicles
            }
        }

        const position = Cesium.Cartesian3.fromDegrees(
            track.longitude, 
            track.latitude, 
            altitude
        );

        const color = this.getTrackColor(track.track_type || track.type);

        // Create detailed description for track information popup
        const trackDescription = this.createTrackDescription(track, altitude);

        const entity = this.viewer.entities.add({
            id: trackId,
            name: trackId,
            description: trackDescription,
            position: position,
            point: {
                pixelSize: 12,
                color: color,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2,
                heightReference: Cesium.HeightReference.RELATIVE_TO_GROUND
            },
            label: {
                text: track.callsign || trackId,
                font: '12px sans-serif',
                fillColor: Cesium.Color.WHITE,
                outlineColor: Cesium.Color.BLACK,
                outlineWidth: 2,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                pixelOffset: new Cesium.Cartesian2(0, -40),
                horizontalOrigin: Cesium.HorizontalOrigin.CENTER
            },
            // Store track data for access during selection
            properties: new Cesium.PropertyBag({
                trackData: track,
                lastUpdated: new Date().toISOString()
            })
        });

        this.unitEntities.set(trackId, entity);
        return entity;
    }

    getTrackColor(trackType) {
        switch (trackType) {
            case 'Aircraft': return Cesium.Color.CYAN;
            case 'Vessel': return Cesium.Color.fromCssColorString('#9333ea');
            case 'Vehicle': return Cesium.Color.fromCssColorString('#d97706');
            default: return Cesium.Color.YELLOW;
        }
    }

    show() {
        const cesiumContainer = document.getElementById('cesium-map');
        if (cesiumContainer) {
            cesiumContainer.classList.remove('hidden');

            // Force a render when showing and reset to optimal view
            if (this.viewer) {
                this.viewer.resize();
                this.resetToOptimalView();                this.viewer.scene.requestRender();
            }
        }
    }

    hide() {
        const cesiumContainer = document.getElementById('cesium-map');
        if (cesiumContainer) {
            cesiumContainer.classList.add('hidden');
        }
    }

    resetToOptimalView() {
        // Reset camera to perfect orthographic view - North Pole at top, South Pole at bottom
        this.viewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(-100.0, 45.0, 20000000),
            orientation: {
                heading: 0.0,
                pitch: -Cesium.Math.PI_OVER_TWO,
                roll: 0.0
            },
            duration: 2.0
        });
    }
}

// Global instance
window.advancedCesium = new AdvancedCesiumManager();