/**
 * Trading Bot Dashboard - Market Page JS
 * 
 * Handles market regime visualization, timeline interactions, performance analytics, and manual regime override
 */

// Chart references
let marketIndicatorsChart = null;
let regimeDistributionChart = null;
let performanceComparisonChart = null;

// Store regime data
let regimeHistory = [];
let regimeStats = {};
let availableProfiles = [];
let performanceData = {};
let currentRegime = {};

// Timeline interaction variables
let timelineScale = 1;
let timelineTranslateX = 0;
let isDragging = false;
let dragStartX = 0;
let startTranslateX = 0;

// Socket.io connection for real-time updates
let socket = null;

// Debounce timers for functions
let debounceTimers = {};

// Flag to track if initial regime tooltips have been displayed
let hasDisplayedInitialRegimeTooltips = false;

// Debounce function for handling UI events efficiently
function debounce(func, wait, immediate) {
    return function() {
        const context = this;
        const args = arguments;
        const funcId = func.toString().slice(0, 50);
        
        clearTimeout(debounceTimers[funcId]);
        
        debounceTimers[funcId] = setTimeout(function() {
            debounceTimers[funcId] = null;
            if (!immediate) func.apply(context, args);
        }, wait);
        
        if (immediate && !debounceTimers[funcId]) {
            func.apply(context, args);
        }
    };
}

// Enhanced error handling and logging
function handleError(error, context = '', silent = false) {
    // Log error with context
    console.error(`Error in ${context}:`, error);
    
    // Send to analytics if available
    if (typeof sendAnalyticsEvent === 'function') {
        sendAnalyticsEvent('error', {
            context: context,
            message: error.message || String(error),
            stack: error.stack,
            timestamp: new Date().toISOString()
        });
    }
    
    // Show UI alert if not silent
    if (!silent) {
        showAlert('danger', `Error in ${context}: ${error.message || 'Unknown error'}`);
    }
    
    // Return for promise catching
    return null;
}

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Add event listeners
    document.getElementById('refresh-market-btn').addEventListener('click', fetchMarketRegime);
    document.getElementById('history-timeframe').addEventListener('change', fetchRegimeHistory);
    document.getElementById('download-regime-data').addEventListener('click', downloadRegimeHistory);
    document.getElementById('save-detection-settings').addEventListener('click', saveDetectionSettings);
    document.getElementById('refresh-signals-btn').addEventListener('click', fetchActiveSignals);
    
    // Strategy toggle listeners
    const strategyToggles = document.querySelectorAll('.strategy-toggle');
    strategyToggles.forEach(toggle => {
        toggle.addEventListener('change', handleStrategyToggle);
    });
    
    // Timeline controls
    document.getElementById('timeline-zoom-in').addEventListener('click', () => zoomTimeline(1.2));
    document.getElementById('timeline-zoom-out').addEventListener('click', () => zoomTimeline(0.8));
    document.getElementById('timeline-reset').addEventListener('click', resetTimelineView);
    
    // Performance timeframe control
    document.getElementById('performance-timeframe').addEventListener('change', fetchPerformanceData);
    
    // Manual override controls
    document.getElementById('manual-override-toggle').addEventListener('change', toggleManualOverrideControls);
    document.getElementById('apply-manual-override').addEventListener('click', applyManualOverride);
    
    // View regime details button
    document.getElementById('view-regime-details-btn').addEventListener('click', () => showCurrentRegimeDetails());
    
    // Indicator chart filters
    const indicatorButtons = document.querySelectorAll('[data-indicator]');
    indicatorButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            // Toggle active state
            indicatorButtons.forEach(btn => btn.classList.remove('active'));
            e.target.classList.add('active');
            
            // Filter chart data
            filterIndicatorChart(e.target.getAttribute('data-indicator'));
        });
    });
    
    // Transition sensitivity slider
    document.getElementById('transition-sensitivity').addEventListener('input', (e) => {
        document.getElementById('transition-sensitivity-value').innerText = e.target.value;
    });
    
    // Range input value displays
    document.getElementById('adx-threshold').addEventListener('input', (e) => {
        document.getElementById('adx-threshold-value').innerText = e.target.value;
    });
    
    document.getElementById('volatility-threshold').addEventListener('input', (e) => {
        document.getElementById('volatility-threshold-value').innerText = e.target.value;
    });
    
    // Setup timeline drag/pan functionality
    setupTimelineInteractions();
    
    // Initialize socket connection for real-time updates
    initSocketConnection();
    
    // Fetch initial data
    fetchMarketRegime();
    fetchRegimeHistory();
    fetchAvailableProfiles();
    fetchPerformanceData();
    fetchActiveSignals();
    fetchSignalCounts();
    
    // Set refresh intervals
    setInterval(fetchMarketRegime, DASHBOARD_CONFIG.refreshInterval);
    setInterval(fetchActiveSignals, DASHBOARD_CONFIG.refreshInterval * 2);
    setInterval(fetchSignalCounts, DASHBOARD_CONFIG.refreshInterval * 5);
});

// Fetch current market regime
async function fetchMarketRegime() {
    try {
        const data = await apiRequest('market/regime');
        
        if (data.current_regime) {
            updateCurrentRegimeDisplay(data.current_regime);
        }
        
        return data;
    } catch (error) {
        console.error('Error fetching market regime:', error);
    }
}

// Setup timeline interactions (drag, pan, zoom)
function setupTimelineInteractions() {
    const timeline = document.querySelector('.regime-timeline');
    const container = document.querySelector('.timeline-container');
    
    if (!timeline || !container) return;
    
    // Mouse down event to start dragging
    timeline.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return; // Only left mouse button
        
        isDragging = true;
        dragStartX = e.clientX;
        startTranslateX = timelineTranslateX;
        
        timeline.style.cursor = 'grabbing';
        e.preventDefault();
    });
    
    // Mouse move event to drag/pan
    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        
        const dx = e.clientX - dragStartX;
        timelineTranslateX = startTranslateX + dx;
        
        applyTimelineTransform();
    });
    
    // Mouse up event to stop dragging
    document.addEventListener('mouseup', () => {
        if (!isDragging) return;
        
        isDragging = false;
        timeline.style.cursor = 'grab';
    });
    
    // Mouse leave event to stop dragging
    container.addEventListener('mouseleave', () => {
        if (!isDragging) return;
        
        isDragging = false;
        timeline.style.cursor = 'grab';
    });
    
    // Setup hover effects for tooltips
    setupTimelineTooltips();
    
    // Initial cursor style
    timeline.style.cursor = 'grab';
}

// Zoom timeline
function zoomTimeline(factor) {
    const oldScale = timelineScale;
    timelineScale *= factor;
    
    // Limit scale to sensible values
    timelineScale = Math.max(0.5, Math.min(5, timelineScale));
    
    // Adjust translation to keep center point
    if (timelineScale !== oldScale) {
        const timeline = document.querySelector('.regime-timeline');
        if (timeline) {
            const containerWidth = timeline.parentElement.clientWidth;
            const centerPoint = containerWidth / 2 - timelineTranslateX;
            const newCenterPoint = centerPoint * (timelineScale / oldScale);
            timelineTranslateX -= (newCenterPoint - centerPoint);
        }
    }
    
    applyTimelineTransform();
}

// Apply timeline transformation
function applyTimelineTransform() {
    const timeline = document.querySelector('.regime-timeline');
    if (!timeline) return;
    
    timeline.style.transform = `translateX(${timelineTranslateX}px) scale(${timelineScale})`;
    timeline.style.transformOrigin = 'left center';
}

// Reset timeline view
function resetTimelineView() {
    timelineScale = 1;
    timelineTranslateX = 0;
    applyTimelineTransform();
}

// Setup tooltip functionality for timeline
function setupTimelineTooltips() {
    const timeline = document.querySelector('.regime-timeline');
    const tooltip = document.getElementById('timeline-tooltip');
    
    if (!timeline || !tooltip) return;
    
    // Add mouseover event for regime blocks
    timeline.addEventListener('mouseover', (e) => {
        const target = e.target;
        
        // Check if we're hovering over a regime block
        if (target.classList.contains('regime-block')) {
            const index = parseInt(target.dataset.index);
            if (isNaN(index) || !regimeHistory[index]) return;
            
            const regime = regimeHistory[index];
            const tooltipContent = createRegimeTooltipContent(regime);
            
            // Position tooltip
            const rect = target.getBoundingClientRect();
            const timelineRect = timeline.getBoundingClientRect();
            
            tooltip.innerHTML = tooltipContent;
            tooltip.style.display = 'block';
            tooltip.style.left = `${rect.left + rect.width/2 - tooltip.offsetWidth/2}px`;
            tooltip.style.top = `${rect.top - tooltip.offsetHeight - 10}px`;
            
            // Handle edge cases - keep tooltip inside viewport
            const tooltipRect = tooltip.getBoundingClientRect();
            if (tooltipRect.left < 10) {
                tooltip.style.left = '10px';
            } else if (tooltipRect.right > window.innerWidth - 10) {
                tooltip.style.left = `${window.innerWidth - tooltip.offsetWidth - 10}px`;
            }
        }
    });
    
    // Hide tooltip when leaving timeline or hovering non-regime-block
    timeline.addEventListener('mouseout', (e) => {
        if (!e.relatedTarget || !e.relatedTarget.closest('.regime-timeline') || 
            !e.relatedTarget.classList.contains('regime-block')) {
            tooltip.style.display = 'none';
        }
    });
}

// Create tooltip content for regime block
function createRegimeTooltipContent(regime) {
    const date = new Date(regime.timestamp);
    const formattedDateTime = formatDateTime(date, 'full');
    
    // Format confidence as percentage
    const confidence = (regime.confidence * 100).toFixed(1) + '%';
    
    // Format duration if available
    let duration = 'Unknown';
    if (regime.duration_minutes) {
        if (regime.duration_minutes < 60) {
            duration = `${regime.duration_minutes} min`;
        } else {
            const hours = Math.floor(regime.duration_minutes / 60);
            const mins = regime.duration_minutes % 60;
            duration = `${hours}h ${mins}m`;
        }
    }
    
    let metrics = '';
    if (regime.metrics) {
        metrics = `
            <div class="mt-2 small">
                <div><strong>ADX:</strong> ${regime.metrics.adx?.toFixed(1) || '--'}</div>
                <div><strong>Volatility:</strong> ${regime.metrics.volatility?.toFixed(2) || '--'}</div>
                <div><strong>Trend:</strong> ${getTrendDirectionText(regime.metrics.trend_direction)}</div>
            </div>
        `;
    }
    
    return `
        <div>
            <div class="fw-bold">${regime.regime.replace('_', ' ')}</div>
            <div class="small text-white-50">${formattedDateTime}</div>
            <div class="d-flex justify-content-between small mt-1">
                <span>Confidence:</span>
                <span class="ms-2 fw-bold">${confidence}</span>
            </div>
            <div class="d-flex justify-content-between small">
                <span>Duration:</span>
                <span class="ms-2 fw-bold">${duration}</span>
            </div>
            ${regime.active_profile ? `<div class="small"><strong>Profile:</strong> ${regime.active_profile}</div>` : ''}
            ${metrics}
        </div>
    `;
}

// Initialize Socket.IO connection for real-time updates
function initSocketConnection() {
    // Create socket connection if supported
    if (typeof io !== 'undefined') {
        socket = io(DASHBOARD_CONFIG.socketUrl, {
            transports: ['websocket'],
            upgrade: false
        });
        
        // Listen for regime change events
        socket.on('regime_changed', (data) => {
            console.log('Regime change event received:', data);
            fetchMarketRegime(); // Refresh current regime display
            
            // Add to history without fetching all history again
            if (data.new_regime && regimeHistory.length > 0) {
                regimeHistory.unshift(data.new_regime); // Add to beginning of history
                updateRegimeTimeline(regimeHistory);
                
                // Show toast notification
                showRegimeChangeNotification(data.new_regime);
            } else {
                // Full refresh if needed
                fetchRegimeHistory();
            }
        });
        
        // Listen for manual override events
        socket.on('regime_override_changed', (data) => {
            console.log('Manual override event received:', data);
            updateManualOverrideDisplay(data.manual_override, data.active_profile);
            fetchMarketRegime(); // Refresh current regime display
        });
        
        // Connection status events
        socket.on('connect', () => {
            console.log('Socket connected');
            document.getElementById('live-status-indicator').classList.add('bg-success');
            document.getElementById('live-status-indicator').classList.remove('bg-info', 'bg-danger');
        });
        
        socket.on('disconnect', () => {
            console.log('Socket disconnected');
            document.getElementById('live-status-indicator').classList.add('bg-danger');
            document.getElementById('live-status-indicator').classList.remove('bg-success', 'bg-info');
        });
    } else {
        console.warn('Socket.IO not available. Live updates disabled.');
    }
}

// Show regime change notification
function showRegimeChangeNotification(regime) {
    // Create toast notification for regime change
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toastId = `regime-toast-${Date.now()}`;
    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body ${regime.regime} text-white">
                    <strong>Regime Change:</strong> ${regime.regime.replace('_', ' ')} detected
                    <div class="small">${formatDateTime(new Date(regime.timestamp))}</div>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    // Initialize and show the toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 5000
    });
    toast.show();
    
    // Return the element for potential use
    return toastElement;
}

// Create toast container if it doesn't exist
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1060';
    document.body.appendChild(container);
    return container;
}

// Fetch available profiles for manual override
async function fetchAvailableProfiles() {
    try {
        const data = await apiRequest('parameters/profiles');
        
        if (data && data.profiles) {
            availableProfiles = data.profiles;
            populateProfileDropdown(data.profiles);
            return data.profiles;
        }
    } catch (error) {
        console.error('Error fetching available profiles:', error);
    }
    
    return [];
}

// Populate profile dropdown for manual override
function populateProfileDropdown(profiles) {
    const select = document.getElementById('manual-profile-select');
    if (!select) return;
    
    // Clear existing options except first
    while (select.options.length > 1) {
        select.remove(1);
    }
    
    // Add profile options
    profiles.forEach(profile => {
        const option = document.createElement('option');
        option.value = profile.name;
        option.textContent = profile.name;
        select.appendChild(option);
    });
}

// Toggle manual override controls visibility
function toggleManualOverrideControls() {
    const toggle = document.getElementById('manual-override-toggle');
    const controls = document.getElementById('manual-override-controls');
    
    if (toggle && controls) {
        if (toggle.checked) {
            controls.classList.remove('d-none');
        } else {
            controls.classList.add('d-none');
            
            // If unchecking, disable any active override
            disableManualOverride();
        }
    }
}

// Apply manual regime override
async function applyManualOverride() {
    const toggle = document.getElementById('manual-override-toggle');
    const profileSelect = document.getElementById('manual-profile-select');
    
    if (!toggle || !profileSelect) return;
    
    // Verify toggle is checked and profile is selected
    if (!toggle.checked) {
        showAlert('warning', 'Manual override is not enabled. Please enable it first.');
        return;
    }
    
    const selectedProfile = profileSelect.value;
    if (!selectedProfile) {
        showAlert('warning', 'Please select a parameter profile to apply.');
        return;
    }
    
    try {
        // Show loading state
        const applyButton = document.getElementById('apply-manual-override');
        const originalText = applyButton.innerHTML;
        applyButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Applying...';
        applyButton.disabled = true;
        
        // Send API request to enable override with selected profile
        const response = await apiRequest('market/regime/override', {
            method: 'POST',
            body: JSON.stringify({
                manual_override: true,
                profile_name: selectedProfile
            })
        });
        
        // Handle response
        if (response && response.success) {
            showAlert('success', `Manual override enabled with profile: ${selectedProfile}`);
            fetchMarketRegime(); // Refresh current regime display
        } else {
            showAlert('danger', 'Failed to apply manual override: ' + (response?.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error applying manual override:', error);
        showAlert('danger', 'Error applying manual override: ' + error.message);
    } finally {
        // Restore button state
        const applyButton = document.getElementById('apply-manual-override');
        if (applyButton) {
            applyButton.innerHTML = '<i class="bi bi-check-circle"></i> Apply Override';
            applyButton.disabled = false;
        }
    }
}

// Disable manual override
async function disableManualOverride() {
    try {
        const response = await apiRequest('market/regime/override', {
            method: 'POST',
            body: JSON.stringify({
                manual_override: false
            })
        });
        
        if (response && response.success) {
            console.log('Manual override disabled');
            fetchMarketRegime(); // Refresh current regime display
        } else {
            console.error('Failed to disable manual override:', response?.message);
        }
    } catch (error) {
        console.error('Error disabling manual override:', error);
    }
}

// Update manual override display based on regime data
function updateManualOverrideDisplay(isOverrideActive, activeProfile) {
    const toggle = document.getElementById('manual-override-toggle');
    const controls = document.getElementById('manual-override-controls');
    const profileSelect = document.getElementById('manual-profile-select');
    
    if (toggle && controls && profileSelect) {
        // Set toggle state without triggering event
        toggle.checked = isOverrideActive;
        
        // Show/hide controls
        if (isOverrideActive) {
            controls.classList.remove('d-none');
            
            // Set selected profile
            if (activeProfile) {
                for (let i = 0; i < profileSelect.options.length; i++) {
                    if (profileSelect.options[i].value === activeProfile) {
                        profileSelect.selectedIndex = i;
                        break;
                    }
                }
            }
        } else {
            controls.classList.add('d-none');
        }
    }
}

// Show current regime details in modal
function showCurrentRegimeDetails() {
    // Fetch latest regime data to ensure we have the most current data
    fetchMarketRegime().then(data => {
        if (data && data.current_regime) {
            showRegimeDetails(data.current_regime);
        } else {
            showAlert('info', 'No regime data available to display');
        }
    }).catch(error => {
        console.error('Error fetching regime details:', error);
        showAlert('danger', 'Error fetching regime details');
    });
}

// Show alert message
function showAlert(type, message) {
    const alertContainer = document.getElementById('alert-container') || createAlertContainer();
    
    const alertId = `alert-${Date.now()}`;
    const alertHTML = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    alertContainer.insertAdjacentHTML('beforeend', alertHTML);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            const bsAlert = bootstrap.Alert.getInstance(alertElement);
            if (bsAlert) {
                bsAlert.close();
            } else {
                alertElement.remove();
            }
        }
    }, 5000);
}

// Create alert container if it doesn't exist
function createAlertContainer() {
    const container = document.createElement('div');
    container.id = 'alert-container';
    container.className = 'position-fixed top-0 start-50 translate-middle-x pt-3';
    container.style.zIndex = '1050';
    container.style.maxWidth = '500px';
    container.style.width = '90%';
    document.body.appendChild(container);
    return container;
}

// Update current regime display
function updateCurrentRegimeDisplay(regimeData) {
    const regimeElement = document.getElementById('current-regime');
    const confidenceElement = document.getElementById('regime-confidence');
    const volatilityElement = document.getElementById('volatility-value');
    const adxElement = document.getElementById('adx-value');
    const trendDirectionElement = document.getElementById('trend-direction');
    const profileElement = document.getElementById('regime-profile');
    const detectedTimeElement = document.getElementById('regime-detected-time');
    
    // Update manual override display if present in data
    if (regimeData.manual_override !== undefined) {
        updateManualOverrideDisplay(regimeData.manual_override, regimeData.active_profile);
    }
    
    // Update regime badge
    if (regimeElement) {
        regimeElement.className = `regime-badge ${regimeData.regime}`;
        regimeElement.innerText = regimeData.regime.replace('_', ' ');
    }
    
    // Update confidence
    if (confidenceElement && regimeData.confidence !== undefined) {
        confidenceElement.innerText = `Confidence: ${(regimeData.confidence * 100).toFixed(1)}%`;
    }
    
    // Update metrics
    if (volatilityElement && regimeData.metrics && regimeData.metrics.volatility !== undefined) {
        volatilityElement.innerText = regimeData.metrics.volatility.toFixed(2);
        
        // Color based on value
        if (regimeData.metrics.volatility > 2.0) {
            volatilityElement.className = 'text-danger market-metric';
        } else if (regimeData.metrics.volatility > 1.5) {
            volatilityElement.className = 'text-warning market-metric';
        } else {
            volatilityElement.className = 'text-success market-metric';
        }
    }
    
    if (adxElement && regimeData.metrics && regimeData.metrics.adx !== undefined) {
        adxElement.innerText = Math.round(regimeData.metrics.adx);
        
        // Color based on value
        if (regimeData.metrics.adx > 30) {
            adxElement.className = 'text-success market-metric';
        } else if (regimeData.metrics.adx > 20) {
            adxElement.className = 'text-warning market-metric';
        } else {
            adxElement.className = 'text-secondary market-metric';
        }
    }
    
    if (trendDirectionElement && regimeData.metrics && regimeData.metrics.trend_direction !== undefined) {
        const direction = regimeData.metrics.trend_direction;
        
        if (direction > 0.5) {
            trendDirectionElement.innerHTML = '<i class="bi bi-arrow-up-circle-fill text-success"></i>';
        } else if (direction < -0.5) {
            trendDirectionElement.innerHTML = '<i class="bi bi-arrow-down-circle-fill text-danger"></i>';
        } else {
            trendDirectionElement.innerHTML = '<i class="bi bi-dash-circle-fill text-secondary"></i>';
        }
    }
    
    // Update profile
    if (profileElement && regimeData.active_profile) {
        profileElement.innerText = regimeData.active_profile;
    }
    
    // Update detection time
    if (detectedTimeElement && regimeData.timestamp) {
        const detectionTime = new Date(regimeData.timestamp);
        const timeDiff = Math.floor((new Date() - detectionTime) / 1000 / 60); // minutes
        
        if (timeDiff < 60) {
            detectedTimeElement.innerText = `Last detected: ${timeDiff} minutes ago`;
        } else if (timeDiff < 24 * 60) {
            const hours = Math.floor(timeDiff / 60);
            detectedTimeElement.innerText = `Last detected: ${hours} hour${hours > 1 ? 's' : ''} ago`;
        } else {
            detectedTimeElement.innerText = `Last detected: ${formatDateTime(regimeData.timestamp)}`;
        }
    }
}

// Fetch regime history
async function fetchRegimeHistory() {
    try {
        const timeframe = document.getElementById('history-timeframe').value || '1w';
        
        const data = await apiRequest(`market/regime/history?timeframe=${timeframe}`);
        
        if (data.history) {
            regimeHistory = data.history;
            updateRegimeTimeline(data.history);
        }
        
        if (data.stats) {
            regimeStats = data.stats;
            updateRegimeDistribution(data.stats);
        }
        
        if (data.indicators) {
            updateMarketIndicatorsChart(data.indicators);
        }
        
        return data;
    } catch (error) {
        console.error('Error fetching regime history:', error);
    }
}

// Fetch performance comparison data
async function fetchPerformanceData() {
    try {
        // Show loading state
        document.getElementById('performance-loading').classList.remove('d-none');
        document.getElementById('performance-content').classList.add('d-none');
        
        const timeframe = document.getElementById('performance-timeframe').value || '30';
        
        const data = await apiRequest(`market/performance?days=${timeframe}`);
        
        if (data) {
            performanceData = data;
            updatePerformanceChart(data);
            updatePerformanceTable(data);
            
            // Hide loading, show content
            document.getElementById('performance-loading').classList.add('d-none');
            document.getElementById('performance-content').classList.remove('d-none');
        }
        
        return data;
    } catch (error) {
        console.error('Error fetching performance data:', error);
        document.getElementById('performance-loading').classList.add('d-none');
        document.getElementById('performance-content').classList.remove('d-none');
        showAlert('danger', 'Failed to load performance data');
    }
}

// Update performance chart
function updatePerformanceChart(data) {
    const canvas = document.getElementById('regime-performance-chart');
    if (!canvas) return;
    
    // Prepare chart data
    const regimeLabels = [];
    const adaptiveData = [];
    const defaultData = [];
    const backgroundColors = [];
    
    if (data.regime_performance) {
        Object.entries(data.regime_performance).forEach(([regime, perf]) => {
            regimeLabels.push(regime.replace('_', ' '));
            adaptiveData.push(perf.adaptive_roi * 100); // Convert to percentage
            defaultData.push(perf.default_roi * 100);
            
            // Set color based on regime
            switch (regime) {
                case 'STRONG_UPTREND': backgroundColors.push('rgba(30, 126, 52, 0.7)'); break;
                case 'WEAK_UPTREND': backgroundColors.push('rgba(40, 167, 69, 0.7)'); break;
                case 'RANGING': backgroundColors.push('rgba(108, 117, 125, 0.7)'); break;
                case 'WEAK_DOWNTREND': backgroundColors.push('rgba(255, 193, 7, 0.7)'); break;
                case 'STRONG_DOWNTREND': backgroundColors.push('rgba(220, 53, 69, 0.7)'); break;
                case 'HIGH_VOLATILITY': backgroundColors.push('rgba(153, 50, 204, 0.7)'); break;
                case 'REVERSAL_LIKELY': backgroundColors.push('rgba(255, 102, 0, 0.7)'); break;
                case 'BREAKOUT_FORMING': backgroundColors.push('rgba(0, 123, 255, 0.7)'); break;
                default: backgroundColors.push('rgba(108, 117, 125, 0.7)');
            }
        });
    }
    
    // Destroy existing chart if it exists
    if (performanceComparisonChart) {
        performanceComparisonChart.destroy();
    }
    
    // Create chart
    performanceComparisonChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: regimeLabels,
            datasets: [
                {
                    label: 'Adaptive',
                    data: adaptiveData,
                    backgroundColor: backgroundColors,
                    borderColor: backgroundColors.map(color => color.replace('0.7', '1')),
                    borderWidth: 1
                },
                {
                    label: 'Default',
                    data: defaultData,
                    backgroundColor: 'rgba(173, 181, 189, 0.5)',
                    borderColor: 'rgba(173, 181, 189, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'ROI %'
                    },
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.raw.toFixed(2) + '%';
                        }
                    }
                }
            }
        }
    });
}

// Update performance comparison table
function updatePerformanceTable(data) {
    // Update comparison table
    if (data.overall_performance) {
        const adaptiveWinRate = document.getElementById('adaptive-win-rate');
        const defaultWinRate = document.getElementById('default-win-rate');
        const adaptiveAvgProfit = document.getElementById('adaptive-avg-profit');
        const defaultAvgProfit = document.getElementById('default-avg-profit');
        const adaptiveROI = document.getElementById('adaptive-total-roi');
        const defaultROI = document.getElementById('default-total-roi');
        
        const overall = data.overall_performance;
        
        // Format and display values
        if (adaptiveWinRate) adaptiveWinRate.innerText = formatPercentage(overall.adaptive_win_rate);
        if (defaultWinRate) defaultWinRate.innerText = formatPercentage(overall.default_win_rate);
        
        if (adaptiveAvgProfit) adaptiveAvgProfit.innerText = formatPercentage(overall.adaptive_avg_profit);
        if (defaultAvgProfit) defaultAvgProfit.innerText = formatPercentage(overall.default_avg_profit);
        
        if (adaptiveROI) adaptiveROI.innerText = formatPercentage(overall.adaptive_total_roi);
        if (defaultROI) defaultROI.innerText = formatPercentage(overall.default_total_roi);
        
        // Add color indicators based on comparison
        highlightBetterValue(adaptiveWinRate, defaultWinRate);
        highlightBetterValue(adaptiveAvgProfit, defaultAvgProfit);
        highlightBetterValue(adaptiveROI, defaultROI);
    }
}

// Helper to highlight better value
function highlightBetterValue(adaptiveEl, defaultEl) {
    if (!adaptiveEl || !defaultEl) return;
    
    // Parse values (remove % and convert to number)
    const adaptiveVal = parseFloat(adaptiveEl.innerText.replace('%', ''));
    const defaultVal = parseFloat(defaultEl.innerText.replace('%', ''));
    
    if (adaptiveVal > defaultVal) {
        adaptiveEl.classList.add('text-success', 'fw-bold');
        defaultEl.classList.add('text-muted');
    } else if (defaultVal > adaptiveVal) {
        defaultEl.classList.add('text-success', 'fw-bold');
        adaptiveEl.classList.add('text-muted');
    }
}

// Format percentage with proper sign
function formatPercentage(value) {
    if (value === undefined || value === null) return '--';
    
    // Convert to percentage and format with 2 decimal places
    const percentage = (value * 100).toFixed(2) + '%';
    
    // Add plus sign for positive values
    if (value > 0) {
        return '+' + percentage;
    }
    return percentage;
}

// Download regime history as CSV
function downloadRegimeHistory() {
    if (!regimeHistory || regimeHistory.length === 0) {
        showAlert('warning', 'No regime history available to download');
        return;
    }
    
    // Convert regime history to CSV
    const headers = ['Timestamp', 'Regime', 'Confidence', 'Duration (min)', 'Profile', 'ADX', 'Volatility', 'Trend Direction'];
    
    const csvRows = [
        headers.join(',') // Header row
    ];
    
    regimeHistory.forEach(regime => {
        const row = [
            new Date(regime.timestamp).toISOString(),
            regime.regime,
            regime.confidence,
            regime.duration_minutes || '',
            regime.active_profile || '',
            regime.metrics?.adx || '',
            regime.metrics?.volatility || '',
            regime.metrics?.trend_direction || ''
        ];
        
        csvRows.push(row.join(','));
    });
    
    const csvContent = csvRows.join('\n');
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `regime_history_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.display = 'none';
    document.body.appendChild(link);
    
    // Start download and cleanup
    link.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(link);
}

// Filter indicator chart based on selection
function filterIndicatorChart(indicator) {
    if (!marketIndicatorsChart) return;
    
    // Get all datasets
    const datasets = marketIndicatorsChart.data.datasets;
    
    // Toggle visibility based on selection
    if (indicator === 'combined') {
        // Show all datasets
        datasets.forEach(dataset => {
            dataset.hidden = false;
        });
    } else {
        // Show only selected indicator
        datasets.forEach(dataset => {
            const datasetName = dataset.label.toLowerCase();
            dataset.hidden = !datasetName.includes(indicator);
        });
    }
    
    // Update chart
    marketIndicatorsChart.update();
}

// Update regime timeline
function updateRegimeTimeline(history) {
    const container = document.getElementById('regime-timeline');
    if (!container) return;
    
    // Clear container
    container.innerHTML = '';
    
    if (!history || history.length === 0) {
        container.innerHTML = '<div class="alert alert-info w-100 text-center">No regime history available</div>';
        return;
    }
    
    // Calculate width for each block based on duration if available
    let totalDuration = 0;
    let hasValidDurations = true;
    
    // Try to calculate total duration for proportional widths
    history.forEach(entry => {
        if (entry.duration_minutes) {
            totalDuration += entry.duration_minutes;
        } else {
            hasValidDurations = false;
        }
    });
    
    // Create timeline blocks
    history.forEach((entry, index) => {
        const regime = entry.regime;
        const timestamp = new Date(entry.timestamp);
        const formattedTime = formatDateTime(timestamp, 'short');
        
        const block = document.createElement('div');
        block.className = `regime-block ${regime}`;
        block.title = `${regime.replace('_', ' ')} at ${formatDateTime(timestamp, 'full')}`;
        block.innerText = formattedTime;
        block.dataset.index = index;
        
        // Set width based on duration if available
        if (hasValidDurations && totalDuration > 0 && entry.duration_minutes) {
            const widthPercentage = (entry.duration_minutes / totalDuration) * 100;
            block.style.width = `${Math.max(5, widthPercentage)}%`; // Minimum 5% width for visibility
        } else {
            // Default equal widths if durations not available
            block.style.width = `${Math.max(80, 1200 / history.length)}px`;
        }
        
        // Add click handler to show details
        block.addEventListener('click', (e) => {
            // Remove selected class from all blocks
            document.querySelectorAll('.regime-block.selected').forEach(el => {
                el.classList.remove('selected');
            });
            
            // Add selected class to clicked block
            block.classList.add('selected');
            
            // Show details
            showRegimeDetails(entry);
            
            // Prevent bubbling
            e.stopPropagation();
        });
        
        container.appendChild(block);
    });
    
    // Reset timeline view
    resetTimelineView();
}

// Show regime details
function showRegimeDetails(regime) {
    // Create or update modal with regime details
    let modal = document.getElementById('regimeDetailModal');
    
    if (!modal) {
        // Create modal if it doesn't exist
        const modalHTML = `
            <div class="modal fade" id="regimeDetailModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header ${regime.regime.toLowerCase()} text-white">
                            <h5 class="modal-title">Regime Details</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body" id="regime-detail-body">
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        modal = document.getElementById('regimeDetailModal');
    }
    
    // Set modal header class based on regime
    const modalHeader = modal.querySelector('.modal-header');
    modalHeader.className = `modal-header ${regime.regime} text-white`;
    
    // Fill in details
    const detailsBody = document.getElementById('regime-detail-body');
    
    const date = new Date(regime.timestamp);
    
    const detailsHTML = `
        <h5>${regime.regime.replace('_', ' ')}</h5>
        <p class="mb-3">Detected on ${formatDateTime(date, 'full')}</p>
        
        <div class="row">
            <div class="col-6">
                <p><strong>Confidence:</strong> ${(regime.confidence * 100).toFixed(1)}%</p>
                <p><strong>ADX:</strong> ${regime.metrics?.adx?.toFixed(1) || '--'}</p>
                <p><strong>Volatility:</strong> ${regime.metrics?.volatility?.toFixed(2) || '--'}</p>
            </div>
            <div class="col-6">
                <p><strong>Trend Direction:</strong> ${getTrendDirectionText(regime.metrics?.trend_direction)}</p>
                <p><strong>Active Profile:</strong> ${regime.active_profile || '--'}</p>
                <p><strong>Duration:</strong> ${regime.duration_minutes ? `${regime.duration_minutes} min` : 'Unknown'}</p>
            </div>
        </div>
    `;
    
    detailsBody.innerHTML = detailsHTML;
    
    // Show modal
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

// Helper to get trend direction text
function getTrendDirectionText(direction) {
    if (direction === undefined || direction === null) return '--';
    
    if (direction > 0.5) return 'Bullish';
    if (direction < -0.5) return 'Bearish';
    return 'Neutral';
}

// Update regime distribution chart
function updateRegimeDistribution(stats) {
    const canvas = document.getElementById('regime-distribution-chart');
    const table = document.getElementById('regime-stats-table').querySelector('tbody');
    
    if (!canvas || !table) return;
    
    // Clear table
    table.innerHTML = '';
    
    // Prepare chart data
    const labels = [];
    const data = [];
    const backgroundColor = [];
    
    // Process stats
    let totalCount = 0;
    Object.entries(stats).forEach(([regime, count]) => {
        totalCount += count;
    });
    
    Object.entries(stats).forEach(([regime, count]) => {
        labels.push(regime.replace('_', ' '));
        data.push(count);
        
        // Set color based on regime
        switch (regime) {
            case 'STRONG_UPTREND': backgroundColor.push('#1e7e34'); break;
            case 'WEAK_UPTREND': backgroundColor.push('#28a745'); break;
            case 'RANGING': backgroundColor.push('#6c757d'); break;
            case 'WEAK_DOWNTREND': backgroundColor.push('#ffc107'); break;
            case 'STRONG_DOWNTREND': backgroundColor.push('#dc3545'); break;
            case 'HIGH_VOLATILITY': backgroundColor.push('#9932cc'); break;
            default: backgroundColor.push('#6c757d');
        }
        
        // Add table row
        const percentage = ((count / totalCount) * 100).toFixed(1);
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <span class="badge regime-badge ${regime}">${regime.replace('_', ' ')}</span>
            </td>
            <td>${count}</td>
            <td>${percentage}%</td>
        `;
        
        table.appendChild(row);
    });
    
    // Create or update chart
    if (regimeDistributionChart) {
        regimeDistributionChart.data.labels = labels;
        regimeDistributionChart.data.datasets[0].data = data;
        regimeDistributionChart.data.datasets[0].backgroundColor = backgroundColor;
        regimeDistributionChart.update();
    } else {
        regimeDistributionChart = new Chart(canvas, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColor,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }
}

// Update market indicators chart
function updateMarketIndicatorsChart(indicators) {
    const canvas = document.getElementById('market-indicators-chart');
    if (!canvas) return;
    
    // Prepare data
    const timestamps = indicators.timestamps.map(ts => new Date(ts));
    const adxData = indicators.adx || [];
    const volatilityData = indicators.volatility || [];
    
    // Create or update chart
    if (marketIndicatorsChart) {
        marketIndicatorsChart.data.labels = timestamps;
        marketIndicatorsChart.data.datasets[0].data = adxData;
        marketIndicatorsChart.data.datasets[1].data = volatilityData;
        marketIndicatorsChart.update();
    } else {
        marketIndicatorsChart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [
                    {
                        label: 'ADX',
                        data: adxData,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        borderWidth: 2,
                        tension: 0.1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Volatility',
                        data: volatilityData,
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        borderWidth: 2,
                        tension: 0.1,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'hour',
                            displayFormats: {
                                hour: 'MMM d, HH:mm'
                            }
                        },
                        ticks: {
                            maxTicksLimit: 8
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'ADX'
                        },
                        min: 0
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Volatility'
                        },
                        min: 0,
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                }
            }
        });
    }
}

// Run market regime backtest
async function runBacktest() {
    try {
        const days = document.getElementById('backtest-days').value || 30;
        const symbol = document.getElementById('backtest-symbol').value || 'BTC/USDT';
        
        // Show status
        const statusContainer = document.getElementById('backtest-status');
        const progressBar = document.getElementById('backtest-progress');
        const statusText = document.getElementById('backtest-status-text');
        
        statusContainer.style.display = 'block';
        document.getElementById('backtest-results').style.display = 'none';
        progressBar.style.width = '10%';
        statusText.innerText = 'Starting backtest...';
        
        // Disable run button
        const runButton = document.getElementById('run-backtest-btn');
        runButton.disabled = true;
        
        // Run backtest
        const response = await apiRequest('market/backtest', {
            method: 'POST',
            body: JSON.stringify({
                days_back: parseInt(days),
                symbol: symbol
            })
        });
        
        // Update progress
        progressBar.style.width = '100%';
        statusText.innerText = 'Processing results...';
        
        // Check result
        if (response.success) {
            // Show results
            document.getElementById('backtest-results').style.display = 'block';
            document.getElementById('backtest-days-count').innerText = days;
            
            // Store results for modal
            window.backtestResults = response;
            
            // Update summary
            const summary = response.summary || {};
            const totalDataPoints = summary.total_datapoints || 0;
            
            document.getElementById('backtest-summary').innerText = 
                `Analyzed ${days} days (${totalDataPoints} data points) with ${summary.regime_changes || 0} regime changes detected.`;
                
            showToast('Backtest Complete', 'Regime detection backtest completed successfully', 'success');
        } else {
            // Show error
            statusText.innerText = `Error: ${response.error || 'Unknown error'}`;
            progressBar.className = 'progress-bar bg-danger';
            
            showToast('Backtest Failed', response.error || 'Unknown error', 'error');
        }
        
        // Re-enable button
        runButton.disabled = false;
        
        return response;
    } catch (error) {
        console.error('Error running backtest:', error);
        
        // Update UI
        const statusText = document.getElementById('backtest-status-text');
        const progressBar = document.getElementById('backtest-progress');
        
        statusText.innerText = `Error: ${error.message}`;
        progressBar.className = 'progress-bar bg-danger';
        
        // Re-enable button
        document.getElementById('run-backtest-btn').disabled = false;
    }
}

// Show backtest results modal
function showBacktestModal() {
    const results = window.backtestResults;
    if (!results || !results.success) {
        showToast('No Results', 'No backtest results available', 'warning');
        return;
    }
    
    // Get modal
    const modal = document.getElementById('backtestResultsModal');
    const modalInstance = new bootstrap.Modal(modal);
    
    // Update backtest chart
    updateBacktestChart(results.regime_timeline || []);
    
    // Update regime stats table
    updateBacktestRegimeStats(results.regime_stats || {});
    
    // Show modal
    modalInstance.show();
}

// Update backtest chart
function updateBacktestChart(timeline) {
    const canvas = document.getElementById('backtest-results-chart');
    if (!canvas) return;
    
    // Prepare data
    const labels = timeline.map(entry => new Date(entry.timestamp));
    
    // Create dataset with regime as point style
    const data = timeline.map(entry => {
        // Map regime to a numeric value for visualization
        switch(entry.regime) {
            case 'STRONG_UPTREND': return 5;
            case 'WEAK_UPTREND': return 4;
            case 'RANGING': return 3;
            case 'WEAK_DOWNTREND': return 2;
            case 'STRONG_DOWNTREND': return 1;
            case 'HIGH_VOLATILITY': return 0;
            default: return null;
        }
    });
    
    // Create color map
    const pointBackgroundColor = timeline.map(entry => {
        switch(entry.regime) {
            case 'STRONG_UPTREND': return '#1e7e34';
            case 'WEAK_UPTREND': return '#28a745';
            case 'RANGING': return '#6c757d';
            case 'WEAK_DOWNTREND': return '#ffc107';
            case 'STRONG_DOWNTREND': return '#dc3545';
            case 'HIGH_VOLATILITY': return '#9932cc';
            default: return '#6c757d';
        }
    });
    
    // Create or update chart
    if (backtestResultsChart) {
        backtestResultsChart.data.labels = labels;
        backtestResultsChart.data.datasets[0].data = data;
        backtestResultsChart.data.datasets[0].pointBackgroundColor = pointBackgroundColor;
        backtestResultsChart.update();
    } else {
        backtestResultsChart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Market Regime',
                        data: data,
                        pointBackgroundColor: pointBackgroundColor,
                        borderColor: 'rgba(75, 192, 192, 0.7)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        borderWidth: 1,
                        pointRadius: 6,
                        pointHoverRadius: 8,
                        tension: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'day',
                            displayFormats: {
                                day: 'MMM d'
                            }
                        },
                        ticks: {
                            maxTicksLimit: 10
                        }
                    },
                    y: {
                        min: 0,
                        max: 6,
                        ticks: {
                            callback: function(value) {
                                switch(value) {
                                    case 5: return 'Strong Up';
                                    case 4: return 'Weak Up';
                                    case 3: return 'Ranging';
                                    case 2: return 'Weak Down';
                                    case 1: return 'Strong Down';
                                    case 0: return 'Volatile';
                                    default: return '';
                                }
                            }
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const index = context.dataIndex;
                                const entry = timeline[index];
                                let label = entry.regime.replace('_', ' ');
                                
                                if (entry.confidence) {
                                    label += ` (${(entry.confidence * 100).toFixed(1)}% confidence)`;
                                }
                                
                                return label;
                            }
                        }
                    }
                }
            }
        });
    }
}

// Update backtest regime stats table
function updateBacktestRegimeStats(stats) {
    const table = document.getElementById('backtest-regime-stats').querySelector('tbody');
    if (!table) return;
    
    // Clear table
    table.innerHTML = '';
    
    // Calculate total count
    let totalCount = 0;
    Object.values(stats).forEach(stat => {
        totalCount += stat.count || 0;
    });
    
    // Add rows
    Object.entries(stats).forEach(([regime, stat]) => {
        const percentage = totalCount > 0 ? ((stat.count / totalCount) * 100).toFixed(1) : '0.0';
        const avgDuration = stat.avg_duration ? `${stat.avg_duration.toFixed(1)} hrs` : 'N/A';
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <span class="badge regime-badge ${regime}">${regime.replace('_', ' ')}</span>
            </td>
            <td>${stat.count || 0}</td>
            <td>${percentage}%</td>
            <td>${avgDuration}</td>
        `;
        
        table.appendChild(row);
    });
}

// Save detection settings
async function saveDetectionSettings() {
    const detectionEnabled = document.getElementById('toggle-regime-detection').checked;
        
try {
const response = await apiRequest('market/detection-settings', {
method: 'POST',
body: JSON.stringify({
enabled: detectionEnabled,
interval_minutes: interval,
adx_threshold: adxThreshold,
volatility_threshold: volatilityThreshold
})
});
        
if (response.success) {
showToast('Settings Saved', 'Market regime detection settings updated', 'success');
}
        
return response;
} catch (error) {
console.error('Error saving detection settings:', error);
}
}

// Fetch active signals
async function fetchActiveSignals() {
    try {
        const data = await apiRequest('bot/active_signals');
        updateSignalsTable(data.signals || []);
        return data;
    } catch (error) {
        console.error('Error fetching active signals:', error);
        handleError(error, 'fetching active signals');
    }
}

// Update signals table
function updateSignalsTable(signals) {
    const tbody = document.getElementById('signals-tbody');
    const noSignalsRow = document.getElementById('no-signals-row');
    
    // Clear existing signals
    while (tbody.firstChild) {
        tbody.removeChild(tbody.firstChild);
    }
    
    // Show/hide no signals message
    if (!signals || signals.length === 0) {
        tbody.appendChild(noSignalsRow);
        return;
    }
    
    // Add signals to table
    signals.forEach(signal => {
        const row = document.createElement('tr');
        
        // Format timestamp
        const timestamp = new Date(signal.timestamp);
        const formattedTime = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        // Format signal type with appropriate badge color
        const signalTypeColor = signal.direction === 'long' ? 'success' : 'danger';
        const signalTypeText = signal.direction === 'long' ? 'LONG' : 'SHORT';
        
        // Format status with appropriate badge
        let statusBadge = '';
        switch (signal.status.toLowerCase()) {
            case 'active':
                statusBadge = '<span class="badge bg-success">Active</span>';
                break;
            case 'executed':
                statusBadge = '<span class="badge bg-primary">Executed</span>';
                break;
            case 'completed':
                statusBadge = '<span class="badge bg-info">Completed</span>';
                break;
            case 'cancelled':
                statusBadge = '<span class="badge bg-secondary">Cancelled</span>';
                break;
            default:
                statusBadge = `<span class="badge bg-light text-dark">${signal.status}</span>`;
        }
        
        // Build row content
        row.innerHTML = `
            <td><strong>${signal.symbol}</strong></td>
            <td>${signal.strategy_name}</td>
            <td><span class="badge bg-${signalTypeColor}">${signalTypeText}</span></td>
            <td>${formattedTime}</td>
            <td>${(signal.confidence * 100).toFixed(1)}%</td>
            <td>${statusBadge}</td>
        `;
        
        tbody.appendChild(row);
    });
    
    // Highlight new signals with animation
    const rows = tbody.querySelectorAll('tr');
    rows.forEach(row => {
        row.classList.add('new-signal-highlight');
        setTimeout(() => {
            row.classList.remove('new-signal-highlight');
        }, 2000);
    });
}

// Handle strategy toggle
async function handleStrategyToggle(event) {
    const toggle = event.target;
    const strategyId = toggle.dataset.strategy;
    const enabled = toggle.checked;
    
    try {
        const data = await apiRequest('bot/toggle_strategy', {
            method: 'POST',
            body: JSON.stringify({
                strategy_id: strategyId,
                enabled: enabled
            })
        });
        
        // Update status badge
        const statusBadgeId = strategyId === 'supertrend_adx' ? 'supertrend-status' : 'inside-bar-status';
        const statusBadge = document.getElementById(statusBadgeId);
        
        if (statusBadge) {
            statusBadge.className = `badge ${enabled ? 'bg-success' : 'bg-secondary'}`;
            statusBadge.textContent = enabled ? 'Active' : 'Inactive';
        }
        
        // Show success message
        showAlert('success', `${strategyId === 'supertrend_adx' ? 'Supertrend+ADX' : 'Inside-Bar'} strategy ${enabled ? 'enabled' : 'disabled'} successfully`);
        
        return data;
    } catch (error) {
        console.error(`Error toggling strategy ${strategyId}:`, error);
        handleError(error, 'toggling strategy');
        
        // Revert toggle state on error
        toggle.checked = !enabled;
    }
}

// Fetch signal counts for today
async function fetchSignalCounts() {
    try {
        const data = await apiRequest('bot/signal_counts');
        
        // Update count displays
        document.getElementById('signal-count').textContent = data.generated_count || 0;
        document.getElementById('trade-count').textContent = data.executed_count || 0;
        document.getElementById('max-signals').textContent = data.max_signals || 15;
        
        // Add progress visual if desired
        const signalPercentage = ((data.generated_count || 0) / (data.max_signals || 15)) * 100;
        if (signalPercentage > 80) {
            document.getElementById('signal-count').classList.add('text-danger');
        } else if (signalPercentage > 60) {
            document.getElementById('signal-count').classList.add('text-warning');
        } else {
            document.getElementById('signal-count').classList.remove('text-danger', 'text-warning');
        }
        
        return data;
    } catch (error) {
        console.error('Error fetching signal counts:', error);
        // Silently handle this error to avoid too many notifications
    }
}

// Download backtest results as CSV
function downloadBacktestResults() {
    const results = window.backtestResults;
    if (!results || !results.regime_timeline) {
        showToast('No Results', 'No backtest results available to download', 'warning');
        return;
    }
    
    // Prepare CSV content
    const timeline = results.regime_timeline;
    
    let csvContent = 'data:text/csv;charset=utf-8,';
    csvContent += 'Timestamp,Regime,Confidence,ADX,Volatility,Trend Direction\n';
    
    timeline.forEach(entry => {
        const row = [
            new Date(entry.timestamp).toISOString(),
            entry.regime,
            entry.confidence || '',
            entry.metrics?.adx || '',
            entry.metrics?.volatility || '',
            entry.metrics?.trend_direction || ''
        ].join(',');
        
        csvContent += row + '\n';
    });
    
    // Create download link
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `market_regime_backtest_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    
    // Trigger download and clean up
    link.click();
    document.body.removeChild(link);
}
