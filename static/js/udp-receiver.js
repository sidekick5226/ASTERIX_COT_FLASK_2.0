/**
 * UDP ASTERIX Receiver Management
 * Handles starting, stopping, and monitoring UDP receiver for ASTERIX CAT-48 data
 */

class UDPReceiverManager {
    constructor() {
        this.status = {
            running: false,
            host: '0.0.0.0',
            port: 8080,
            statistics: null
        };
        
        this.updateInterval = null;
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.updateStatus();
        this.startStatusPolling();
    }
    
    setupEventListeners() {
        // Update configuration when network settings change
        document.getElementById('port').addEventListener('change', () => {
            this.updateConfiguration();
        });
        
        document.getElementById('ip_address').addEventListener('change', () => {
            this.updateConfiguration();
        });
    }
    
    async startReceiver() {
        try {
            const host = document.getElementById('ip_address').value || '0.0.0.0';
            const port = parseInt(document.getElementById('port').value) || 8080;
            
            this.showLoading('Starting UDP receiver...');
            
            const response = await fetch('/api/udp/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    host: host,
                    port: port
                })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.showNotification(result.message, 'success');
                this.updateStatus();
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error starting UDP receiver: ' + error.message, 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    async stopReceiver() {
        try {
            this.showLoading('Stopping UDP receiver...');
            
            const response = await fetch('/api/udp/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.showNotification(result.message, 'success');
                this.updateStatus();
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error stopping UDP receiver: ' + error.message, 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    async updateStatus() {
        try {
            const response = await fetch('/api/udp/status');
            const result = await response.json();
            
            if (result.status === 'success') {
                this.status = result.data;
                this.updateUI();
            }
        } catch (error) {
            console.error('Error updating UDP receiver status:', error);
        }
    }
    
    updateUI() {
        // UDP receiver runs automatically in background
        // No UI elements to update since receiver section was removed
        console.log(`UDP Receiver Status: ${this.status.running ? 'Running' : 'Stopped'} on ${this.status.host}:${this.status.port}`);
        
        // Log statistics for debugging if needed
        if (this.status.statistics) {
            console.log('UDP Stats:', {
                messages: this.status.statistics.messages_received || 0,
                tracks: this.status.statistics.tracks_updated || 0,
                errors: this.status.statistics.errors || 0
            });
        }
    }
    
    async updateConfiguration() {
        try {
            const host = document.getElementById('ip_address').value || '0.0.0.0';
            const port = parseInt(document.getElementById('port').value) || 8080;
            
            const response = await fetch('/api/udp/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    host: host,
                    port: port
                })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                console.log('UDP configuration updated');
            } else {
                console.error('Error updating UDP configuration:', result.message);
            }
        } catch (error) {
            console.error('Error updating UDP configuration:', error);
        }
    }
    
    startStatusPolling() {
        // Poll status every 2 seconds
        this.updateInterval = setInterval(() => {
            this.updateStatus();
        }, 2000);
    }
    
    stopStatusPolling() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    showLoading(message) {
        // Create or update loading indicator
        let loadingEl = document.getElementById('udp-loading');
        if (!loadingEl) {
            loadingEl = document.createElement('div');
            loadingEl.id = 'udp-loading';
            loadingEl.className = 'text-xs text-blue-400 mt-2';
            document.getElementById('udp-stats').appendChild(loadingEl);
        }
        loadingEl.innerHTML = `<i class="fas fa-spinner fa-spin mr-1"></i> ${message}`;
    }
    
    hideLoading() {
        const loadingEl = document.getElementById('udp-loading');
        if (loadingEl) {
            loadingEl.remove();
        }
    }
    
    showNotification(message, type = 'info') {
        // Use existing notification system if available
        if (window.dashboard && window.dashboard.showNotification) {
            window.dashboard.showNotification(message, type);
        } else {
            // Fallback to console
            console.log(`[UDP Receiver] ${type.toUpperCase()}: ${message}`);
        }
    }
    
    // Public method to get current status
    getStatus() {
        return this.status;
    }
    
    // Cleanup method
    destroy() {
        this.stopStatusPolling();
    }
}

// Initialize UDP receiver manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.udpReceiverManager = new UDPReceiverManager();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.udpReceiverManager) {
        window.udpReceiverManager.destroy();
    }
});
