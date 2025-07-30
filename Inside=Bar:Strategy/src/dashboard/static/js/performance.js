/**
 * Performance Analytics and Playbook Management
 * -------------------------------------------
 * This module provides functionality for:
 * - Regime performance visualization and analysis
 * - Playbook generation and management
 * - Pattern recognition and intelligent insights
 * - Real-time regime monitoring and matching
 * - Telegram alerts for regime insights
 * 
 * Dependencies:
 * - performance_render.js - UI rendering functions
 * - performance_core.js - Core utilities and formatting
 * - performance_api.js - API service functions
 * - telegram_alerts.js - Telegram alert functions
 */

// Dashboard Configuration and Globals
const DASHBOARD_CONFIG = {
    apiUrl: window.location.protocol + '//' + window.location.host,
    socketUrl: window.location.protocol + '//' + window.location.host,
    refreshInterval: 30000, // 30 seconds
    maxDisplayEntries: 10,
    chartColors: {
        strongUptrend: 'rgba(16, 185, 129, 0.7)',
        strongDowntrend: 'rgba(239, 68, 68, 0.7)',
        ranging: 'rgba(59, 130, 246, 0.7)',
        highVolatility: 'rgba(245, 158, 11, 0.7)',
        transition: 'rgba(139, 92, 246, 0.7)'
    },
    telegram: {
        enableAlerts: true,
        confidenceThreshold: 0.80, // Send alert when confidence exceeds 80%
        highPerformerAlerts: true,
        playbookMatchAlerts: true
    }
};

// Store global state
const state = {
    performanceEntries: [],
    topPerformers: [],
    playbooks: [],
    currentRegime: null,
    matchingPlaybooks: [],
    currentPage: 1,
    pageSize: 10,
    socket: null,
    charts: {},
    selectedPerformanceEntry: null,
    currentFilters: {
        regimeType: '',
        search: '',
        activeOnly: true
    },
    sortBy: 'timestamp',
    sortDirection: 'desc',
    telegramAlertHistory: {} // Prevent duplicate alerts
};

// Initialize on document ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Telegram settings first to ensure they're loaded
    initTelegramSettings();
    
    initializeSocketConnection();
    setupEventListeners();
    loadPerformanceData();
    loadTopPerformers();
    loadPlaybooks();
    loadCurrentRegimeStatus();
    setupCharts();
    
    // Set up periodic refreshes
    setInterval(() => {
        loadCurrentRegimeStatus();
        loadTopPerformers();
    }, DASHBOARD_CONFIG.refreshInterval);
});

/**
 * Initialize Socket.IO connection for real-time updates
 */
function initializeSocketConnection() {
    try {
        state.socket = io(DASHBOARD_CONFIG.socketUrl);
        
        state.socket.on('connect', () => {
            console.log('Socket connected');
            showToast('Socket.IO connection established', 'success');
        });
        
        state.socket.on('disconnect', () => {
            console.log('Socket disconnected');
            showToast('Socket.IO connection lost. Reconnecting...', 'warning');
        });
        
        // Listen for regime change events
        state.socket.on('regime_change', (data) => {
            console.log('Regime change detected:', data);
            const confidence = (data.confidence * 100).toFixed(0);
            
            // Update UI
            showToast(`Regime changed to ${data.regime} with ${confidence}% confidence`, 'info');
            loadCurrentRegimeStatus();
            
            // Send Telegram alert if confidence exceeds threshold
            if (DASHBOARD_CONFIG.telegram.enableAlerts && 
                data.confidence >= DASHBOARD_CONFIG.telegram.confidenceThreshold) {
                // Use our new telegram_alerts.js module
                sendTelegramAlert({
                    type: 'regime_change',
                    title: '🔄 Regime Change Detected',
                    message: `New regime: ${data.regime} | Confidence: ${confidence}%`,
                    data: data
                });
            }
        });
        
        // Listen for new performance entry events
        state.socket.on('new_performance_entry', (data) => {
            console.log('New performance entry:', data);
            
            // Update UI for high performers
            if (data.is_high_performer) {
                showToast(`New high-performing ${data.regime_type} regime detected!`, 'success');
                
                // Send Telegram alert for high performers
                if (DASHBOARD_CONFIG.telegram.enableAlerts && 
                    DASHBOARD_CONFIG.telegram.highPerformerAlerts) {
                    const roi = data.performance?.roi_pct ? 
                        (data.performance.roi_pct > 0 ? '+' : '') + 
                        data.performance.roi_pct.toFixed(2) + '%' : 'N/A';
                        
                    // Use our new telegram_alerts.js module
                    sendTelegramAlert({
                        type: 'high_performer',
                        title: '🔥 Top-Performing Regime Detected',
                        message: `Regime: ${data.regime_type} | ROI: ${roi} | Confidence: ${(data.confidence * 100).toFixed(0)}%`,
                        data: data
                    });
                }
            }
            
            // Refresh data
            loadPerformanceData();
            loadTopPerformers();
        });
        
        // Listen for playbook match events
        state.socket.on('playbook_match', (data) => {
            console.log('Playbook match detected:', data);
            
            // Update UI
            showToast(`Playbook "${data.name}" matched current regime with ${(data.match_confidence * 100).toFixed(0)}% confidence`, 'success');
            
            // Send Telegram alert
            if (DASHBOARD_CONFIG.telegram.enableAlerts && 
                DASHBOARD_CONFIG.telegram.playbookMatchAlerts) {
                // Use our new telegram_alerts.js module
                sendTelegramAlert({
                    type: 'playbook_match',
                    title: '💡 Playbook Match Triggered',
                    message: `"${data.name}" | Confidence: ${(data.match_confidence * 100).toFixed(0)}% | Regime: ${state.currentRegime?.regime || 'Unknown'}`,
                    data: data
                });
            }
            
            // Reload matching playbooks
            loadMatchingPlaybooks();
        });
        
        // Listen for new playbook events
        state.socket.on('new_playbook', (data) => {
            console.log('New playbook created:', data);
            showToast(`New playbook "${data.name}" created!`, 'success');
            loadPlaybooks();
        });
    } catch (error) {
        console.error('Error initializing socket:', error);
        showToast('Failed to establish Socket.IO connection', 'error');
    }
}

/**
 * Set up event listeners for user interactions
 */
function setupEventListeners() {
    // Tab switching
    const tabs = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', (e) => {
            const targetId = e.target.getAttribute('href');
            if (targetId === '#performance-analytics-tab') {
                updateTimelineChart();
                updatePerformanceCharts();
            }
        });
    });
    
    // Refresh button
    document.getElementById('refresh-performance-data').addEventListener('click', () => {
        loadPerformanceData();
        loadTopPerformers();
        loadPlaybooks();
        loadCurrentRegimeStatus();
    });
    
    // Regime filter dropdown
    document.getElementById('regime-filter').addEventListener('change', (e) => {
        state.currentFilters.regimeType = e.target.value;
        loadPerformanceData();
    });
    
    // Playbook search
    document.getElementById('playbook-search').addEventListener('input', debounce((e) => {
        state.currentFilters.search = e.target.value.toLowerCase();
        renderPlaybooks();
    }, 300));
    
    // Clear search button
    document.getElementById('clear-search').addEventListener('click', () => {
        document.getElementById('playbook-search').value = '';
        state.currentFilters.search = '';
        renderPlaybooks();
    });
    
    // Active only toggle
    document.getElementById('show-active-only').addEventListener('change', (e) => {
        state.currentFilters.activeOnly = e.target.checked;
        renderPlaybooks();
    });
    
    // Create playbook modal
    document.getElementById('playbook-confidence-threshold').addEventListener('input', (e) => {
        document.getElementById('confidence-value').textContent = `${e.target.value}%`;
    });
    
    // Save new playbook button
    document.getElementById('save-playbook-btn').addEventListener('click', () => {
        const playbookData = {
            name: document.getElementById('playbook-name').value,
            description: document.getElementById('playbook-description').value,
            regime_type: document.getElementById('playbook-regime-type').value,
            confidence_threshold: parseInt(document.getElementById('playbook-confidence-threshold').value) / 100,
            is_active: document.getElementById('playbook-is-active').checked,
            strategy: {
                entry_conditions: document.getElementById('playbook-entry-conditions').value,
                exit_conditions: document.getElementById('playbook-exit-conditions').value,
                stop_loss_strategy: document.getElementById('playbook-stop-loss').value,
                take_profit_strategy: document.getElementById('playbook-take-profit').value,
                position_sizing: document.getElementById('playbook-position-sizing').value,
                parameter_settings: parseParameterSettings(document.getElementById('playbook-parameters').value)
            }
        };
        
        createPlaybook(playbookData);
    });
    
    // Apply playbook button
    document.getElementById('apply-playbook-btn').addEventListener('click', () => {
        if (state.selectedPlaybook) {
            applyPlaybook(state.selectedPlaybook.id);
        }
    });
    
    // Create playbook from performance button
    document.getElementById('create-playbook-from-performance').addEventListener('click', () => {
        if (state.selectedPerformanceEntry) {
            createPlaybookFromPerformance(state.selectedPerformanceEntry.id);
        }
    });
    
    // Export buttons
    document.getElementById('export-performance-csv').addEventListener('click', exportPerformanceData);
    document.getElementById('export-playbooks-json').addEventListener('click', exportPlaybooks);
    
    // Import playbooks button
    document.getElementById('import-playbooks').addEventListener('click', () => {
        document.getElementById('import-file').click();
    });
    
    document.getElementById('import-file').addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            importPlaybooks(e.target.files[0]);
        }
    });
    
    // Telegram settings
    document.getElementById('telegram-alerts-toggle').addEventListener('change', (e) => {
        DASHBOARD_CONFIG.telegram.enableAlerts = e.target.checked;
        localStorage.setItem('telegram_alerts_enabled', e.target.checked);
    });
    
    // Set initial value from localStorage if exists
    const savedTelegramSetting = localStorage.getItem('telegram_alerts_enabled');
    if (savedTelegramSetting !== null) {
        const enabled = savedTelegramSetting === 'true';
        document.getElementById('telegram-alerts-toggle').checked = enabled;
        DASHBOARD_CONFIG.telegram.enableAlerts = enabled;
    }
    
    // Timeline zoom controls
    document.getElementById('timelineZoomIn').addEventListener('click', () => {
        if (state.charts.timeline) {
            const chart = state.charts.timeline;
            chart.zoom(1.1);
        }
    });
    
    document.getElementById('timelineZoomOut').addEventListener('click', () => {
        if (state.charts.timeline) {
            const chart = state.charts.timeline;
            chart.zoom(0.9);
        }
    });
    
    document.getElementById('timelineReset').addEventListener('click', () => {
        if (state.charts.timeline) {
            const chart = state.charts.timeline;
            chart.resetZoom();
        }
    });
    
    // Take regime snapshot button
    document.getElementById('take-regime-snapshot').addEventListener('click', takeRegimeSnapshot);
}

/**
 * Load performance data from API
 */
function loadPerformanceData() {
    const url = new URL(`${DASHBOARD_CONFIG.apiUrl}/api/regime/performance-log`);
    
    // Add query parameters
    if (state.currentFilters.regimeType) {
        url.searchParams.append('regime', state.currentFilters.regimeType);
    }
    
    showLoading('Loading performance data...');
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                state.performanceEntries = data.performance_entries;
                updatePerformanceStats();
                renderPerformanceTable();
                updateTimelineChart();
                updatePerformanceCharts();
            } else {
                showToast(`Error: ${data.error}`, 'error');
            }
            hideLoading();
        })
        .catch(error => {
            console.error('Error loading performance data:', error);
            showToast('Failed to load performance data', 'error');
            hideLoading();
        });
}

/**
 * Load top performing regimes
 */
function loadTopPerformers() {
    fetch(`${DASHBOARD_CONFIG.apiUrl}/api/regime/top-performers?limit=10`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                state.topPerformers = data.top_performers;
                renderTopPerformers();
            } else {
                showToast(`Error: ${data.error}`, 'error');
            }
        })
        .catch(error => {
            console.error('Error loading top performers:', error);
            showToast('Failed to load top performers', 'error');
        });
}

/**
 * Load available playbooks
 */
function loadPlaybooks() {
    const url = new URL(`${DASHBOARD_CONFIG.apiUrl}/api/regime/playbooks`);
    url.searchParams.append('active_only', state.currentFilters.activeOnly);
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                state.playbooks = data.playbooks;
                renderPlaybooks();
            } else {
                showToast(`Error: ${data.error}`, 'error');
            }
        })
        .catch(error => {
            console.error('Error loading playbooks:', error);
            showToast('Failed to load playbooks', 'error');
        });
}

/**
 * Load current regime status and matching playbooks
 */
function loadCurrentRegimeStatus() {
    fetch(`${DASHBOARD_CONFIG.apiUrl}/api/regime/current`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                state.currentRegime = data.regime;
                renderCurrentRegimeStatus();
                
                // Load matching playbooks
                return fetch(`${DASHBOARD_CONFIG.apiUrl}/api/regime/playbooks/match-current`);
            } else {
                showToast(`Error: ${data.error}`, 'error');
                throw new Error(data.error);
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                state.matchingPlaybooks = data.matching_playbooks;
                renderMatchingPlaybooks();
            } else {
                showToast(`Error: ${data.error}`, 'error');
            }
        })
        .catch(error => {
            console.error('Error loading current regime status:', error);
            showToast('Failed to load current regime status', 'error');
        });
}
