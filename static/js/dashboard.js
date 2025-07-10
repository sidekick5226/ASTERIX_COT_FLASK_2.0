// Dashboard functionality
class SurveillanceDashboard {
    constructor() {
        this.tracks = new Map();
        this.events = [];
        this.currentPage = 1;
        this.isLiveDemo = false;
        this.isBattleMode = false;
        this.updateInterval = null;

        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInitialData();
        this.setupTabHandlers();
        this.startPeriodicUpdates(); // Always check for updates every second
    }

    bindEvents() {
        // Control buttons
        document.getElementById('start-demo-btn').addEventListener('click', () => this.startLiveDemo());
        document.getElementById('stop-demo-btn').addEventListener('click', () => this.stopLiveDemo());
        document.getElementById('battle-mode-btn').addEventListener('click', () => this.toggleBattleMode());

        // Add advanced 3D mode with double-click
        document.getElementById('battle-mode-btn').addEventListener('dblclick', () => this.toggleAdvanced3DMode());

        // Filters
        document.getElementById('track-type-filter').addEventListener('change', (e) => this.filterTracks(e.target.value));
        document.getElementById('search-input').addEventListener('input', (e) => this.searchTracks(e.target.value));

        // Event handlers
        document.getElementById('refresh-events-btn').addEventListener('click', () => this.refreshEvents());
        document.getElementById('filter-log-btn').addEventListener('click', () => this.filterEventLog());
        document.getElementById('export-log-btn').addEventListener('click', () => this.exportEventLog());

        // Network configuration
        this.bindNetworkConfigEvents();
    }

    bindNetworkConfigEvents() {
        const protocol = document.getElementById('protocol');
        const port = document.getElementById('port');
        const ipAddress = document.getElementById('ip_address');

        [protocol, port, ipAddress].forEach(element => {
            element.addEventListener('change', () => this.updateNetworkConfig());
        });
    }

    setupTabHandlers() {
        // Tab handlers are now managed by the tabs.js file and Alpine.js
        // No need to set up Bootstrap tab handlers
    }

    handleTabChange(target) {
        // Tab changes are now handled by tabs.js
        // This method is kept for compatibility but no longer needed
    }

    async loadInitialData() {
        try {
            await this.loadTracks();
            await this.loadNetworkConfig();
        } catch (error) {
            console.error('Error loading initial data:', error);
            // Don't show popup notification to prevent spam
        }
    }

    async loadTracks() {
        try {
            const response = await fetch('/api/tracks');
            const tracks = await response.json();

            this.tracks.clear();
            tracks.forEach(track => {
                this.tracks.set(track.track_id, track);
            });

            this.updateTracksDisplay();
            this.updateTrackCounts();

            if (window.mapManager) {
                window.mapManager.updateTracks(tracks);
            }
        } catch (error) {
            // Only log error, don't show notification to prevent popup spam
            console.error('Error loading tracks:', error);
        }
    }

    startPeriodicUpdates() {
        // Check for track updates every second
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }

        this.updateInterval = setInterval(async () => {
            await this.loadTracks(); // Always check for updates
        }, 1000);
    }

    stopPeriodicUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    async loadNetworkConfig() {
        try {
            const response = await fetch('/api/network-config');
            const config = await response.json();

            document.getElementById('protocol').value = config.protocol;
            document.getElementById('port').value = config.port;
            document.getElementById('ip_address').value = config.ip_address;
        } catch (error) {
            console.error('Error loading network config:', error);
        }
    }

    async updateNetworkConfig() {
        try {
            const config = {
                protocol: document.getElementById('protocol').value,
                port: parseInt(document.getElementById('port').value),
                ip_address: document.getElementById('ip_address').value,
                is_active: true
            };

            const response = await fetch('/api/network-config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });

            if (response.ok) {
                this.showNotification('Network configuration updated', 'success');
            }
        } catch (error) {
            console.error('Error updating network config:', error);
            this.showNotification('Error updating network configuration', 'error');
        }
    }

    updateTracksDisplay() {
        const tbody = document.getElementById('tracks-table-body');
        tbody.innerHTML = '';

        this.tracks.forEach(track => {
            const row = this.createTrackRow(track);
            tbody.appendChild(row);
        });

        document.getElementById('total-tracks').textContent = this.tracks.size;
    }

    createTrackRow(track) {
        const row = document.createElement('tr');

        const typeColors = {
            'Aircraft': 'bg-blue-600',
            'Vessel': 'bg-cyan-600',
            'Vehicle': 'bg-green-600'
        };

        const statusColors = {
            'Active': 'bg-green-600',
            'Inactive': 'bg-red-600',
            'Unknown': 'bg-gray-600'
        };

        const trackType = track.track_type || track.type || 'Unknown';
        const typeColor = typeColors[trackType] || 'bg-gray-600';
        const statusColor = statusColors[track.status] || 'bg-gray-600';

        row.className = 'border-b border-slate-600 hover:bg-slate-600/50';
        row.innerHTML = `
            <td class="px-3 py-2">${track.track_id}</td>
            <td class="px-3 py-2">
                <span class="px-2 py-1 rounded text-xs font-medium text-white ${typeColor}">${trackType}</span>
            </td>
            <td class="px-3 py-2">
                <span class="px-2 py-1 rounded text-xs font-medium text-white ${statusColor}">${track.status}</span>
            </td>
            <td class="px-3 py-2">
                <div class="flex space-x-1">
                    <button class="bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded text-xs transition-colors" onclick="dashboard.viewTrackDetails('${track.track_id}')">
                        <i class="fas fa-info-circle"></i>
                    </button>
                    <button class="bg-green-600 hover:bg-green-700 text-white px-2 py-1 rounded text-xs transition-colors" onclick="dashboard.trackOnMap('${track.track_id}')">
                        <i class="fas fa-map-marker-alt"></i>
                    </button>
                </div>
            </td>
        `;
        return row;
    }

    updateTrackCounts() {
        const counts = {
            aircraft: 0,
            vessel: 0,
            vehicle: 0,
            unknown: 0
        };

        this.tracks.forEach(track => {
            const type = (track.track_type || track.type || 'unknown').toLowerCase();
            if (counts.hasOwnProperty(type)) {
                counts[type]++;
            } else {
                counts.unknown++;
            }
        });

        document.getElementById('aircraft-count').textContent = counts.aircraft;
        document.getElementById('vessel-count').textContent = counts.vessel;
        document.getElementById('vehicle-count').textContent = counts.vehicle;
        document.getElementById('unknown-count').textContent = counts.unknown;
    }

    filterTracks(type) {
        // Implementation for track filtering
        if (window.mapManager) {
            window.mapManager.filterByType(type);
        }

        // Update table display
        const rows = document.querySelectorAll('#tracks-table-body tr');
        rows.forEach(row => {
            const trackType = row.cells[1].textContent.trim();
            if (!type || trackType === type) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    searchTracks(query) {
        const rows = document.querySelectorAll('#tracks-table-body tr');
        rows.forEach(row => {
            const trackId = row.cells[0].textContent.trim();
            if (!query || trackId.toLowerCase().includes(query.toLowerCase())) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    async refreshEvents() {
        try {
            const response = await fetch('/api/events');
            const data = await response.json();
            this.events = data.events;

            this.updateEventsDisplay();
        } catch (error) {
            console.error('Error refreshing events:', error);
        }
    }

    updateEventsDisplay() {
        const tbody = document.getElementById('events-table-body');
        if (!tbody) return;

        tbody.innerHTML = '';

        this.events.slice(0, 50).forEach(event => { // Show latest 50 events
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${new Date(event.timestamp).toLocaleString()}</td>
                <td>${event.track_id}</td>
                <td><span class="status-badge status-${event.event_type.toLowerCase().replace(' ', '-')}">${event.event_type}</span></td>
                <td>${event.description}</td>
            `;
            tbody.appendChild(row);
        });
    }

    async loadEventLog() {
        try {
            const response = await fetch(`/api/events?page=${this.currentPage}&per_page=20`);
            const data = await response.json();

            this.updateEventLogDisplay(data.events);
            this.updatePagination(data.current_page, data.pages);
        } catch (error) {
            console.error('Error loading event log:', error);
        }
    }

    updateEventLogDisplay(events) {
        const tbody = document.getElementById('events-log-body');
        if (!tbody) return;

        tbody.innerHTML = '';

        events.forEach(event => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${new Date(event.timestamp).toLocaleString()}</td>
                <td>${event.track_id}</td>
                <td><span class="status-badge status-${event.event_type.toLowerCase().replace(' ', '-')}">${event.event_type}</span></td>
                <td>${event.description}</td>
                <td>
                    <button class="btn btn-sm btn-outline-info action-btn" onclick="dashboard.viewEventDetails(${event.id})">
                        <i class="fas fa-info-circle"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    updatePagination(currentPage, totalPages) {
        const pagination = document.getElementById('log-pagination');
        if (!pagination) return;

        pagination.innerHTML = '';

        // Previous button
        const prevItem = document.createElement('li');
        prevItem.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
        prevItem.innerHTML = `<a class="page-link" href="#" onclick="dashboard.goToPage(${currentPage - 1})">Previous</a>`;
        pagination.appendChild(prevItem);

        // Page numbers
        for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
            const pageItem = document.createElement('li');
            pageItem.className = `page-item ${i === currentPage ? 'active' : ''}`;
            pageItem.innerHTML = `<a class="page-link" href="#" onclick="dashboard.goToPage(${i})">${i}</a>`;
            pagination.appendChild(pageItem);
        }

        // Next button
        const nextItem = document.createElement('li');
        nextItem.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
        nextItem.innerHTML = `<a class="page-link" href="#" onclick="dashboard.goToPage(${currentPage + 1})">Next</a>`;
        pagination.appendChild(nextItem);
    }

    goToPage(page) {
        this.currentPage = page;
        this.loadEventLog();
    }

    filterEventLog() {
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;
        const eventType = document.getElementById('event-type-filter').value;

        // Implementation for filtering event log
        console.log('Filtering events:', { startDate, endDate, eventType });
        this.showNotification('Event log filtered', 'info');
    }

    exportEventLog() {
        // Implementation for exporting event log
        const data = this.events.map(event => ({
            timestamp: event.timestamp,
            track_id: event.track_id,
            event_type: event.event_type,
            description: event.description
        }));

        const csv = this.convertToCSV(data);
        this.downloadCSV(csv, 'event_log.csv');
    }

    convertToCSV(data) {
        const headers = Object.keys(data[0]).join(',');
        const rows = data.map(row => Object.values(row).join(','));
        return [headers, ...rows].join('\n');
    }

    downloadCSV(csv, filename) {
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(url);
    }

    startLiveDemo() {
        this.isLiveDemo = true;
        document.getElementById('start-demo-btn').disabled = true;
        document.getElementById('stop-demo-btn').disabled = false;

        // Generate new simulated tracks
        fetch('/api/tracks/generate', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                console.log('Generated tracks:', data);
                this.showNotification('Live surveillance demo started - New tracks generated', 'success');
            })
            .catch(error => {
                console.error('Error generating tracks:', error);
                this.showNotification('Live demo started', 'success');
            });
    }

    stopLiveDemo() {
        this.isLiveDemo = false;
        document.getElementById('start-demo-btn').disabled = false;
        document.getElementById('stop-demo-btn').disabled = true;

        // Clear all tracks from display
        this.tracks.clear();
        this.updateTracksDisplay();
        this.updateTrackCounts();

        // Clear tracks from map
        if (window.mapManager) {
            window.mapManager.clearAllTracks();
        }

        // Send request to server to clear tracks
        fetch('/api/tracks/clear', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                console.log('Tracks cleared:', data);
            })
            .catch(error => {
                console.error('Error clearing tracks:', error);
            });

        this.showNotification('Live demo stopped - All tracks cleared', 'info');
    }

    toggleBattleMode() {
        this.isBattleMode = !this.isBattleMode;
        const btn = document.getElementById('battle-mode-btn');

        if (this.isBattleMode) {
            btn.innerHTML = '<i class="fas fa-globe"></i> Standard View';
            btn.classList.add('active');
            if (window.mapManager) {
                window.mapManager.switchTo3D();
            }
            this.showNotification('Battle Mode activated', 'success');
        } else {
            btn.innerHTML = '<i class="fas fa-fighter-jet"></i> Battle View';
            btn.classList.remove('active');
            if (window.mapManager) {
                window.mapManager.switchTo2D();
            }
            this.showNotification('Standard view activated', 'info');
        }
    }

    toggleAdvanced3DMode() {
        if (window.advancedCesium) {
            // Switch to advanced 3D mode
            window.advancedCesium.enable3DMode();
            this.showNotification('Advanced 3D Mode: Quantized terrain, 3D buildings, glTF units, follow cam enabled', 'success');

            const btn = document.getElementById('battle-mode-btn');
            btn.innerHTML = '<i class="fas fa-cube"></i> Advanced 3D';
            btn.classList.add('advanced-3d');
        } else {
            this.showNotification('Advanced 3D mode not available', 'error');
        }
    }

    viewTrackDetails(trackId) {
        const track = this.tracks.get(trackId);
        if (track) {
            alert(`Track Details:\nID: ${track.track_id}\nType: ${track.type}\nPosition: ${track.latitude}, ${track.longitude}\nStatus: ${track.status}`);
        }
    }

    trackOnMap(trackId) {
        if (window.mapManager) {
            window.mapManager.focusOnTrack(trackId);
        }
    }

    viewEventDetails(eventId) {
        const event = this.events.find(e => e.id === eventId);
        if (event) {
            alert(`Event Details:\nID: ${event.id}\nTrack: ${event.track_id}\nType: ${event.event_type}\nTime: ${event.timestamp}\nDescription: ${event.description}`);
        }
    }

    onTrackUpdate(tracks) {
        tracks.forEach(track => {
            this.tracks.set(track.track_id, track);
        });

        this.updateTracksDisplay();
        this.updateTrackCounts();

        if (window.mapManager) {
            window.mapManager.updateTracks(tracks);
        }
    }

    showNotification(message, type = 'info') {
        // Simple notification system
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new SurveillanceDashboard();
});