// WebSocket management for real-time updates
class WebSocketManager {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.isConnected = false;
        this.lastErrorTime = 0; // For throttling error messages
        
        this.init();
    }
    
    init() {
        this.connect();
        this.setupEventHandlers();
    }
    
    connect() {
        try {
            this.socket = io();
            
            this.socket.on('connect', () => {
                console.log('Connected to surveillance system');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus(true);
            });
            
            this.socket.on('disconnect', () => {
                console.log('Disconnected from surveillance system');
                this.isConnected = false;
                this.updateConnectionStatus(false);
                this.attemptReconnect();
            });
            
            this.socket.on('connect_error', (error) => {
                // Throttle error messages to prevent spam
                if (!this.lastErrorTime || Date.now() - this.lastErrorTime > 10000) {
                    console.error('Connection error:', error);
                    this.lastErrorTime = Date.now();
                }
                this.updateConnectionStatus(false);
                this.attemptReconnect();
            });
            
            this.socket.on('track_update', (tracks) => {
                this.handleTrackUpdate(tracks);
            });
            
            this.socket.on('event_update', (event) => {
                this.handleEventUpdate(event);
            });
            
            this.socket.on('status', (data) => {
                console.log('Status update:', data.msg);
            });
            
        } catch (error) {
            console.error('Error initializing WebSocket:', error);
        }
    }
    
    setupEventHandlers() {
        // Request initial track data when connected
        document.addEventListener('DOMContentLoaded', () => {
            if (this.isConnected) {
                this.requestTrackUpdate();
            }
        });
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            // Only log once when max attempts reached, don't spam console
            if (this.reconnectAttempts === this.maxReconnectAttempts) {
                console.error('Max reconnection attempts reached');
            }
            return;
        }
        
        this.reconnectAttempts++;
        // Reduce console spam
        if (this.reconnectAttempts <= 2) {
            console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        }
        
        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay * Math.min(this.reconnectAttempts, 3)); // Cap delay
    }
    
    requestTrackUpdate() {
        if (this.socket && this.isConnected) {
            this.socket.emit('request_track_update');
        }
    }
    
    handleTrackUpdate(tracks) {
        try {
            // Update dashboard if available
            if (window.dashboard) {
                window.dashboard.onTrackUpdate(tracks);
            }
            
            // Update map if available
            if (window.mapManager) {
                window.mapManager.updateTracks(tracks);
            }
            
            console.log(`Updated ${tracks.length} tracks`);
        } catch (error) {
            console.error('Error handling track update:', error);
        }
    }
    
    handleEventUpdate(event) {
        try {
            // Add event to dashboard events if available
            if (window.dashboard && window.dashboard.events) {
                window.dashboard.events.unshift(event);
                
                // Keep only the latest 100 events in memory
                if (window.dashboard.events.length > 100) {
                    window.dashboard.events = window.dashboard.events.slice(0, 100);
                }
                
                // Update events display if currently viewing events
                const activeTab = document.querySelector('.nav-link.active');
                if (activeTab && activeTab.getAttribute('data-bs-target') === '#event-monitor') {
                    window.dashboard.updateEventsDisplay();
                }
            }
            
            console.log('New event received:', event);
        } catch (error) {
            console.error('Error handling event update:', error);
        }
    }
    
    updateConnectionStatus(connected) {
        // Update connection indicator in the UI
        let indicator = document.getElementById('connection-indicator');
        
        if (!indicator) {
            // Create connection indicator if it doesn't exist
            indicator = document.createElement('div');
            indicator.id = 'connection-indicator';
            indicator.style.cssText = `
                position: fixed;
                top: 10px;
                left: 50%;
                transform: translateX(-50%);
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 0.85rem;
                font-weight: 600;
                z-index: 9999;
                transition: all 0.3s ease;
            `;
            document.body.appendChild(indicator);
        }
        
        // Hide connection status entirely to prevent red popup spam
        indicator.style.display = 'none';
    }
    
    // Public methods for external use
    emit(event, data) {
        if (this.socket && this.isConnected) {
            this.socket.emit(event, data);
        } else {
            console.warn('Cannot emit event: WebSocket not connected');
        }
    }
    
    isSocketConnected() {
        return this.isConnected;
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
        }
    }
    
    // Send message to other connected clients (for future messenger functionality)
    sendMessage(message, recipient = 'all') {
        this.emit('send_message', {
            message: message,
            recipient: recipient,
            timestamp: new Date().toISOString()
        });
    }
    
    // Request specific track details
    requestTrackDetails(trackId) {
        this.emit('request_track_details', { track_id: trackId });
    }
    
    // Send alert/notification to other clients
    sendAlert(alertData) {
        this.emit('send_alert', {
            ...alertData,
            timestamp: new Date().toISOString()
        });
    }
}

// Initialize WebSocket manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.wsManager = new WebSocketManager();
    
    // Periodically request updates if live demo is active
    setInterval(() => {
        if (window.dashboard && window.dashboard.isLiveDemo && window.wsManager.isSocketConnected()) {
            window.wsManager.requestTrackUpdate();
        }
    }, 5000); // Request updates every 5 seconds during live demo
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.wsManager) {
        window.wsManager.disconnect();
    }
});
