/**
 * MIL-STD-2525 Symbol System for SurveillanceSentry
 * 
 * This module provides MIL-STD-2525 military symbology for track visualization
 * on both 2D and 3D maps. It includes symbol generation, color coding, and
 * standardized military symbol representation.
 */

class MilStd2525SymbolSystem {
    constructor() {
        this.symbols = new Map();
        this.init();
    }

    init() {
        this.setupSymbolDefinitions();
    }

    setupSymbolDefinitions() {
        // Define MIL-STD-2525 symbol mappings
        this.symbols.set('aircraft', {
            base: 'M',  // Military
            category: 'A',  // Air
            subcategory: 'MF',  // Military Fixed Wing
            svg: this.createAircraftSymbol(),
            color: '#3b82f6',
            size: 30
        });

        this.symbols.set('helicopter', {
            base: 'M',
            category: 'A',
            subcategory: 'MH',  // Military Helicopter
            svg: this.createHelicopterSymbol(),
            color: '#10b981',
            size: 30
        });

        this.symbols.set('vessel', {
            base: 'M',
            category: 'S',  // Surface
            subcategory: 'CL',  // Combatant Line
            svg: this.createVesselSymbol(),
            color: '#9333ea',
            size: 30
        });

        this.symbols.set('vehicle', {
            base: 'M',
            category: 'G',  // Ground
            subcategory: 'UC',  // Unit Combatant
            svg: this.createVehicleSymbol(),
            color: '#d97706',
            size: 30
        });

        this.symbols.set('ground_vehicle', {
            base: 'M',
            category: 'G',
            subcategory: 'UC',
            svg: this.createVehicleSymbol(),
            color: '#d97706',
            size: 30
        });

        this.symbols.set('radar_target', {
            base: 'U',  // Unknown
            category: 'G',
            subcategory: 'R',   // Radar
            svg: this.createRadarSymbol(),
            color: '#ef4444',
            size: 30
        });

        this.symbols.set('multilateration', {
            base: 'U',
            category: 'A',
            subcategory: 'ML',  // Multilateration
            svg: this.createMultilaterationSymbol(),
            color: '#f59e0b',
            size: 30
        });

        this.symbols.set('unknown', {
            base: 'U',
            category: 'U',
            subcategory: 'U',
            svg: this.createUnknownSymbol(),
            color: '#6b7280',
            size: 30
        });
    }

    /**
     * Get MIL-STD-2525 symbol for a track type
     * @param {string} trackType - The type of track
     * @param {string} affiliation - Friend, Hostile, Neutral, Unknown (default: Unknown)
     * @returns {Object} Symbol configuration
     */
    getSymbol(trackType, affiliation = 'Unknown') {
        const normalizedType = this.normalizeTrackType(trackType);
        const symbol = this.symbols.get(normalizedType) || this.symbols.get('unknown');
        
        // Modify color based on affiliation
        const symbolCopy = { ...symbol };
        symbolCopy.color = this.getAffiliationColor(affiliation);
        symbolCopy.svg = this.modifySymbolForAffiliation(symbol.svg, affiliation);
        
        return symbolCopy;
    }

    /**
     * Normalize track type names to standard values
     */
    normalizeTrackType(trackType) {
        if (!trackType) return 'unknown';
        
        const type = trackType.toLowerCase();
        
        // Map various input types to standard types
        const typeMap = {
            'aircraft': 'aircraft',
            'airplane': 'aircraft',
            'plane': 'aircraft',
            'helicopter': 'helicopter',
            'heli': 'helicopter',
            'vessel': 'vessel',
            'ship': 'vessel',
            'boat': 'vessel',
            'marine': 'vessel',
            'vehicle': 'ground_vehicle',
            'ground': 'ground_vehicle',
            'car': 'ground_vehicle',
            'truck': 'ground_vehicle',
            'ground_vehicle': 'ground_vehicle',
            'radar': 'radar_target',
            'radar_target': 'radar_target',
            'primary': 'radar_target',
            'mlat': 'multilateration',
            'multilateration': 'multilateration',
            'ads-b': 'aircraft',
            'adsb': 'aircraft'
        };

        return typeMap[type] || 'unknown';
    }

    /**
     * Get color based on affiliation
     */
    getAffiliationColor(affiliation) {
        switch (affiliation.toLowerCase()) {
            case 'friend':
            case 'friendly':
                return '#00ff00';  // Green
            case 'hostile':
            case 'enemy':
                return '#ff0000';  // Red
            case 'neutral':
                return '#ffff00';  // Yellow
            case 'unknown':
            default:
                return '#00ffff';  // Cyan
        }
    }

    /**
     * Create aircraft symbol (fixed wing)
     */
    createAircraftSymbol() {
        return `
            <svg width="30" height="30" viewBox="0 0 30 30" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <filter id="aircraftGlow">
                        <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
                        <feMerge>
                            <feMergeNode in="coloredBlur"/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                </defs>
                <!-- Main fuselage -->
                <rect x="13" y="8" width="4" height="14" fill="currentColor" stroke="black" stroke-width="1"/>
                <!-- Wings -->
                <rect x="6" y="13" width="18" height="4" fill="currentColor" stroke="black" stroke-width="1"/>
                <!-- Tail -->
                <rect x="11" y="6" width="8" height="4" fill="currentColor" stroke="black" stroke-width="1"/>
                <!-- Direction indicator -->
                <polygon points="15,6 12,2 18,2" fill="currentColor" stroke="black" stroke-width="1"/>
            </svg>
        `;
    }

    /**
     * Create helicopter symbol
     */
    createHelicopterSymbol() {
        return `
            <svg width="30" height="30" viewBox="0 0 30 30" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <filter id="heliGlow">
                        <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
                        <feMerge>
                            <feMergeNode in="coloredBlur"/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                </defs>
                <!-- Main fuselage -->
                <ellipse cx="15" cy="15" rx="8" ry="6" fill="currentColor" stroke="black" stroke-width="1"/>
                <!-- Main rotor -->
                <line x1="6" y1="15" x2="24" y2="15" stroke="currentColor" stroke-width="2"/>
                <!-- Tail rotor -->
                <line x1="23" y1="12" x2="23" y2="18" stroke="currentColor" stroke-width="2"/>
                <!-- Tail boom -->
                <rect x="22" y="13" width="6" height="4" fill="currentColor" stroke="black" stroke-width="1"/>
                <!-- Direction indicator -->
                <polygon points="15,8 12,4 18,4" fill="currentColor" stroke="black" stroke-width="1"/>
            </svg>
        `;
    }

    /**
     * Create vessel symbol
     */
    createVesselSymbol() {
        return `
            <svg width="30" height="30" viewBox="0 0 30 30" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <filter id="vesselGlow">
                        <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
                        <feMerge>
                            <feMergeNode in="coloredBlur"/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                </defs>
                <!-- Hull -->
                <path d="M 5 20 L 25 20 L 23 15 L 7 15 Z" fill="currentColor" stroke="black" stroke-width="1"/>
                <!-- Superstructure -->
                <rect x="10" y="10" width="10" height="8" fill="currentColor" stroke="black" stroke-width="1"/>
                <!-- Mast -->
                <line x1="15" y1="10" x2="15" y2="5" stroke="currentColor" stroke-width="2"/>
                <!-- Direction indicator -->
                <polygon points="15,5 12,2 18,2" fill="currentColor" stroke="black" stroke-width="1"/>
            </svg>
        `;
    }

    /**
     * Create vehicle symbol
     */
    createVehicleSymbol() {
        return `
            <svg width="30" height="30" viewBox="0 0 30 30" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <filter id="vehicleGlow">
                        <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
                        <feMerge>
                            <feMergeNode in="coloredBlur"/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                </defs>
                <!-- Main body -->
                <rect x="7" y="10" width="16" height="10" fill="currentColor" stroke="black" stroke-width="1"/>
                <!-- Wheels -->
                <circle cx="10" cy="22" r="3" fill="currentColor" stroke="black" stroke-width="1"/>
                <circle cx="20" cy="22" r="3" fill="currentColor" stroke="black" stroke-width="1"/>
                <!-- Turret/cab -->
                <rect x="12" y="6" width="6" height="6" fill="currentColor" stroke="black" stroke-width="1"/>
                <!-- Direction indicator -->
                <polygon points="15,6 12,2 18,2" fill="currentColor" stroke="black" stroke-width="1"/>
            </svg>
        `;
    }

    /**
     * Create radar target symbol
     */
    createRadarSymbol() {
        return `
            <svg width="30" height="30" viewBox="0 0 30 30" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <filter id="radarGlow">
                        <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
                        <feMerge>
                            <feMergeNode in="coloredBlur"/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                </defs>
                <!-- Center dot -->
                <circle cx="15" cy="15" r="3" fill="currentColor" stroke="black" stroke-width="1"/>
                <!-- Radar sweep lines -->
                <line x1="15" y1="3" x2="15" y2="12" stroke="currentColor" stroke-width="2"/>
                <line x1="15" y1="18" x2="15" y2="27" stroke="currentColor" stroke-width="2"/>
                <line x1="3" y1="15" x2="12" y2="15" stroke="currentColor" stroke-width="2"/>
                <line x1="18" y1="15" x2="27" y2="15" stroke="currentColor" stroke-width="2"/>
                <!-- Corner indicators -->
                <line x1="6" y1="6" x2="10" y2="10" stroke="currentColor" stroke-width="1"/>
                <line x1="24" y1="6" x2="20" y2="10" stroke="currentColor" stroke-width="1"/>
                <line x1="6" y1="24" x2="10" y2="20" stroke="currentColor" stroke-width="1"/>
                <line x1="24" y1="24" x2="20" y2="20" stroke="currentColor" stroke-width="1"/>
            </svg>
        `;
    }

    /**
     * Create multilateration symbol
     */
    createMultilaterationSymbol() {
        return `
            <svg width="30" height="30" viewBox="0 0 30 30" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <filter id="mlatGlow">
                        <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
                        <feMerge>
                            <feMergeNode in="coloredBlur"/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                </defs>
                <!-- Center target -->
                <circle cx="15" cy="15" r="4" fill="none" stroke="currentColor" stroke-width="2"/>
                <!-- Triangulation points -->
                <circle cx="8" cy="8" r="2" fill="currentColor" stroke="black" stroke-width="1"/>
                <circle cx="22" cy="8" r="2" fill="currentColor" stroke="black" stroke-width="1"/>
                <circle cx="15" cy="22" r="2" fill="currentColor" stroke="black" stroke-width="1"/>
                <!-- Connection lines -->
                <line x1="8" y1="8" x2="15" y2="15" stroke="currentColor" stroke-width="1" stroke-dasharray="2,2"/>
                <line x1="22" y1="8" x2="15" y2="15" stroke="currentColor" stroke-width="1" stroke-dasharray="2,2"/>
                <line x1="15" y1="22" x2="15" y2="15" stroke="currentColor" stroke-width="1" stroke-dasharray="2,2"/>
            </svg>
        `;
    }

    /**
     * Create unknown symbol
     */
    createUnknownSymbol() {
        return `
            <svg width="30" height="30" viewBox="0 0 30 30" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <filter id="unknownGlow">
                        <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
                        <feMerge>
                            <feMergeNode in="coloredBlur"/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                </defs>
                <!-- Diamond shape for unknown -->
                <polygon points="15,5 25,15 15,25 5,15" fill="currentColor" stroke="black" stroke-width="2"/>
                <!-- Question mark -->
                <text x="15" y="20" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="black">?</text>
            </svg>
        `;
    }

    /**
     * Modify symbol based on affiliation
     */
    modifySymbolForAffiliation(svg, affiliation) {
        // For now, just return the original SVG
        // In a full implementation, this would modify the symbol shape based on affiliation
        return svg;
    }

    /**
     * Create HTML marker for Leaflet
     */
    createLeafletMarker(track, affiliation = 'Unknown') {
        const symbol = this.getSymbol(track.track_type || track.type, affiliation);
        
        return `
            <div class="mil-std-marker" style="color: ${symbol.color}; width: ${symbol.size}px; height: ${symbol.size}px; position: relative;">
                ${symbol.svg}
                <div style="position: absolute; top: ${symbol.size}px; left: 50%; transform: translateX(-50%); 
                           font-size: 10px; font-weight: bold; white-space: nowrap; background: rgba(0,0,0,0.7); 
                           color: white; padding: 1px 4px; border-radius: 3px;">
                    ${track.track_id}
                </div>
            </div>
        `;
    }

    /**
     * Get Cesium color for symbol
     */
    getCesiumColor(trackType, affiliation = 'Unknown') {
        const color = this.getAffiliationColor(affiliation);
        return Cesium.Color.fromCssColorString(color);
    }

    /**
     * Create billboard for Cesium
     */
    createCesiumBillboard(track, affiliation = 'Unknown') {
        const symbol = this.getSymbol(track.track_type || track.type, affiliation);
        
        // Create a canvas with the symbol
        const canvas = document.createElement('canvas');
        canvas.width = symbol.size;
        canvas.height = symbol.size;
        const ctx = canvas.getContext('2d');
        
        // Set the color
        ctx.fillStyle = symbol.color;
        ctx.strokeStyle = '#000000';
        
        // Draw the symbol (simplified version for canvas)
        this.drawSymbolOnCanvas(ctx, symbol, symbol.size);
        
        return canvas;
    }

    /**
     * Draw symbol on canvas for Cesium
     */
    drawSymbolOnCanvas(ctx, symbol, size) {
        const centerX = size / 2;
        const centerY = size / 2;
        
        // Basic shape drawing based on symbol type
        ctx.lineWidth = 2;
        
        switch (symbol.subcategory) {
            case 'MF': // Aircraft
                // Simple aircraft shape
                ctx.beginPath();
                ctx.moveTo(centerX, centerY - 10);
                ctx.lineTo(centerX - 8, centerY + 5);
                ctx.lineTo(centerX + 8, centerY + 5);
                ctx.closePath();
                ctx.fill();
                ctx.stroke();
                break;
                
            case 'MH': // Helicopter
                // Simple helicopter shape
                ctx.fillRect(centerX - 8, centerY - 4, 16, 8);
                ctx.strokeRect(centerX - 8, centerY - 4, 16, 8);
                // Rotor
                ctx.beginPath();
                ctx.moveTo(centerX - 10, centerY);
                ctx.lineTo(centerX + 10, centerY);
                ctx.stroke();
                break;
                
            case 'CL': // Vessel
                // Simple vessel shape
                ctx.beginPath();
                ctx.moveTo(centerX - 10, centerY + 5);
                ctx.lineTo(centerX + 10, centerY + 5);
                ctx.lineTo(centerX + 8, centerY - 5);
                ctx.lineTo(centerX - 8, centerY - 5);
                ctx.closePath();
                ctx.fill();
                ctx.stroke();
                break;
                
            case 'UC': // Vehicle
                // Simple vehicle shape
                ctx.fillRect(centerX - 8, centerY - 4, 16, 8);
                ctx.strokeRect(centerX - 8, centerY - 4, 16, 8);
                break;
                
            default: // Unknown
                // Diamond shape
                ctx.beginPath();
                ctx.moveTo(centerX, centerY - 10);
                ctx.lineTo(centerX + 10, centerY);
                ctx.lineTo(centerX, centerY + 10);
                ctx.lineTo(centerX - 10, centerY);
                ctx.closePath();
                ctx.fill();
                ctx.stroke();
                break;
        }
    }
}

// Create global instance
window.milStd2525 = new MilStd2525SymbolSystem();
