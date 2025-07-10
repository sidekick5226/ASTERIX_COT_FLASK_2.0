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
    if (tabName === 'dashboard' && window.dashboard && typeof window.dashboard.loadInitialData === 'function') {
        setTimeout(() => {
            window.dashboard.loadInitialData();
            if (window.mapManager && typeof window.mapManager.initMaps === 'function') {
                window.mapManager.initMaps();
            }
        }, 100);
    }
}

// Initialize default tab on page load
document.addEventListener('DOMContentLoaded', () => {
    showTab('dashboard');
});