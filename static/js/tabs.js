// Tab management for Tailwind-based interface
function showTab(tabName) {
    // Hide all tab content
    const tabs = ['dashboard', 'event-monitor', 'event-log', 'messenger'];
    tabs.forEach(tab => {
        const element = document.getElementById(tab);
        if (element) {
            element.classList.add('hidden');
        }
    });
    
    // Show selected tab
    const selectedTab = document.getElementById(tabName);
    if (selectedTab) {
        selectedTab.classList.remove('hidden');
    }
    
    // Update dashboard on tab switch
    if (tabName === 'dashboard' && window.dashboard) {
        setTimeout(() => {
            window.dashboard.loadInitialData();
            if (window.mapManager) {
                window.mapManager.initMaps();
            }
        }, 100);
    }
    
    // Load Event Log data when switching to Event Log tab
    if (tabName === 'event-log' && window.dashboard) {
        setTimeout(() => {
            window.dashboard.loadEventLog();
        }, 100);
    }
}

// Initialize default tab on page load
document.addEventListener('DOMContentLoaded', () => {
    showTab('dashboard');
});