// Dashboard functionality
class SurveillanceDashboard {
    constructor() {
        // Dashboard constructor
        this.tracks = new Map();
        this.events = []; // Historical events for Event Log
        this.monitorEvents = []; // Real-time events for Event Monitor
        this.currentPage = 1;
        this.isLiveDemo = false;
        this.isBattleMode = false;
        this.updateInterval = null;
        this.monitorInterval = null; // For Event Monitor auto-refresh
        this.eventLogInterval = null; // For Event Log auto-refresh
        this.selectedTracks = new Set(); // For multi-track selection
        this.battleGroups = new Map(); // Battle Groups storage
        this.battleGroupCounter = 0; // Counter for naming battle groups
        this.isMultiSelecting = false; // Track if we're in multi-select mode
        // Dashboard properties initialized
        
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
        // Dashboard initialized with multi-select functionality
    }

    setupSocketHandlers() {
        // Setting up socket handlers

        // Handle real-time track updates
        this.socket.on('track_update', (tracks) => {
            // Debug log removed
            this.onTrackUpdate(tracks);
        });

        // Handle real-time event notes updates
        this.socket.on('event_notes_updated', (data) => {
            // Debug log removed
            this.handleEventNotesUpdate(data);
        });

        // Handle real-time new events
        this.socket.on('new_event', (event) => {
            // Debug log removed
            this.handleNewEvent(event);
        });

        // Handle connection status
        this.socket.on('status', (data) => {
            // Debug log removed
            this.showNotification(data.msg, 'info');
        });

        this.socket.on('connect', () => {
            // Debug log removed
        });

        this.socket.on('disconnect', () => {
            // Debug log removed
        });

        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
        });
    }

    bindEvents() {
        // Control buttons
        const startDemoBtn = document.getElementById('start-demo-btn');
        if (startDemoBtn) startDemoBtn.addEventListener('click', () => this.startLiveDemo());
        const stopDemoBtn = document.getElementById('stop-demo-btn');
        if (stopDemoBtn) stopDemoBtn.addEventListener('click', () => this.stopLiveDemo());
        const battleModeBtn = document.getElementById('battle-mode-btn');
        if (battleModeBtn) {
            battleModeBtn.addEventListener('click', () => this.toggleBattleMode());
            battleModeBtn.addEventListener('dblclick', () => this.toggleAdvanced3DMode());
        }

        // Filters
        const trackTypeFilter = document.getElementById('track-type-filter');
        if (trackTypeFilter) trackTypeFilter.addEventListener('change', (e) => this.filterTracks(e.target.value));
        const searchInput = document.getElementById('search-input');
        if (searchInput) searchInput.addEventListener('input', (e) => this.searchTracks(e.target.value));

        // Event handlers
        const refreshEventsBtn = document.getElementById('refresh-events-btn');
        if (refreshEventsBtn) refreshEventsBtn.addEventListener('click', () => this.refreshEvents());
        const clearFiltersBtn = document.getElementById('clear-filters-btn');
        if (clearFiltersBtn) clearFiltersBtn.addEventListener('click', () => this.clearEventLogFilters());
        const exportLogBtn = document.getElementById('export-log-btn');
        if (exportLogBtn) exportLogBtn.addEventListener('click', () => this.exportEventLog());

        // Event Log filter handlers - automatic filtering on change
        const startDate = document.getElementById('start-date');
        if (startDate) startDate.addEventListener('change', () => this.filterEventLog());
        const endDate = document.getElementById('end-date');
        if (endDate) endDate.addEventListener('change', () => this.filterEventLog());
        const eventTypeFilter = document.getElementById('event-type-filter');
        if (eventTypeFilter) eventTypeFilter.addEventListener('change', () => this.filterEventLog());

        // Event Monitor filter handlers - automatic filtering on change
        const monitorEventTypeFilter = document.getElementById('monitor-event-type-filter');
        if (monitorEventTypeFilter) monitorEventTypeFilter.addEventListener('change', () => this.applyMonitorFilters());
        const monitorTrackTypeFilter = document.getElementById('monitor-track-type-filter');
        if (monitorTrackTypeFilter) monitorTrackTypeFilter.addEventListener('change', () => this.applyMonitorFilters());

        // Add debounced input for track ID filter
        let trackFilterTimeout;
        const monitorTrackFilter = document.getElementById('monitor-track-filter');
        if (monitorTrackFilter) {
            monitorTrackFilter.addEventListener('input', () => {
                clearTimeout(trackFilterTimeout);
                trackFilterTimeout = setTimeout(() => this.applyMonitorFilters(), 300);
            });
        }

        const clearMonitorFiltersBtn = document.getElementById('clear-monitor-filters-btn');
        if (clearMonitorFiltersBtn) clearMonitorFiltersBtn.addEventListener('click', () => this.clearMonitorFilters());

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
            
            // Load initial Event Log data
            await this.loadEventLog();
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
            console.log('Tracks received from API:', tracks);
            this.tracks.clear();
            tracks.forEach(track => {
                console.log('Processing track:', track);
                this.tracks.set(track.track_id, track);
            });
            console.log('Total tracks processed:', this.tracks.size);
            this.updateTracksDisplay();
            // Update the map with current filters
            this.updateMapWithCurrentFilters();
            
        } catch (error) {
            // Silently handle errors to avoid console spam
            if (error.name !== 'AbortError') {
                console.warn('Tracks temporarily unavailable');
            }
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
        if (this.eventLogInterval) {
            clearInterval(this.eventLogInterval);
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

        // Event Log updates every 3 seconds for history
        this.eventLogInterval = setInterval(async () => {
            await this.loadEventLog();
        }, 3000);

        // Debug log removed
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
        if (this.eventLogInterval) {
            clearInterval(this.eventLogInterval);
            this.eventLogInterval = null;
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
        // Debug log removed
        
        // Always reapply Active Tracks table filters to maintain table state
        this.applyFilters();
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
        // Debug log removed
        
        // Check if Event Monitor filters are active - if so, don't interfere with map filtering
        const trackFilter = document.getElementById('monitor-track-filter')?.value?.toLowerCase() || '';
        const eventTypeFilter = document.getElementById('monitor-event-type-filter')?.value || '';
        const trackTypeFilter = document.getElementById('monitor-track-type-filter')?.value || '';
        
        // Debug log removed
        
        // Only apply Active Tracks filter to map if Event Monitor filters are not active
        if (!trackFilter && !eventTypeFilter && !trackTypeFilter) {
            // Debug log removed
            if (window.mapManager) {
                window.mapManager.filterByType(type);
            }
        } else {
            // Debug log removed
        }

        // Always apply the filter to the tracks table
        this.applyFilters();
    }

    searchTracks(query) {
        this.applyFilters();
    }

    applyFilters() {
        const typeFilter = document.getElementById('track-type-filter')?.value || '';
        const searchQuery = document.getElementById('search-input')?.value || '';

        // If no filters are active, show all rows
        if (!typeFilter && !searchQuery) {
            const rows = document.querySelectorAll('#tracks-table-body tr');
            rows.forEach(row => {
                row.style.display = '';
            });
            return;
        }

        const rows = document.querySelectorAll('#tracks-table-body tr');
        rows.forEach(row => {
            const trackType = row.cells[1].textContent.trim();
            const trackId = row.dataset.trackId || row.cells[0].textContent.trim().replace(/.*?([A-Z]+\d+).*/, '$1');
            
            const matchesType = !typeFilter || trackType === typeFilter;
            const matchesSearch = !searchQuery || trackId.toLowerCase().includes(searchQuery.toLowerCase());
            
            if (matchesType && matchesSearch) {
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
            // Debug log removed
            return;
        }

        // Debug log removed

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

        // Get filter values
        const trackFilter = document.getElementById('monitor-track-filter')?.value?.toLowerCase() || '';
        const eventTypeFilter = document.getElementById('monitor-event-type-filter')?.value || '';
        const trackTypeFilter = document.getElementById('monitor-track-type-filter')?.value || '';

        // Filter events based on filter criteria
        let filteredEvents = this.monitorEvents;

        if (trackFilter) {
            filteredEvents = filteredEvents.filter(event => 
                event.track_id?.toLowerCase().includes(trackFilter)
            );
        }

        if (eventTypeFilter) {
            filteredEvents = filteredEvents.filter(event => 
                event.event_type === eventTypeFilter
            );
        }

        if (trackTypeFilter) {
            filteredEvents = filteredEvents.filter(event => 
                event.track_type === trackTypeFilter
            );
        }

        // Show real-time monitor events (most recent first)
        const eventsToShow = filteredEvents.slice(-50).reverse();
        // Debug log removed

        // Update event count display
        const eventCountSpan = document.getElementById('monitor-event-count');
        if (eventCountSpan) {
            eventCountSpan.textContent = eventsToShow.length;
        }

        if (eventsToShow.length === 0) {
            // Show no results message when filters exclude all events
            const noResultsRow = document.createElement('tr');
            noResultsRow.innerHTML = `
                <td colspan="8" class="px-4 py-8 text-center text-slate-400">
                    <i class="fas fa-filter text-2xl mb-2"></i><br>
                    No events match the current filters<br>
                    <small>Try adjusting your filter criteria</small>
                </td>
            `;
            tbody.appendChild(noResultsRow);
            return;
        }

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

        // Debug log removed
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
                    // Debug log removed`);
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
        // Debug log removed
    }

    async loadEventLog() {
        try {
            // Debug log removed
            const response = await fetch(`/api/events?page=${this.currentPage}&per_page=20`);
            const data = await response.json();

            // Debug log removed
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

        // Debug log removed

        events.forEach(event => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="px-4 py-2">${new Date(event.timestamp).toLocaleString()}</td>
                <td class="px-4 py-2">${event.track_id}</td>
                <td class="px-4 py-2"><span class="px-2 py-1 rounded text-xs font-semibold bg-blue-100 text-blue-800">${event.event_type}</span></td>
                <td class="px-4 py-2">${event.description}</td>
                <td class="px-4 py-2">
                    <button class="bg-blue-500 hover:bg-blue-600 text-white px-2 py-1 rounded text-xs transition-colors" 
                            onclick="dashboard.editEventDetails(${event.id})" 
                            title="Add/Edit Details">
                        <i class="fas fa-info-circle"></i>
                    </button>
                    ${event.user_notes ? `<span class="ml-2 text-red-500" title="Has user notes"><i class="fas fa-exclamation-triangle"></i></span>` : ''}
                </td>
            `;
            tbody.appendChild(row);
        });

        // Debug log removed
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

    async filterEventLog() {
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;
        const eventType = document.getElementById('event-type-filter').value;

        // Debug log removed
        
        try {
            // Build query parameters
            const params = new URLSearchParams();
            params.append('page', this.currentPage);
            params.append('per_page', '20');
            
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);
            if (eventType) params.append('event_type', eventType);
            
            // Make API call with filters
            const response = await fetch(`/api/events?${params.toString()}`);
            const data = await response.json();
            
            // Update display with filtered results
            this.updateEventLogDisplay(data.events);
            this.updatePagination(data.current_page, data.pages);
            
            // Show success message
            const filterCount = data.events.length;
            const totalPages = data.pages;
            this.showNotification(`Event log filtered - ${filterCount} events found (${totalPages} pages)`, 'success');
            
        } catch (error) {
            console.error('Error filtering event log:', error);
            this.showNotification('Error filtering event log', 'error');
        }
    }

    clearEventLogFilters() {
        // Clear all filter inputs
        document.getElementById('start-date').value = '';
        document.getElementById('end-date').value = '';
        document.getElementById('event-type-filter').value = '';
        
        // Reset to page 1 and reload without filters
        this.currentPage = 1;
        this.loadEventLog();
        
        this.showNotification('Event log filters cleared', 'info');
    }

    exportEventLog() {
        // Debug log removed
        // Call the API to export the event log (without clearing)
        if (confirm('This will export all events to CSV. The log will remain in the system. Continue?')) {
            // Debug log removed
            fetch('/api/export-events', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                // Debug log removed
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
            // Debug log removed
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
                // Debug log removed
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
                // Debug log removed
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

    async editEventDetails(eventId) {
        try {
            // First, get the current notes for this event
            const response = await fetch(`/api/events/${eventId}/notes`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Failed to load event details');
            }
            
            const currentNotes = data.notes || '';
            const event = data.event;
            
            // Create a modal dialog for editing notes
            const modal = this.createEventDetailsModal(event, currentNotes);
            document.body.appendChild(modal);
            
            // Show the modal
            modal.style.display = 'flex';
            
            // Focus on the textarea
            const textarea = modal.querySelector('textarea');
            if (textarea) {
                textarea.focus();
                textarea.setSelectionRange(textarea.value.length, textarea.value.length);
            }
            
        } catch (error) {
            console.error('Error loading event details:', error);
            this.showNotification('Failed to load event details: ' + error.message, 'error');
        }
    }

    createEventDetailsModal(event, currentNotes) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.style.display = 'none';
        
        modal.innerHTML = `
            <div class="bg-slate-800 rounded-lg p-6 w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto">
                <div class="flex justify-between items-start mb-4">
                    <h3 class="text-xl font-bold text-white">Event Details</h3>
                    <button class="text-gray-400 hover:text-white text-xl" onclick="this.closest('.fixed').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <div class="mb-4 space-y-3">
                    <div class="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <label class="text-gray-300 font-medium">Track ID:</label>
                            <p class="text-white">${event.track_id}</p>
                        </div>
                        <div>
                            <label class="text-gray-300 font-medium">Event Type:</label>
                            <p class="text-white">${event.event_type}</p>
                        </div>
                        <div class="col-span-2">
                            <label class="text-gray-300 font-medium">Timestamp:</label>
                            <p class="text-white">${new Date(event.timestamp).toLocaleString()}</p>
                        </div>
                        <div class="col-span-2">
                            <label class="text-gray-300 font-medium">Description:</label>
                            <p class="text-white">${event.description}</p>
                        </div>
                    </div>
                </div>
                
                <div class="mb-4">
                    <label class="text-gray-300 font-medium mb-2 block">Additional Notes:</label>
                    <textarea 
                        class="w-full h-32 p-3 bg-slate-700 text-white rounded border border-slate-600 focus:border-blue-500 focus:outline-none resize-none"
                        placeholder="Add your notes or details about this event..."
                        maxlength="1000"
                    >${currentNotes}</textarea>
                    <div class="text-xs text-gray-400 mt-1">
                        <span id="char-count">${currentNotes.length}</span>/1000 characters
                    </div>
                </div>
                
                <div class="flex justify-end space-x-3">
                    <button class="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors" 
                            onclick="this.closest('.fixed').remove()">
                        Cancel
                    </button>
                    <button class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors" 
                            onclick="dashboard.saveEventNotes(${event.id}, this)">
                        Save Notes
                    </button>
                </div>
            </div>
        `;
        
        // Add character counter
        const textarea = modal.querySelector('textarea');
        const charCount = modal.querySelector('#char-count');
        
        textarea.addEventListener('input', () => {
            charCount.textContent = textarea.value.length;
        });
        
        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
        
        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.parentNode) {
                modal.remove();
            }
        });
        
        return modal;
    }

    async saveEventNotes(eventId, button) {
        const modal = button.closest('.fixed');
        const textarea = modal.querySelector('textarea');
        const notes = textarea.value.trim();
        
        // Show loading state
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        
        try {
            const response = await fetch(`/api/events/${eventId}/notes`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ notes: notes })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Failed to save notes');
            }
            
            // Close modal
            modal.remove();
            
            // Show success notification
            this.showNotification('Event notes saved successfully!', 'success');
            
            // Refresh the event log display
            this.loadEventLog();
            
        } catch (error) {
            console.error('Error saving event notes:', error);
            this.showNotification('Failed to save notes: ' + error.message, 'error');
            
            // Reset button state
            button.disabled = false;
            button.innerHTML = 'Save Notes';
        }
    }

    handleEventNotesUpdate(data) {
        // Debug log removed
        
        // Find the event row in the current display
        const eventRows = document.querySelectorAll('#events-log-body tr');
        
        eventRows.forEach(row => {
            // Check if this row contains a button for the updated event
            const button = row.querySelector(`[onclick*="${data.event_id}"]`);
            if (button) {
                // Update the details cell
                const detailsCell = button.closest('td');
                if (detailsCell) {
                    // Update the button and add/remove notes indicator
                    const hasNotes = data.notes && data.notes.trim().length > 0;
                    const notesIndicator = detailsCell.querySelector('.text-red-500');
                    
                    if (hasNotes) {
                        // Add notes indicator if it doesn't exist
                        if (!notesIndicator) {
                            const indicator = document.createElement('span');
                            indicator.className = 'ml-2 text-red-500';
                            indicator.title = 'Has user notes';
                            indicator.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
                            detailsCell.appendChild(indicator);
                        }
                    } else {
                        // Remove notes indicator if notes are empty
                        if (notesIndicator) {
                            notesIndicator.remove();
                        }
                    }
                }
                
                // Show a subtle notification for other users
                this.showNotification(`Event notes updated for ${data.event_id}`, 'info');
                return;
            }
        });
    }

    // ...existing code...

    onTrackUpdate(tracks) {
        // Debug log removed
        tracks.forEach(track => {
            this.tracks.set(track.track_id, track);
        });

        this.updateTracksDisplay();

        // Always update the map with the proper filtered tracks
        this.updateMapWithCurrentFilters();
    }

    updateMapWithCurrentFilters() {
        if (!window.mapManager) {
            // Debug log removed
            return;
        }

        // Always ensure the map has the full track list first
        const allTracks = Array.from(this.tracks.values());
        window.mapManager.setFullTrackList(allTracks);

        // Check if Event Monitor filters are active
        const trackFilter = document.getElementById('monitor-track-filter')?.value?.toLowerCase() || '';
        const trackTypeFilter = document.getElementById('monitor-track-type-filter')?.value || '';
        
        // Debug log removed
        
        if (trackFilter || trackTypeFilter) {
            // Event Monitor filters are active - apply them to the map
            // Debug log removed
            this.applyFiltersToMap(trackFilter, trackTypeFilter);
        } else {
            // No Event Monitor filters - check if Active Tracks tab filter should be applied
            const activeTracksFilter = document.getElementById('track-type-filter')?.value || '';
            // Debug log removed
            
            if (activeTracksFilter) {
                // Apply Active Tracks filter to map
                // Debug log removed
                window.mapManager.filterByType(activeTracksFilter);
            } else {
                // No filters active - show all tracks
                // Debug log removed
                window.mapManager.updateTracks(allTracks);
            }
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
        // Debug log removed
        
        // Track shift key state globally
        document.addEventListener('keydown', (e) => {
            // Don't activate multi-select mode if dialog is open or if user is typing in an input field
            if (e.key === 'Shift' && !this.isDialogOpen() && !this.isTypingInInput(e.target)) {
                // Debug log removed
                this.isMultiSelecting = true;
                document.body.classList.add('multi-select-mode');
                
                // Add visual indicator for map selection
                if (window.mapManager) {
                    const mapContainer = document.getElementById('map-container');
                    if (mapContainer) {
                        mapContainer.style.cursor = 'crosshair';
                    }
                }
            }
        });

        document.addEventListener('keyup', (e) => {
            // Only process shift release if we were in multi-select mode
            if (e.key === 'Shift' && this.isMultiSelecting) {
                // Debug log removed
                this.isMultiSelecting = false;
                document.body.classList.remove('multi-select-mode');
                
                // Remove visual indicator
                if (window.mapManager) {
                    const mapContainer = document.getElementById('map-container');
                    if (mapContainer) {
                        mapContainer.style.cursor = '';
                    }
                }
                
                // Show battle group dialog if we have multiple tracks selected
                if (this.selectedTracks.size > 1) {
                    // Debug log removed
                    // Debug log removed);
                    
                    // Add a small delay to ensure the UI is ready
                    setTimeout(() => {
                        this.showBattleGroupDialog();
                    }, 100);
                } else {
                    // Debug log removed
                    // Clear selection and highlighting if not enough tracks
                    this.selectedTracks.clear();
                    this.updateTracksDisplay();
                    if (window.mapManager) {
                        window.mapManager.updateTrackHighlighting();
                    }
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
        // Debug log removed
        
        if (this.isMultiSelecting) {
            // Multi-select mode
            if (this.selectedTracks.has(trackId)) {
                this.selectedTracks.delete(trackId);
                // Debug log removed
            } else {
                this.selectedTracks.add(trackId);
                // Debug log removed
            }
            
            // Log current selection state
            // Debug log removed);
            
            // Update the track display to show selection
            this.updateTracksDisplay();
            
            // Update map highlighting consistently
            if (window.mapManager && window.mapManager.updateTrackHighlighting) {
                window.mapManager.updateTrackHighlighting();
            } else if (window.cesiumAdvanced && window.cesiumAdvanced.isActive()) {
                // Fallback to direct highlighting update
                window.cesiumAdvanced.highlightSelectedTracks(Array.from(this.selectedTracks));
            }
        } else {
            // Single track selection - clear previous selections
            this.selectedTracks.clear();
            this.selectedTracks.add(trackId);
            this.updateTracksDisplay();
            
            // Focus on single track
            this.trackOnMap(trackId);
            // Debug log removed
        }
    }

    showBattleGroupDialog() {
        // Debug log removed
        
        // Ensure multi-select mode is disabled when dialog opens
        this.isMultiSelecting = false;
        document.body.classList.remove('multi-select-mode');
        
        const dialog = document.getElementById('battle-group-dialog');
        const selectedCount = document.getElementById('selected-count');
        const selectedTracksPreview = document.getElementById('selected-tracks-preview');
        const nameInput = document.getElementById('battle-group-name-input');
        
        if (!dialog) {
            console.error('Battle group dialog not found!');
            // Debug log removed);
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
        
        // Debug log removed
        
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
                // Debug log removed
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
        // Debug log removed
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
            // Debug log removed
        }, 50);
        
        // Debug log removed
    }

    hideBattleGroupDialog() {
        // Debug log removed
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
            
            // Debug log removed
        } else {
            console.error('Battle group dialog not found when trying to hide');
        }
    }

    bindBattleGroupEvents() {
        // Debug log removed
        
        // Cancel button
        const cancelBtn = document.getElementById('cancel-battle-group');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                // Debug log removed
                this.selectedTracks.clear();
                this.updateTracksDisplay();
                // Remove highlighting from map
                if (window.mapManager) {
                    window.mapManager.updateTrackHighlighting();
                }
                this.hideBattleGroupDialog();
            });
        } else {
            console.error('Cancel battle group button not found!');
        }

        // Confirm button
        const confirmBtn = document.getElementById('confirm-battle-group');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                // Debug log removed
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
                    // Debug log removed
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
                    // Debug log removed
                    this.selectedTracks.clear();
                    this.updateTracksDisplay();
                    // Remove highlighting from map
                    if (window.mapManager) {
                        window.mapManager.updateTrackHighlighting();
                    }
                    this.hideBattleGroupDialog();
                }
            });
        }
        
        // Add keyboard escape support
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const dialog = document.getElementById('battle-group-dialog');
                if (dialog && !dialog.classList.contains('hidden')) {
                    // Debug log removed
                    this.selectedTracks.clear();
                    this.updateTracksDisplay();
                    // Remove highlighting from map
                    if (window.mapManager) {
                        window.mapManager.updateTrackHighlighting();
                    }
                    this.hideBattleGroupDialog();
                }
            }
        });
    }

    createBattleGroup() {
        // Debug log removed
        const selectedTrackIds = Array.from(this.selectedTracks);
        const nameInput = document.getElementById('battle-group-name-input');
        
        // Get custom name or use default
        let customName = nameInput ? nameInput.value.trim() : '';
        let battleGroupName, battleGroupId;
        
        if (customName) {
            // Use custom name
            battleGroupName = customName;
            battleGroupId = `BG-${customName.replace(/[^a-zA-Z0-9]/g, '')}`; // Clean ID
            // Debug log removed
        } else {
            // Use default naming scheme
            const defaultLetter = String.fromCharCode(65 + this.battleGroupCounter);
            battleGroupName = `Battle Group ${defaultLetter}`;
            battleGroupId = `BG-${defaultLetter}`;
            // Debug log removed
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
        
        // Remove highlighting from map
        if (window.mapManager) {
            window.mapManager.updateTrackHighlighting();
        }
        
        // Hide dialog first
        this.hideBattleGroupDialog();
        
        // Show notification
        this.showNotification(`${battleGroup.name} created with ${selectedTrackIds.length} tracks`, 'success');
        
        // Update map highlighting
        if (window.cesiumAdvanced && window.cesiumAdvanced.isActive()) {
            window.cesiumAdvanced.highlightBattleGroup(battleGroup);
        }
        
        // Debug log removed
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
            
            // Clear highlighting from map
            if (window.cesiumAdvanced && window.cesiumAdvanced.isActive()) {
                window.cesiumAdvanced.clearBattleGroupHighlight(battleGroupId);
            }
            
            // Also clear any current selection highlighting if these tracks are selected
            if (window.mapManager) {
                window.mapManager.updateTrackHighlighting();
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

    applyMonitorFilters() {
        // Debug log removed
        
        // Update the Event Monitor display
        this.updateEventsDisplay();
        
        // Update the map with the current filters
        this.updateMapWithCurrentFilters();
    }

    applyFiltersToMap(trackFilter, trackTypeFilter) {
        // Debug log removed
        
        // Always start with the full track list from the dashboard
        let filteredTracks = Array.from(this.tracks.values());
        // Debug log removed
        
        // Apply track ID filter
        if (trackFilter) {
            filteredTracks = filteredTracks.filter(track => 
                track.track_id?.toLowerCase().includes(trackFilter)
            );
            // Debug log removed
        }
        
        // Apply track type filter
        if (trackTypeFilter) {
            filteredTracks = filteredTracks.filter(track => 
                track.track_type === trackTypeFilter || track.type === trackTypeFilter
            );
            // Debug log removed
        }
        
        // Update map with filtered tracks
        if (window.mapManager) {
            window.mapManager.updateTracks(filteredTracks);
            // Debug log removed
        }
    }

    clearMonitorFilters() {
        // Debug log removed
        // Clear all filter inputs
        document.getElementById('monitor-track-filter').value = '';
        document.getElementById('monitor-event-type-filter').value = '';
        document.getElementById('monitor-track-type-filter').value = '';
        
        // Apply filters (which will now show all events and tracks)
        this.applyMonitorFilters();
    }

    handleNewEvent(event) {
        // Debug log removed
        
        // Add the new event to the events array (at the beginning for newest first)
        this.events.unshift(event);
        
        // Refresh the event log display to show the new event
        this.loadEventLog();
        
        // Show a notification for the new event
        this.showNotification(`New event: ${event.event_type} for ${event.track_id}`, 'info');
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Debug log removed
    try {
        window.dashboard = new SurveillanceDashboard();
        // Debug log removed
    } catch (error) {
        console.error('Error creating dashboard:', error);
    }
});
