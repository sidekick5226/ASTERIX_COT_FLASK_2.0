// Dashboard functionality
class SurveillanceDashboard {
    constructor() {
        console.log('Dashboard constructor called');
        this.tracks = new Map();
        this.events = []; // Historical events for Event Log
        this.monitorEvents = []; // Real-time events for Event Monitor
        this.currentPage = 1;
        this.isLiveDemo = false;
        this.isBattleMode = false;
        this.updateInterval = null;
        this.monitorInterval = null; // For Event Monitor auto-refresh
        this.selectedTracks = new Set(); // For multi-track selection
        this.battleGroups = new Map(); // Battle Groups storage
        this.battleGroupCounter = 0; // Counter for naming battle groups
        this.isMultiSelecting = false; // Track if we're in multi-select mode
        console.log('Dashboard properties initialized');
        
        this.socket = io({
            timeout: 120000,
            reconnection: true,
            reconnectionDelay: 2000,
            reconnectionAttempts: 5,
            transports: ['polling', 'websocket']
        }); // Initialize Socket.IO connection

        this.setupSocketHandlers();
        this.init();
    }

    init() {
        this.bindEvents();
        this.bindMultiSelectEvents(); // Bind shift+click functionality
        this.bindBattleGroupEvents(); // Bind battle group dialog events
        this.loadInitialData();
        this.setupTabHandlers();
        this.startPeriodicUpdates(); // Always check for updates every second
        console.log('Dashboard initialized with multi-select functionality');
    }

    setupSocketHandlers() {
        console.log('Setting up socket handlers...');

        // Handle real-time track updates
        this.socket.on('track_update', (tracks) => {
            console.log('Received track_update:', tracks.length, 'tracks');
            this.onTrackUpdate(tracks);
        });

        // Handle connection status
        this.socket.on('status', (data) => {
            console.log('Status update:', data.msg);
            this.showNotification(data.msg, 'info');
        });

        this.socket.on('connect', () => {
            console.log('Connected to surveillance system');
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from surveillance system');
        });

        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
        });
    }

    bindEvents() {
        // Control buttons
        document.getElementById('start-demo-btn').addEventListener('click', () => this.startLiveDemo());
        document.getElementById('stop-demo-btn').addEventListener('click', () => this.stopLiveDemo());
        document.getElementById('battle-mode-btn').addEventListener('click', () => this.toggleBattleMode());

        // Add test dialog button for debugging
        document.getElementById('test-dialog-btn').addEventListener('click', () => this.testBattleGroupDialog());

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
            // Only load network config on startup, not tracks
            await this.loadNetworkConfig();

            // Initialize empty tracks display
            this.tracks.clear();
            this.updateTracksDisplay();
        } catch (error) {
            console.error('Error loading initial data:', error);
            // Don't show popup notification to prevent spam
        }
    }

    async loadTracks() {
        try {
            const response = await fetch('/api/tracks', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                timeout: 3000 // 3 second timeout
            });

            if (!response.ok) {
                console.warn('Tracks API returned non-200 status:', response.status);
                return;
            }

            const tracks = await response.json();

            this.tracks.clear();
            tracks.forEach(track => {
                this.tracks.set(track.track_id, track);
            });

            this.updateTracksDisplay();

            if (window.mapManager) {
                window.mapManager.updateTracks(tracks);
            }
        } catch (error) {
            // Silently handle errors to avoid console spam
            if (error.name !== 'AbortError') {
                console.warn('Tracks temporarily unavailable');            }
        }
    }

    startPeriodicUpdates() {
        // Check for track updates every 1 second, monitor events every 1.5 seconds for faster refresh
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        if (this.monitorInterval) {
            clearInterval(this.monitorInterval);
        }

        // Track updates every 1 second for responsiveness
        this.updateInterval = setInterval(async () => {
            await this.loadTracks();
        }, 1000);

        // Monitor events every 1.5 seconds for faster real-time updates
        this.monitorInterval = setInterval(async () => {
            // Show brief visual feedback during auto-refresh
            this.showAutoRefreshIndicator();
            await this.loadMonitorEvents();
        }, 1500);

        console.log('Started periodic updates - Event Monitor will auto-refresh every 1.5 seconds');
    }

    stopPeriodicUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
        if (this.monitorInterval) {
            clearInterval(this.monitorInterval);
            this.monitorInterval = null;
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
        console.log(`Updated tracks display with ${this.tracks.size} tracks`);
    }

    createTrackRow(track) {
        const row = document.createElement('tr');

        const typeColors = {
            'Aircraft': 'bg-blue-600',
            'Vessel': 'bg-purple-600',
            'Vehicle': 'bg-yellow-600'
        };

        const statusColors = {
            'Active': 'bg-green-600',
            'Inactive': 'bg-red-600',
            'Unknown': 'bg-gray-600'
        };

        const trackType = track.track_type || track.type || 'Unknown';
        const typeColor = typeColors[trackType] || 'bg-gray-600';
        const statusColor = statusColors[track.status] || 'bg-gray-600';

        // Add selection state styling
        const isSelected = this.selectedTracks.has(track.track_id);
        const selectionClass = isSelected ? 'selected-track' : '';
        
        row.className = `border-b border-slate-600 hover:bg-slate-600/50 cursor-pointer ${selectionClass}`;
        row.dataset.trackId = track.track_id;
        
        // Add click event for multi-selection
        row.addEventListener('click', (e) => this.handleTrackRowClick(e, track.track_id));
        
        row.innerHTML = `
            <td class="px-3 py-2">
                ${isSelected ? '<i class="fas fa-check-circle text-orange-400 mr-2"></i>' : ''}
                ${track.track_id}
            </td>
            <td class="px-3 py-2">
                <span class="px-2 py-1 rounded text-xs font-medium text-white ${typeColor}">${trackType}</span>
            </td>
            <td class="px-3 py-2">
                <span class="px-2 py-1 rounded text-xs font-medium text-white ${statusColor}">${track.status}</span>
            </td>
            <td class="px-3 py-2">
                <div class="flex space-x-1">
                    <button class="bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded text-xs transition-colors" onclick="event.stopPropagation(); dashboard.viewTrackDetails('${track.track_id}')">
                        <i class="fas fa-info-circle"></i>
                    </button>
                    <button class="bg-green-600 hover:bg-green-700 text-white px-2 py-1 rounded text-xs transition-colors" onclick="event.stopPropagation(); dashboard.trackOnMap('${track.track_id}')">
                        <i class="fas fa-map-marker-alt"></i>
                    </button>
                </div>
            </td>
        `;
        return row;
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
            // Show manual refresh in progress
            const refreshBtn = document.getElementById('refresh-events-btn');
            const originalHTML = refreshBtn.innerHTML;
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Refreshing...';
            refreshBtn.disabled = true;

            // Refresh both monitor events and event log
            await this.loadMonitorEvents();
            await this.loadEventLog();

            this.showNotification('Events manually refreshed', 'success');

            // Restore button
            refreshBtn.innerHTML = originalHTML;
            refreshBtn.disabled = false;
        } catch (error) {
            console.error('Error refreshing events:', error);
            this.showNotification('Error refreshing events', 'error');
            
            // Restore button on error
            const refreshBtn = document.getElementById('refresh-events-btn');
            refreshBtn.innerHTML = '<i class="fas fa-sync mr-1"></i> Manual Refresh';
            refreshBtn.disabled = false;
        }
    }

    updateEventsDisplay() {
        const tbody = document.getElementById('events-table-body');
        if (!tbody) {
            console.log('events-table-body not found!');
            return;
        }

        console.log('Updating events display with', this.monitorEvents.length, 'monitor events');

        // Clear existing content
        tbody.innerHTML = '';

        if (this.monitorEvents.length === 0) {
            // Show placeholder message when no events
            const placeholderRow = document.createElement('tr');
            placeholderRow.innerHTML = `
                <td colspan="8" class="px-4 py-8 text-center text-slate-400">
                    <i class="fas fa-eye-slash text-2xl mb-2"></i><br>
                    No real-time events yet<br>
                    <small>Events will appear here when surveillance is active</small>
                </td>
            `;
            tbody.appendChild(placeholderRow);
            return;
        }

        // Show real-time monitor events (most recent first)
        const eventsToShow = this.monitorEvents.slice(-50).reverse();
        console.log('Displaying', eventsToShow.length, 'events');

        eventsToShow.forEach(event => {
            const row = document.createElement('tr');
            row.className = 'border-b border-slate-600 hover:bg-slate-600/50';

            const timestamp = event.timestamp ? new Date(event.timestamp).toLocaleString() : new Date().toLocaleString();

            // Track type color coding
            const typeColors = {
                'Aircraft': 'bg-blue-600 text-white',
                'Vessel': 'bg-purple-600 text-white',
                'Vehicle': 'bg-yellow-600 text-white'
            };
            const typeColor = typeColors[event.track_type] || 'bg-gray-600 text-white';

            row.innerHTML = `
                <td class="px-3 py-2 text-slate-300 text-xs">${timestamp}</td>
                <td class="px-3 py-2 text-blue-400 font-medium">${event.track_id}</td>
                <td class="px-3 py-2">
                    <span class="px-2 py-1 rounded text-xs font-medium ${event.is_realtime ? 'bg-green-600 text-white' : 'bg-blue-600 text-white'}">${event.event_type}</span>
                </td>
                <td class="px-3 py-2">
                    <span class="px-2 py-1 rounded text-xs font-medium ${typeColor}">${event.track_type || 'Unknown'}</span>
                </td>
                <td class="px-3 py-2 text-slate-300 font-mono text-xs">${event.latitude || 'N/A'}</td>
                <td class="px-3 py-2 text-slate-300 font-mono text-xs">${event.longitude || 'N/A'}</td>
                <td class="px-3 py-2 text-slate-300 text-right">${event.speed || 0}</td>
                <td class="px-3 py-2 text-slate-300 text-right">${event.altitude || 0}</td>
            `;
            tbody.appendChild(row);
        });

        console.log('Added', tbody.children.length, 'rows to events table');
    }

    async loadMonitorEvents() {
        try {
            const response = await fetch('/api/monitor-events', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                timeout: 2000 // Reduced timeout for faster response
            });

            if (!response.ok) {
                console.warn('Monitor events API returned non-200 status:', response.status);
                return;
            }

            const data = await response.json();

            if (data.status === 'success') {
                // Update monitor events with current real-time data
                const previousCount = this.monitorEvents.length;
                this.monitorEvents = data.events || [];

                // Update the Event Monitor display
                this.updateEventsDisplay();

                // Only log if there's a change to avoid console spam
                if (this.monitorEvents.length !== previousCount) {
                    console.log(`Monitor events updated: ${this.monitorEvents.length} events (was ${previousCount})`);
                }
            }
        } catch (error) {
            // Silently handle errors to avoid console spam during auto-refresh
            if (error.name !== 'AbortError') {
                console.warn('Monitor events temporarily unavailable');
            }
        }
    }

    onMonitorEvents(events) {
        // This method is kept for compatibility but no longer used
        // Monitor events are now loaded via polling
        console.log('Legacy monitor events handler called');
    }

    async loadEventLog() {
        try {
            console.log('Loading Event Log data...');
            const response = await fetch(`/api/events?page=${this.currentPage}&per_page=20`);
            const data = await response.json();

            console.log('Event Log data received:', data);
            this.updateEventLogDisplay(data.events);
            this.updatePagination(data.current_page, data.pages);
        } catch (error) {
            console.error('Error loading event log:', error);
        }
    }

    updateEventLogDisplay(events) {
        const tbody = document.getElementById('events-log-body');
        if (!tbody) {
            console.error('Event Log table body not found');
            return;
        }

        tbody.innerHTML = '';

        console.log('Displaying', events.length, 'events in Event Log');

        events.forEach(event => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="px-4 py-2">${new Date(event.timestamp).toLocaleString()}</td>
                <td class="px-4 py-2">${event.track_id}</td>
                <td class="px-4 py-2"><span class="px-2 py-1 rounded text-xs font-semibold bg-blue-100 text-blue-800">${event.event_type}</span></td>
                <td class="px-4 py-2">${event.description}</td>
                <td class="px-4 py-2">
                    <button class="bg-blue-500 hover:bg-blue-600 text-white px-2 py-1 rounded text-xs" onclick="dashboard.viewEventDetails(${event.id})">
                        <i class="fas fa-info-circle"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });

        console.log('Added', tbody.children.length, 'rows to Event Log table');
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
        console.log('Export button clicked');
        // Call the API to export the event log (without clearing)
        if (confirm('This will export all events to CSV. The log will remain in the system. Continue?')) {
            console.log('User confirmed export');
            fetch('/api/export-events', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                console.log('Export response:', data);
                if (data.status === 'success') {
                    this.showNotification(data.message, 'success');
                    // No need to refresh the event log since it wasn't cleared
                } else {
                    this.showNotification('Failed to export event log: ' + data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Export error:', error);
                this.showNotification('Error exporting event log', 'error');
            });
        } else {
            console.log('User cancelled export');
        }
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
        // Immediately update UI for responsiveness
        this.isLiveDemo = true;
        const startBtn = document.getElementById('start-demo-btn');
        const stopBtn = document.getElementById('stop-demo-btn');

        startBtn.disabled = true;
        stopBtn.disabled = false;
        startBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting...';

        // Start surveillance tracking
        fetch('/api/surveillance/start', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                console.log('Surveillance started:', data);
                startBtn.innerHTML = '<i class="fas fa-play"></i> Start Surveillance';
                this.showNotification('Surveillance started - Live tracking active', 'success');
            })
            .catch(error => {
                console.error('Error starting surveillance:', error);
                startBtn.innerHTML = '<i class="fas fa-play"></i> Start Surveillance';
                startBtn.disabled = false;
                stopBtn.disabled = true;
                this.isLiveDemo = false;
                this.showNotification('Error starting surveillance', 'error');
            });
    }

    stopLiveDemo() {
        // Immediately update UI for responsiveness
        const startBtn = document.getElementById('start-demo-btn');
        const stopBtn = document.getElementById('stop-demo-btn');

        this.isLiveDemo = false;
        startBtn.disabled = false;
        stopBtn.disabled = true;
        stopBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Stopping...';

        // Immediately clear UI for responsive feel
        this.tracks.clear();
        this.updateTracksDisplay();

        // Clear tracks from map immediately
        if (window.mapManager) {
            window.mapManager.clearAllTracks();
        }

        // Stop surveillance tracking
        fetch('/api/surveillance/stop', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                console.log('Surveillance stopped:', data);
                stopBtn.innerHTML = '<i class="fas fa-stop"></i> Stop & Clear';
                this.showNotification('Surveillance stopped - All tracks cleared', 'info');
            })
            .catch(error => {
                console.error('Error stopping surveillance:', error);
                stopBtn.innerHTML = '<i class="fas fa-stop"></i> Stop & Clear';
                this.showNotification('Error stopping surveillance', 'error');
            });
    }

    toggleBattleMode() {
        this.isBattleMode = !this.isBattleMode;
        const btn = document.getElementById('battle-mode-btn');
        const tracksPanel = document.getElementById('active-tracks-panel');
        const mapContainer = document.getElementById('map-container');
        const trackLegend = document.getElementById('track-legend');

        if (this.isBattleMode) {
            btn.innerHTML = '<i class="fas fa-globe"></i> Standard View';
            btn.classList.add('active');

            // Hide Active Tracks Panel and Track Legend for clean immersive view
            if (tracksPanel) {
                tracksPanel.classList.add('hidden');
            }
            if (trackLegend) {
                trackLegend.classList.add('hidden');
            }
            if (mapContainer) {
                mapContainer.classList.remove('flex-1');
                mapContainer.classList.add('w-full');
            }

            if (window.mapManager) {
                window.mapManager.switchTo3D();
            }
            this.showNotification('Battle Mode activated - Full screen 3D view', 'success');
        } else {
            btn.innerHTML = '<i class="fas fa-globe-americas mr-1"></i> Battle View';
            btn.classList.remove('active');

            // Show Active Tracks Panel and Track Legend for standard view
            if (tracksPanel) {
                tracksPanel.classList.remove('hidden');
            }
            if (trackLegend) {
                trackLegend.classList.remove('hidden');
            }
            if (mapContainer) {
                mapContainer.classList.remove('w-full');
                mapContainer.classList.add('flex-1');
            }

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

    getTrackTypeColor(type) {
        switch (type.toLowerCase()) {
            case 'aircraft': return '#3b82f6';
            case 'vessel': return '#9333ea';
            case 'vehicle': return '#d97706';
            default: return '#6b7280';
        }
    }
    
    // Multi-track selection methods
    bindMultiSelectEvents() {
        console.log('Binding multi-select events...');
        
        // Track shift key state
        document.addEventListener('keydown', (e) => {
            // Don't activate multi-select mode if dialog is open or if user is typing in an input field
            if (e.key === 'Shift' && !this.isDialogOpen() && !this.isTypingInInput(e.target)) {
                console.log('Shift key pressed - entering multi-select mode');
                this.isMultiSelecting = true;
                document.body.classList.add('multi-select-mode');
            }
        });

        document.addEventListener('keyup', (e) => {
            // Only process shift release if we were in multi-select mode
            if (e.key === 'Shift' && this.isMultiSelecting) {
                console.log('Shift key released - exiting multi-select mode');
                this.isMultiSelecting = false;
                document.body.classList.remove('multi-select-mode');
                
                // Show battle group dialog if we have multiple tracks selected
                if (this.selectedTracks.size > 1) {
                    console.log(`Showing battle group dialog for ${this.selectedTracks.size} selected tracks`);
                    console.log('Selected tracks:', Array.from(this.selectedTracks));
                    
                    // Add a small delay to ensure the UI is ready
                    setTimeout(() => {
                        this.showBattleGroupDialog();
                    }, 100);
                } else {
                    console.log(`Only ${this.selectedTracks.size} tracks selected - dialog not shown`);
                }
            }
        });
    }

    // Helper method to check if any dialog is open
    isDialogOpen() {
        const dialog = document.getElementById('battle-group-dialog');
        return dialog && !dialog.classList.contains('hidden');
    }

    // Helper method to check if user is typing in an input field
    isTypingInInput(target) {
        if (!target) return false;
        
        const tagName = target.tagName.toLowerCase();
        const inputTypes = ['input', 'textarea', 'select'];
        
        return inputTypes.includes(tagName) || 
               target.contentEditable === 'true' ||
               target.closest('input, textarea, select') !== null;
    }

    handleTrackRowClick(event, trackId) {
        console.log(`Track row clicked: ${trackId}, multi-selecting: ${this.isMultiSelecting}`);
        
        if (this.isMultiSelecting) {
            // Multi-select mode
            if (this.selectedTracks.has(trackId)) {
                this.selectedTracks.delete(trackId);
                console.log(`Deselected track ${trackId}, total selected: ${this.selectedTracks.size}`);
            } else {
                this.selectedTracks.add(trackId);
                console.log(`Selected track ${trackId}, total selected: ${this.selectedTracks.size}`);
            }
            
            // Log current selection state
            console.log('Current selected tracks:', Array.from(this.selectedTracks));
            
            // Update the track display to show selection
            this.updateTracksDisplay();
            
            // Update map highlighting if in 3D mode
            if (window.cesiumAdvanced && window.cesiumAdvanced.isActive()) {
                window.cesiumAdvanced.highlightSelectedTracks(Array.from(this.selectedTracks));
            }
        } else {
            // Single track selection - clear previous selections
            this.selectedTracks.clear();
            this.selectedTracks.add(trackId);
            this.updateTracksDisplay();
            
            // Focus on single track
            this.trackOnMap(trackId);
            console.log(`Single track selected: ${trackId}`);
        }
    }

    showBattleGroupDialog() {
        console.log('Attempting to show battle group dialog...');
        
        // Ensure multi-select mode is disabled when dialog opens
        this.isMultiSelecting = false;
        document.body.classList.remove('multi-select-mode');
        
        const dialog = document.getElementById('battle-group-dialog');
        const selectedCount = document.getElementById('selected-count');
        const selectedTracksPreview = document.getElementById('selected-tracks-preview');
        const nameInput = document.getElementById('battle-group-name-input');
        
        if (!dialog) {
            console.error('Battle group dialog not found!');
            console.log('Available elements:', document.querySelectorAll('[id*="battle"]'));
            return;
        }
        
        if (!selectedCount) {
            console.error('Selected count element not found!');
            return;
        }
        
        if (!selectedTracksPreview) {
            console.error('Selected tracks preview element not found!');
            return;
        }
        
        if (!nameInput) {
            console.error('Battle group name input not found!');
            return;
        }
        
        console.log('All dialog elements found, updating content...');
        
        // Update dialog content
        selectedCount.textContent = this.selectedTracks.size;
        
        // Generate default name and set it as placeholder
        const defaultName = `Battle Group ${String.fromCharCode(65 + this.battleGroupCounter)}`;
        nameInput.placeholder = `Enter name or leave blank for "${defaultName}"`;
        nameInput.value = ''; // Clear any previous value
        
        // Show preview of selected tracks
        selectedTracksPreview.innerHTML = '';
        Array.from(this.selectedTracks).forEach(trackId => {
            const track = this.tracks.get(trackId);
            if (track) {
                const trackElement = document.createElement('div');
                trackElement.className = 'flex items-center justify-between py-1';
                trackElement.innerHTML = `
                    <span class="text-slate-300">${trackId}</span>
                    <span class="text-xs text-slate-400">${track.track_type || 'Unknown'}</span>
                `;
                selectedTracksPreview.appendChild(trackElement);
            } else {
                console.log(`Track ${trackId} not found in tracks map - adding placeholder`);
                const trackElement = document.createElement('div');
                trackElement.className = 'flex items-center justify-between py-1';
                trackElement.innerHTML = `
                    <span class="text-slate-300">${trackId}</span>
                    <span class="text-xs text-slate-400">Unknown</span>
                `;
                selectedTracksPreview.appendChild(trackElement);
            }
        });
        
        // Show dialog with additional logging
        console.log('Removing hidden class from dialog');
        dialog.classList.remove('hidden');
        
        // Force display and visibility
        dialog.style.display = 'flex';
        dialog.style.visibility = 'visible';
        dialog.style.opacity = '1';
        dialog.style.zIndex = '9999';
        
        // Focus on the name input for better UX
        setTimeout(() => {
            nameInput.focus();
            nameInput.select(); // Select any existing text for easy replacement
        }, 150);
        
        // Force visibility check
        setTimeout(() => {
            const computedStyle = window.getComputedStyle(dialog);
            console.log('Dialog visibility after show:', {
                display: computedStyle.display,
                visibility: computedStyle.visibility,
                opacity: computedStyle.opacity,
                zIndex: computedStyle.zIndex,
                hasHiddenClass: dialog.classList.contains('hidden')
            });
        }, 50);
        
        console.log('Battle group dialog should now be visible');
    }

    hideBattleGroupDialog() {
        console.log('Hiding battle group dialog...');
        const dialog = document.getElementById('battle-group-dialog');
        const nameInput = document.getElementById('battle-group-name-input');
        
        if (dialog) {
            // Remove visible state
            dialog.classList.add('hidden');
            
            // Force hide with inline styles
            dialog.style.display = 'none';
            dialog.style.visibility = 'hidden';
            dialog.style.opacity = '0';
            
            // Clear the name input for next use
            if (nameInput) {
                nameInput.value = '';
            }
            
            console.log('Battle group dialog hidden');
        } else {
            console.error('Battle group dialog not found when trying to hide');
        }
    }

    bindBattleGroupEvents() {
        console.log('Binding battle group dialog events...');
        
        // Cancel button
        const cancelBtn = document.getElementById('cancel-battle-group');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                console.log('Cancel button clicked');
                this.selectedTracks.clear();
                this.updateTracksDisplay();
                this.hideBattleGroupDialog();
            });
        } else {
            console.error('Cancel battle group button not found!');
        }

        // Confirm button
        const confirmBtn = document.getElementById('confirm-battle-group');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                console.log('Confirm button clicked');
                this.createBattleGroup();
            });
        } else {
            console.error('Confirm battle group button not found!');
        }
        
        // Name input field - Enter key support
        const nameInput = document.getElementById('battle-group-name-input');
        if (nameInput) {
            nameInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    console.log('Enter key pressed in name input - creating battle group');
                    this.createBattleGroup();
                }
            });
        }
        
        // Also allow clicking outside the dialog to close it
        const dialog = document.getElementById('battle-group-dialog');
        if (dialog) {
            dialog.addEventListener('click', (e) => {
                // Only close if clicking on the backdrop (not the dialog content)
                if (e.target === dialog) {
                    console.log('Dialog backdrop clicked - closing dialog');
                    this.selectedTracks.clear();
                    this.updateTracksDisplay();
                    this.hideBattleGroupDialog();
                }
            });
        }
        
        // Add keyboard escape support
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const dialog = document.getElementById('battle-group-dialog');
                if (dialog && !dialog.classList.contains('hidden')) {
                    console.log('Escape key pressed - closing dialog');
                    this.selectedTracks.clear();
                    this.updateTracksDisplay();
                    this.hideBattleGroupDialog();
                }
            }
        });
    }

    createBattleGroup() {
        console.log('Creating battle group...');
        const selectedTrackIds = Array.from(this.selectedTracks);
        const nameInput = document.getElementById('battle-group-name-input');
        
        // Get custom name or use default
        let customName = nameInput ? nameInput.value.trim() : '';
        let battleGroupName, battleGroupId;
        
        if (customName) {
            // Use custom name
            battleGroupName = customName;
            battleGroupId = `BG-${customName.replace(/[^a-zA-Z0-9]/g, '')}`; // Clean ID
            console.log(`Using custom name: ${battleGroupName}`);
        } else {
            // Use default naming scheme
            const defaultLetter = String.fromCharCode(65 + this.battleGroupCounter);
            battleGroupName = `Battle Group ${defaultLetter}`;
            battleGroupId = `BG-${defaultLetter}`;
            console.log(`Using default name: ${battleGroupName}`);
        }
        
        const battleGroup = {
            id: battleGroupId,
            name: battleGroupName,
            tracks: selectedTrackIds,
            created: new Date().toISOString(),
            color: this.getBattleGroupColor(this.battleGroupCounter)
        };
        
        // Check if ID already exists (for custom names)
        if (this.battleGroups.has(battleGroupId)) {
            // Add a number suffix to make it unique
            let counter = 1;
            let newId = `${battleGroupId}-${counter}`;
            while (this.battleGroups.has(newId)) {
                counter++;
                newId = `${battleGroupId}-${counter}`;
            }
            battleGroup.id = newId;
            if (customName) {
                battleGroup.name = `${battleGroupName} (${counter})`;
            }
        }
        
        this.battleGroups.set(battleGroup.id, battleGroup);
        this.battleGroupCounter++;
        
        // Clear selection
        this.selectedTracks.clear();
        this.updateTracksDisplay();
        this.updateBattleGroupsDisplay();
        
        // Hide dialog first
        this.hideBattleGroupDialog();
        
        // Show notification
        this.showNotification(`${battleGroup.name} created with ${selectedTrackIds.length} tracks`, 'success');
        
        // Update map highlighting
        if (window.cesiumAdvanced && window.cesiumAdvanced.isActive()) {
            window.cesiumAdvanced.highlightBattleGroup(battleGroup);
        }
        
        console.log('Battle group created and dialog hidden:', battleGroup);
    }

    getBattleGroupColor(index) {
        const colors = ['orange', 'red', 'green', 'blue', 'purple', 'yellow', 'pink', 'cyan'];
        return colors[index % colors.length];
    }

    updateBattleGroupsDisplay() {
        const section = document.getElementById('battle-groups-section');
        const list = document.getElementById('battle-groups-list');
        const counter = document.getElementById('total-battle-groups');
        
        if (this.battleGroups.size === 0) {
            section.classList.add('hidden');
            return;
        }
        
        section.classList.remove('hidden');
        counter.textContent = this.battleGroups.size;
        
        list.innerHTML = '';
        this.battleGroups.forEach((battleGroup, id) => {
            const groupElement = document.createElement('div');
            groupElement.className = 'bg-slate-800 border border-slate-600 rounded-lg p-3';
            groupElement.innerHTML = `
                <div class="flex items-center justify-between mb-2">
                    <h7 class="font-semibold text-white flex items-center">
                        <i class="fas fa-users mr-2" style="color: ${battleGroup.color}"></i>
                        ${battleGroup.name}
                    </h7>
                    <button class="text-red-400 hover:text-red-300 text-sm" onclick="dashboard.disbandBattleGroup('${id}')">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="text-xs text-slate-400 mb-2">
                    ${battleGroup.tracks.length} tracks
                </div>
                <div class="flex flex-wrap gap-1">
                    ${battleGroup.tracks.map(trackId => 
                        `<span class="px-2 py-1 bg-slate-700 text-slate-300 rounded text-xs">${trackId}</span>`
                    ).join('')}
                </div>
                <div class="mt-2 flex space-x-2">
                    <button class="bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded text-xs" 
                            onclick="dashboard.focusBattleGroup('${id}')">
                        <i class="fas fa-search mr-1"></i> Focus
                    </button>
                    <button class="bg-green-600 hover:bg-green-700 text-white px-2 py-1 rounded text-xs" 
                            onclick="dashboard.followBattleGroup('${id}')">
                        <i class="fas fa-video mr-1"></i> Follow
                    </button>
                </div>
            `;
            list.appendChild(groupElement);
        });
    }

    disbandBattleGroup(battleGroupId) {
        const battleGroup = this.battleGroups.get(battleGroupId);
        if (battleGroup) {
            this.battleGroups.delete(battleGroupId);
            this.updateBattleGroupsDisplay();
            this.showNotification(`${battleGroup.name} disbanded`, 'info');
            
            // Update map
            if (window.cesiumAdvanced && window.cesiumAdvanced.isActive()) {
                window.cesiumAdvanced.clearBattleGroupHighlight(battleGroupId);
            }
        }
    }

    focusBattleGroup(battleGroupId) {
        const battleGroup = this.battleGroups.get(battleGroupId);
        if (battleGroup && window.cesiumAdvanced && window.cesiumAdvanced.isActive()) {
            window.cesiumAdvanced.focusOnBattleGroup(battleGroup);
        }
    }

    followBattleGroup(battleGroupId) {
        const battleGroup = this.battleGroups.get(battleGroupId);
        if (battleGroup && window.cesiumAdvanced && window.cesiumAdvanced.isActive()) {
            window.cesiumAdvanced.followBattleGroup(battleGroup);
        }
    }

    showAutoRefreshIndicator() {
        const autoRefreshIndicator = document.querySelector('.text-green-400');
        if (autoRefreshIndicator) {
            // Briefly highlight the auto-refresh indicator
            const icon = autoRefreshIndicator.querySelector('i');
            if (icon) {
                icon.classList.add('fa-spin');
                setTimeout(() => {
                    icon.classList.remove('fa-spin');
                }, 500);
            }
        }
    }

    testBattleGroupDialog() {
        console.log('Testing battle group dialog...');
        
        // Simulate having selected tracks
        this.selectedTracks.clear();
        this.selectedTracks.add('TRK1000');
        this.selectedTracks.add('TRK1001');
        
        console.log('Added test tracks to selection:', Array.from(this.selectedTracks));
        
        // Try to show the dialog
        this.showBattleGroupDialog();
        
        // Test auto-close after 5 seconds for debugging
        setTimeout(() => {
            console.log('Auto-closing dialog after 5 seconds for testing...');
            this.hideBattleGroupDialog();
        }, 5000);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing dashboard...');
    try {
        window.dashboard = new SurveillanceDashboard();
        console.log('Dashboard created successfully:', window.dashboard);
    } catch (error) {
        console.error('Error creating dashboard:', error);
    }
});