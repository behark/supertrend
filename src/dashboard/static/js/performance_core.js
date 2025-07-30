/**
 * Performance Analytics Utilities
 * -----------------------------
 * Core helper functions for the regime performance dashboard
 */

/**
 * Update performance statistics display
 */
function updatePerformanceStats() {
    if (!state.performanceEntries || state.performanceEntries.length === 0) {
        return;
    }
    
    // Total regimes count
    document.getElementById('total-regimes-count').innerText = state.performanceEntries.length;
    
    // High performer count
    const highPerformerCount = state.performanceEntries.filter(entry => 
        entry.pattern_analysis.is_high_performer).length;
    document.getElementById('high-performer-count').innerText = highPerformerCount;
    
    // Best regime ROI
    let bestRoi = -Infinity;
    state.performanceEntries.forEach(entry => {
        if (entry.performance.roi_pct > bestRoi) {
            bestRoi = entry.performance.roi_pct;
        }
    });
    document.getElementById('best-regime-roi').innerText = formatPercentage(bestRoi);
    
    // Average regime confidence
    const avgConfidence = state.performanceEntries.reduce((sum, entry) => 
        sum + entry.confidence, 0) / state.performanceEntries.length;
    document.getElementById('avg-regime-confidence').innerText = 
        (avgConfidence * 100).toFixed(1) + '%';
}

/**
 * Update timeline chart with performance data
 */
function updateTimelineChart() {
    if (!state.charts.timeline || !state.performanceEntries || 
        state.performanceEntries.length === 0) {
        return;
    }
    
    // Sort entries by start time
    const sortedEntries = [...state.performanceEntries]
        .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
    
    // Prepare chart data
    const labels = [];
    const data = [];
    const backgroundColors = [];
    const borderColors = [];
    
    sortedEntries.forEach(entry => {
        // Create label from date
        const startDate = new Date(entry.start_time);
        const label = formatDate(startDate);
        labels.push(label);
        
        // Set data point as duration in hours (to represent block width)
        let duration = 1; // Default 1 hour if no duration
        if (entry.start_time && entry.end_time) {
            const start = new Date(entry.start_time);
            const end = new Date(entry.end_time);
            duration = (end - start) / (1000 * 60 * 60); // Hours
            duration = Math.max(1, duration); // Minimum 1 hour for visibility
        }
        data.push(duration);
        
        // Set colors based on regime type
        const color = getRegimeColor(entry.regime_type);
        backgroundColors.push(color);
        borderColors.push(color.replace('0.7', '1.0')); // Darker border
    });
    
    // Update chart data
    state.charts.timeline.data.labels = labels;
    state.charts.timeline.data.datasets[0].data = data;
    state.charts.timeline.data.datasets[0].backgroundColor = backgroundColors;
    state.charts.timeline.data.datasets[0].borderColor = borderColors;
    
    // Update chart
    state.charts.timeline.update();
}

/**
 * Update performance comparison charts
 */
function updatePerformanceCharts() {
    if (!state.charts.comparison || !state.charts.confidencePerformance || 
        !state.performanceEntries || state.performanceEntries.length === 0) {
        return;
    }
    
    // Group entries by regime type for comparison chart
    const regimeData = {
        'Strong Uptrend': { roi: [], winRate: [] },
        'Strong Downtrend': { roi: [], winRate: [] },
        'Ranging': { roi: [], winRate: [] },
        'High Volatility': { roi: [], winRate: [] },
        'Transition': { roi: [], winRate: [] }
    };
    
    // Prepare scatter data for confidence vs performance chart
    const scatterData = [];
    
    state.performanceEntries.forEach(entry => {
        const regimeType = entry.regime_type;
        const roi = entry.performance.roi_pct;
        const winRate = entry.performance.win_rate;
        const confidence = entry.confidence;
        
        // Add to regime data if valid
        if (regimeData[regimeType] && roi !== null && winRate !== null) {
            regimeData[regimeType].roi.push(roi);
            regimeData[regimeType].winRate.push(winRate);
        }
        
        // Add to scatter data
        if (roi !== null && confidence !== null) {
            scatterData.push({
                x: confidence,
                y: roi,
                regime_type: regimeType
            });
        }
    });
    
    // Calculate averages for comparison chart
    const roiData = [];
    const winRateData = [];
    
    Object.keys(regimeData).forEach(regime => {
        const data = regimeData[regime];
        
        // Calculate average ROI
        if (data.roi.length > 0) {
            const avgRoi = data.roi.reduce((sum, val) => sum + val, 0) / data.roi.length;
            roiData.push(avgRoi);
        } else {
            roiData.push(0);
        }
        
        // Calculate average win rate
        if (data.winRate.length > 0) {
            const avgWinRate = data.winRate.reduce((sum, val) => sum + val, 0) / data.winRate.length;
            winRateData.push(avgWinRate);
        } else {
            winRateData.push(0);
        }
    });
    
    // Update comparison chart
    state.charts.comparison.data.datasets[0].data = roiData;
    state.charts.comparison.data.datasets[1].data = winRateData;
    state.charts.comparison.update();
    
    // Update confidence vs performance chart
    state.charts.confidencePerformance.data.datasets[0].data = scatterData;
    state.charts.confidencePerformance.update();
}

/**
 * Show performance details modal
 */
function showPerformanceDetails(performanceId) {
    // Find the performance entry
    const entry = state.performanceEntries.find(e => e.id === performanceId);
    if (!entry) {
        showToast('Performance entry not found', 'error');
        return;
    }
    
    // Store selected entry for potential playbook creation
    state.selectedPerformanceEntry = entry;
    
    // Set modal title
    document.getElementById('performance-details-title').innerText = 
        `${entry.regime_type} Performance Details`;
    
    // Build modal content
    const modalBody = document.getElementById('performance-details-body');
    
    const startDate = new Date(entry.start_time);
    const endDate = entry.end_time ? new Date(entry.end_time) : null;
    const duration = endDate ? calculateDuration(startDate, endDate) : 'Ongoing';
    
    modalBody.innerHTML = `
        <div class="row mb-3">
            <div class="col-md-6">
                <h5>Regime Information</h5>
                <table class="table table-sm">
                    <tr>
                        <td><strong>Type:</strong></td>
                        <td><span class="regime-tag ${getRegimeTagClass(entry.regime_type)}">${entry.regime_type}</span></td>
                    </tr>
                    <tr>
                        <td><strong>Confidence:</strong></td>
                        <td>${(entry.confidence * 100).toFixed(1)}%</td>
                    </tr>
                    <tr>
                        <td><strong>Duration:</strong></td>
                        <td>${duration}</td>
                    </tr>
                    <tr>
                        <td><strong>Preceding Regime:</strong></td>
                        <td>${entry.market_context.preceding_regime || 'None'}</td>
                    </tr>
                    <tr>
                        <td><strong>Market Phase:</strong></td>
                        <td>${entry.market_context.market_phase || 'Unknown'}</td>
                    </tr>
                </table>
            </div>
            <div class="col-md-6">
                <h5>Performance Metrics</h5>
                <table class="table table-sm">
                    <tr>
                        <td><strong>ROI:</strong></td>
                        <td class="${entry.performance.roi_pct >= 0 ? 'positive-value' : 'negative-value'}">
                            ${formatPercentage(entry.performance.roi_pct)}
                        </td>
                    </tr>
                    <tr>
                        <td><strong>Win Rate:</strong></td>
                        <td>${formatPercentage(entry.performance.win_rate)}</td>
                    </tr>
                    <tr>
                        <td><strong>Avg Profit:</strong></td>
                        <td>${formatPercentage(entry.performance.avg_profit_pct)}</td>
                    </tr>
                    <tr>
                        <td><strong>Max Drawdown:</strong></td>
                        <td>${formatPercentage(entry.performance.max_drawdown_pct)}</td>
                    </tr>
                    <tr>
                        <td><strong>Trade Count:</strong></td>
                        <td>${entry.performance.trade_count}</td>
                    </tr>
                </table>
            </div>
        </div>
        
        <div class="row mb-3">
            <div class="col-12">
                <h5>Market Indicators</h5>
                <div class="row">
                    <div class="col-md-4">
                        <div class="card p-2">
                            <div class="text-center">
                                <h3>${entry.market_context.adx ? entry.market_context.adx.toFixed(1) : 'N/A'}</h3>
                                <p class="mb-0">ADX</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card p-2">
                            <div class="text-center">
                                <h3>${entry.market_context.volatility ? 
                                    (entry.market_context.volatility * 100).toFixed(2) + '%' : 'N/A'}</h3>
                                <p class="mb-0">Volatility</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card p-2">
                            <div class="text-center">
                                <h3>${entry.market_context.rsi ? entry.market_context.rsi.toFixed(1) : 'N/A'}</h3>
                                <p class="mb-0">RSI</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-6">
                <h5>Pattern Analysis</h5>
                <table class="table table-sm">
                    <tr>
                        <td><strong>Pattern Score:</strong></td>
                        <td>
                            <div class="pattern-score-bar">
                                <div class="pattern-score-fill" style="width: ${(entry.pattern_analysis.pattern_score || 0) * 100}%"></div>
                            </div>
                            ${entry.pattern_analysis.pattern_score ? 
                                (entry.pattern_analysis.pattern_score * 100).toFixed(1) + '%' : 'N/A'}
                        </td>
                    </tr>
                    <tr>
                        <td><strong>Statistical Significance:</strong></td>
                        <td>${entry.pattern_analysis.statistical_significance ? 
                            entry.pattern_analysis.statistical_significance.toFixed(2) : 'N/A'}</td>
                    </tr>
                    <tr>
                        <td><strong>High Performer:</strong></td>
                        <td>
                            <i class="fas ${entry.pattern_analysis.is_high_performer ? 
                                'fa-check text-success' : 'fa-times text-danger'}"></i>
                        </td>
                    </tr>
                    <tr>
                        <td><strong>Statistical Outlier:</strong></td>
                        <td>
                            <i class="fas ${entry.pattern_analysis.is_outlier ? 
                                'fa-check text-warning' : 'fa-times text-muted'}"></i>
                        </td>
                    </tr>
                </table>
            </div>
            <div class="col-md-6">
                <h5>Trading Recommendation</h5>
                <p>
                    ${entry.pattern_analysis.is_high_performer ? 
                        `<i class="fas fa-lightbulb text-warning"></i> 
                        This is a high-performing regime pattern that should be considered for playbook creation.` :
                        `<i class="fas fa-info-circle text-info"></i> 
                        This regime performance is within normal parameters and doesn't show exceptional characteristics.`}
                </p>
                <div class="alert ${entry.pattern_analysis.is_high_performer ? 'alert-success' : 'alert-secondary'}">
                    ${entry.pattern_analysis.is_high_performer ? 
                        `Click "Create Playbook" to generate trading rules based on this high-performing regime pattern.` :
                        `Continue monitoring similar regime patterns to identify potential trading opportunities.`}
                </div>
            </div>
        </div>
    `;
    
    // Enable/disable create playbook button based on whether this is a high performer
    document.getElementById('create-playbook-from-performance').disabled = 
        !entry.pattern_analysis.is_high_performer;
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('performanceDetailsModal'));
    modal.show();
}

/**
 * Show playbook details modal
 */
function showPlaybookDetails(playbookId) {
    // Find the playbook
    const playbook = state.playbooks.find(p => p.id === playbookId);
    if (!playbook) {
        showToast('Playbook not found', 'error');
        return;
    }
    
    // Set modal title
    document.getElementById('playbook-detail-title').innerText = playbook.name;
    
    // Build modal content
    const modalBody = document.getElementById('playbook-detail-body');
    
    // Create star rating based on user_rating
    let ratingHtml = '';
    if (playbook.user_rating) {
        ratingHtml = '<div class="star-rating">';
        for (let i = 0; i < 5; i++) {
            if (i < playbook.user_rating) {
                ratingHtml += '<i class="fas fa-star"></i>';
            } else {
                ratingHtml += '<i class="far fa-star"></i>';
            }
        }
        ratingHtml += '</div>';
    } else {
        ratingHtml = '<span class="text-muted">Not rated</span>';
    }
    
    modalBody.innerHTML = `
        <div class="row mb-3">
            <div class="col-12">
                <div class="d-flex justify-content-between align-items-center">
                    <span class="regime-tag ${getRegimeTagClass(playbook.regime_type)}">
                        ${playbook.regime_type}
                    </span>
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" id="playbook-active-toggle" 
                            ${playbook.is_active ? 'checked' : ''}>
                        <label class="form-check-label" for="playbook-active-toggle">
                            ${playbook.is_active ? 'Active' : 'Inactive'}
                        </label>
                    </div>
                </div>
                <p class="mt-2">${playbook.description || 'No description available.'}</p>
            </div>
        </div>
        
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-transparent">
                        <h5 class="mb-0"><i class="fas fa-sign-in-alt"></i> Entry Conditions</h5>
                    </div>
                    <div class="card-body">
                        <pre class="mb-0">${playbook.strategy.entry_conditions}</pre>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-transparent">
                        <h5 class="mb-0"><i class="fas fa-sign-out-alt"></i> Exit Conditions</h5>
                    </div>
                    <div class="card-body">
                        <pre class="mb-0">${playbook.strategy.exit_conditions}</pre>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-transparent">
                        <h5 class="mb-0"><i class="fas fa-shield-alt"></i> Risk Management</h5>
                    </div>
                    <div class="card-body">
                        <h6>Stop Loss Strategy</h6>
                        <p>${playbook.strategy.stop_loss_strategy || 'Not specified'}</p>
                        <h6>Take Profit Strategy</h6>
                        <p>${playbook.strategy.take_profit_strategy || 'Not specified'}</p>
                        <h6>Position Sizing</h6>
                        <p>${playbook.strategy.position_sizing || 'Not specified'}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-transparent">
                        <h5 class="mb-0"><i class="fas fa-cogs"></i> Parameters & Performance</h5>
                    </div>
                    <div class="card-body">
                        <h6>Confidence Threshold</h6>
                        <div class="progress mb-2">
                            <div class="progress-bar" role="progressbar" 
                                style="width: ${playbook.confidence_threshold * 100}%" 
                                aria-valuenow="${playbook.confidence_threshold * 100}" 
                                aria-valuemin="0" aria-valuemax="100">
                                ${(playbook.confidence_threshold * 100).toFixed(0)}%
                            </div>
                        </div>
                        
                        <h6>Parameter Settings</h6>
                        <div class="mb-2">
                            ${playbook.strategy.parameter_settings ? 
                                Object.entries(playbook.strategy.parameter_settings)
                                    .map(([key, value]) => `<span class="param-tag">${key}: ${value}</span>`)
                                    .join('') : 
                                '<span class="text-muted">No parameters specified</span>'}
                        </div>
                        
                        <h6>Performance</h6>
                        <table class="table table-sm">
                            <tr>
                                <td>Times Applied:</td>
                                <td>${playbook.performance.times_applied || 0}</td>
                            </tr>
                            <tr>
                                <td>Success Rate:</td>
                                <td>${playbook.performance.success_rate ? 
                                    formatPercentage(playbook.performance.success_rate) : 'N/A'}</td>
                            </tr>
                            <tr>
                                <td>Average ROI:</td>
                                <td>${playbook.performance.average_roi ? 
                                    formatPercentage(playbook.performance.average_roi) : 'N/A'}</td>
                            </tr>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-12">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <small class="text-muted">
                            Created: ${formatDateTime(playbook.created_at)}
                            ${playbook.updated_at && playbook.updated_at !== playbook.created_at ? 
                                `| Updated: ${formatDateTime(playbook.updated_at)}` : ''}
                        </small>
                    </div>
                    <div>
                        ${ratingHtml}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add event listener for active toggle
    const activeToggle = document.getElementById('playbook-active-toggle');
    activeToggle.addEventListener('change', () => {
        updatePlaybookActive(playbook.id, activeToggle.checked);
    });
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('playbookDetailModal'));
    modal.show();
}

// Utility functions
function getRegimeTagClass(regimeType) {
    switch (regimeType) {
        case 'Strong Uptrend':
            return 'tag-strong-uptrend';
        case 'Strong Downtrend':
            return 'tag-strong-downtrend';
        case 'Ranging':
            return 'tag-ranging';
        case 'High Volatility':
            return 'tag-high-volatility';
        case 'Transition':
            return 'tag-transition';
        default:
            return '';
    }
}

function getRegimeColor(regimeType) {
    switch (regimeType) {
        case 'Strong Uptrend':
            return DASHBOARD_CONFIG.chartColors.strongUptrend;
        case 'Strong Downtrend':
            return DASHBOARD_CONFIG.chartColors.strongDowntrend;
        case 'Ranging':
            return DASHBOARD_CONFIG.chartColors.ranging;
        case 'High Volatility':
            return DASHBOARD_CONFIG.chartColors.highVolatility;
        case 'Transition':
            return DASHBOARD_CONFIG.chartColors.transition;
        default:
            return 'rgba(128, 128, 128, 0.7)'; // Default gray
    }
}

function getConfidenceBadgeStyle(confidence) {
    const color = getConfidenceColor(confidence);
    return `background-color: ${color}; color: white;`;
}

function getConfidenceColor(confidence) {
    if (confidence >= 0.9) {
        return '#10b981'; // Green for high confidence
    } else if (confidence >= 0.75) {
        return '#3b82f6'; // Blue for good confidence
    } else if (confidence >= 0.6) {
        return '#f59e0b'; // Yellow for moderate confidence
    } else {
        return '#ef4444'; // Red for low confidence
    }
}

function formatPercentage(value) {
    if (value === null || value === undefined) return 'N/A';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
}

function formatDate(date) {
    if (!date) return 'N/A';
    return date.toLocaleDateString();
}

function formatDateTime(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
}

function calculateDuration(start, end) {
    if (!start) return 'N/A';
    
    const endTime = end || new Date();
    const diffMs = endTime - start;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHrs = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    
    if (diffDays > 0) {
        return `${diffDays}d ${diffHrs}h`;
    } else if (diffHrs > 0) {
        return `${diffHrs}h ${diffMins}m`;
    } else {
        return `${diffMins}m`;
    }
}

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center border-0 bg-${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.setAttribute('id', toastId);
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body text-white">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Show toast
    const toastInstance = new bootstrap.Toast(toast, { delay: 5000 });
    toastInstance.show();
    
    // Remove after hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

function showLoading(message = 'Loading...') {
    // Create alert container if it doesn't exist
    let alertContainer = document.querySelector('.alert-container');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.className = 'alert-container position-fixed top-0 start-50 translate-middle-x p-3';
        document.body.appendChild(alertContainer);
    }
    
    // Remove existing loading alerts
    const existingAlerts = alertContainer.querySelectorAll('.alert-loading');
    existingAlerts.forEach(alert => alert.remove());
    
    // Create loading alert
    const loadingAlert = document.createElement('div');
    loadingAlert.className = 'alert alert-info alert-loading d-flex align-items-center';
    loadingAlert.setAttribute('role', 'alert');
    loadingAlert.innerHTML = `
        <div class="spinner-border spinner-border-sm me-2" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <div>${message}</div>
    `;
    
    alertContainer.appendChild(loadingAlert);
}

function hideLoading() {
    const existingAlerts = document.querySelectorAll('.alert-loading');
    existingAlerts.forEach(alert => {
        alert.classList.add('fade');
        setTimeout(() => alert.remove(), 500);
    });
}
