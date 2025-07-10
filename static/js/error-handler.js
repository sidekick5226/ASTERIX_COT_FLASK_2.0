// Global error handler to prevent console spam and improve debugging
class ErrorHandler {
    constructor() {
        this.errorCounts = new Map();
        this.lastErrorTime = new Map();
        this.maxErrorsPerType = 3;
        this.errorThrottleTime = 10000; // 10 seconds
        
        this.setupGlobalErrorHandling();
    }
    
    setupGlobalErrorHandling() {
        // Handle uncaught JavaScript errors
        window.addEventListener('error', (event) => {
            this.handleError('JavaScript Error', event.error || event.message);
        });
        
        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError('Promise Rejection', event.reason);
        });
        
        // Override console.error to throttle repeated errors
        const originalConsoleError = console.error;
        console.error = (...args) => {
            const errorKey = args.join(' ');
            if (this.shouldLogError(errorKey)) {
                originalConsoleError.apply(console, args);
            }
        };
    }
    
    handleError(type, error) {
        const errorKey = `${type}: ${error}`;
        
        if (this.shouldLogError(errorKey)) {
            console.error(`[${type}]`, error);
            
            // Don't show error popups for connection errors to prevent spam
            if (!errorKey.includes('Connection error') && !errorKey.includes('WebSocket')) {
                this.showErrorNotification(error);
            }
        }
    }
    
    shouldLogError(errorKey) {
        const now = Date.now();
        const lastTime = this.lastErrorTime.get(errorKey) || 0;
        const count = this.errorCounts.get(errorKey) || 0;
        
        // Reset count if enough time has passed
        if (now - lastTime > this.errorThrottleTime) {
            this.errorCounts.set(errorKey, 0);
        }
        
        // Check if we should log this error
        if (count < this.maxErrorsPerType) {
            this.errorCounts.set(errorKey, count + 1);
            this.lastErrorTime.set(errorKey, now);
            return true;
        }
        
        return false;
    }
    
    showErrorNotification(error) {
        // Only show critical errors, not connection issues
        if (typeof error === 'string' && (
            error.includes('Connection') || 
            error.includes('WebSocket') || 
            error.includes('reconnect')
        )) {
            return;
        }
        
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-red-600 text-white px-4 py-2 rounded shadow-lg z-50 max-w-sm';
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-exclamation-triangle mr-2"></i>
                <span class="text-sm">${String(error).substring(0, 100)}</span>
                <button class="ml-2 text-red-200 hover:text-white" onclick="this.parentNode.parentNode.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
}

// Initialize error handler
if (!window.errorHandler) {
    window.errorHandler = new ErrorHandler();
}