/**
 * Trading Bot Dashboard - Core JavaScript
 * 
 * Handles core functionality, websocket connections, and shared utilities
 */

// Dashboard configuration
const DASHBOARD_CONFIG = {
    apiKey: localStorage.getItem('apiKey') || 'default_api_key',
    refreshInterval: 30000, // 30 seconds
    chartRefreshInterval: 60000, // 1 minute
    dateTimeFormat: {
        short: { hour: '2-digit', minute: '2-digit', second: '2-digit' },
        medium: { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' },
        full: { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' }
    }
};

// Global state
const appState = {
    connected: false,
    socket: null,
    lastUpdate: null,
    botStatus: {},
    parameters: {},
    profiles: {},
    activeProfile: '',
    marketRegime: 'UNKNOWN',
    refreshTimers: []
};

// Socket.IO connection
function initializeSocket() {
    try {
        appState.socket = io();
        
        // Connection events
        appState.socket.on('connect', () => {
            console.log('Socket.IO connected');
            updateConnectionStatus(true);
        });
        
        appState.socket.on('disconnect', () => {
            console.log('Socket.IO disconnected');
            updateConnectionStatus(false);
        });
        
        // Data events
        appState.socket.on('status', (data) => {
            console.log('Status update:', data);
        });
        
        appState.socket.on('parameter_update', (data) => {
            console.log('Parameter update:', data);
            showToast('Parameter Updated', `${data.parameter} set to ${data.value}`, 'info');
            
            // Update parameters if the handler exists
            if (typeof updateParameters === 'function') {
                fetchParameters();
            }
        });
        
        appState.socket.on('profile_change', (data) => {
            console.log('Profile change:', data);
            showToast('Profile Changed', `Active profile switched to ${data.profile}`, 'info');
            appState.activeProfile = data.profile;
            
            // Update if handler exists
            if (typeof updateProfiles === 'function') {
                fetchParameters();
            }
        });
        
        appState.socket.on('regime_change', (data) => {
            console.log('Regime change:', data);
            showToast('Market Regime Change', `New regime: ${data.regime}`, 'warning');
            updateRegimeBadge(data.regime);
        });
        
    } catch (error) {
        console.error('Socket initialization error:', error);
    }
}

// Update connection status UI
function updateConnectionStatus(connected) {
    appState.connected = connected;
    
    // Update status indicator
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('bot-status-text');
    const connStatusBadge = document.getElementById('connection-status');
    
    if (statusIndicator) {
        statusIndicator.className = connected ? 'status-circle connected' : 'status-circle disconnected';
    }
    
    if (statusText) {
        statusText.innerText = connected ? 'Connected' : 'Disconnected';
    }
    
    if (connStatusBadge) {
        connStatusBadge.className = connected ? 'badge bg-success' : 'badge bg-danger';
        connStatusBadge.innerText = connected ? 'Connected' : 'Disconnected';
    }
}

// Update market regime badge
function updateRegimeBadge(regime) {
    appState.marketRegime = regime;
    
    const regimeBadge = document.getElementById('market-regime-badge');
    if (regimeBadge) {
        regimeBadge.className = `badge regime-badge ${regime}`;
        
        let displayName = regime.replace('_', ' ');
        
        regimeBadge.innerText = displayName;
    }
    
    // Update regime text if present
    const regimeText = document.getElementById('market-regime');
    if (regimeText) {
        regimeText.innerText = regime.replace('_', ' ');
        regimeText.className = `display-6 mb-0 text-${getRegimeColorClass(regime)}`;
    }
}

// API request helper
async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        'X-API-Key': DASHBOARD_CONFIG.apiKey
    };
    
    const requestOptions = {
        ...options,
        headers: {
            ...headers,
            ...options.headers
        }
    };
    
    try {
        const response = await fetch(`/api/${endpoint}`, requestOptions);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `API request failed: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`API error (${endpoint}):`, error);
        showError(error.message);
        throw error;
    }
}

// Show toast notification
function showToast(title, message, type = 'info') {
    // Create container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast
    const toastId = 'toast-' + Date.now();
    const bgClass = `bg-${type === 'error' ? 'danger' : type}`;
    
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="5000">
            <div class="toast-header ${bgClass} text-white">
                <strong class="me-auto">${title}</strong>
                <small>${new Date().toLocaleTimeString()}</small>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Initialize and show toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Remove after hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Show error in modal
function showError(message) {
    const errorModal = document.getElementById('errorModal');
    const errorBody = document.getElementById('errorModalBody');
    
    if (errorModal && errorBody) {
        errorBody.innerText = message;
        const modal = new bootstrap.Modal(errorModal);
        modal.show();
    } else {
        alert(`Error: ${message}`);
    }
}

// Format datetime
function formatDateTime(timestamp, format = 'medium') {
    if (!timestamp) return '-';
    
    const date = new Date(timestamp);
    
    return date.toLocaleString(undefined, DASHBOARD_CONFIG.dateTimeFormat[format]);
}

// Format number with appropriate precision
function formatNumber(value, precision = 2) {
    if (value === undefined || value === null) return '-';
    
    return Number(value).toFixed(precision);
}

// Get color class for regime
function getRegimeColorClass(regime) {
    switch (regime) {
        case 'STRONG_UPTREND': return 'success';
        case 'WEAK_UPTREND': return 'success';
        case 'RANGING': return 'secondary';
        case 'WEAK_DOWNTREND': return 'warning';
        case 'STRONG_DOWNTREND': return 'danger';
        case 'HIGH_VOLATILITY': return 'purple';
        default: return 'secondary';
    }
}

// Format P&L value with color
function formatPnL(value) {
    if (value === undefined || value === null) return '-';
    
    const formattedValue = Number(value).toFixed(2);
    const valueClass = value >= 0 ? 'text-success' : 'text-danger';
    const prefix = value >= 0 ? '+' : '';
    
    return `<span class="${valueClass}">${prefix}${formattedValue}</span>`;
}

// Clear all refresh timers
function clearRefreshTimers() {
    appState.refreshTimers.forEach(timer => clearInterval(timer));
    appState.refreshTimers = [];
}

// Initialize dashboard
function initializeDashboard() {
    // Initialize Socket.IO
    initializeSocket();
    
    // Set up refresh timer for status checks
    const statusTimer = setInterval(() => {
        fetchDashboardStatus();
    }, DASHBOARD_CONFIG.refreshInterval);
    
    appState.refreshTimers.push(statusTimer);
    
    // Initial status fetch
    fetchDashboardStatus();
}

// Fetch dashboard status
async function fetchDashboardStatus() {
    try {
        const statusData = await apiRequest('status');
        
        appState.lastUpdate = new Date();
        appState.botStatus = statusData.bot || {};
        
        // Update market regime if available
        if (appState.botStatus.market_regime) {
            updateRegimeBadge(appState.botStatus.market_regime);
        }
        
        // Update connection status
        updateConnectionStatus(appState.botStatus.connected === true);
        
        // Uptime formatting if available
        if (appState.botStatus.uptime && document.getElementById('bot-uptime')) {
            const uptime = appState.botStatus.uptime;
            const days = Math.floor(uptime / (24 * 3600));
            const hours = Math.floor((uptime % (24 * 3600)) / 3600);
            const minutes = Math.floor((uptime % 3600) / 60);
            
            let uptimeText = 'Uptime: ';
            if (days > 0) uptimeText += `${days}d `;
            uptimeText += `${hours}h ${minutes}m`;
            
            document.getElementById('bot-uptime').innerText = uptimeText;
        }
        
        return statusData;
    } catch (error) {
        console.error('Error fetching dashboard status:', error);
        updateConnectionStatus(false);
    }
}

// Document ready handler
document.addEventListener('DOMContentLoaded', () => {
    initializeDashboard();
});
