/**
 * Trading Bot Dashboard - Overview Page JS
 * 
 * Handles data fetching and visualization for the dashboard overview page
 */

// Chart references
let dailyPnlChart = null;

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
    // Fetch initial data
    fetchBotStats();
    fetchParameters();
    fetchAnalytics();
    
    // Set up refresh intervals
    setInterval(fetchBotStats, DASHBOARD_CONFIG.refreshInterval);
    setInterval(fetchAnalytics, DASHBOARD_CONFIG.chartRefreshInterval);
});

// Fetch bot statistics
async function fetchBotStats() {
    try {
        const stats = await apiRequest('bot/stats');
        
        // Update UI elements
        document.getElementById('market-regime').innerText = stats.market_regime || 'UNKNOWN';
        document.getElementById('market-regime').className = `display-6 mb-0 text-${getRegimeColorClass(stats.market_regime)}`;
        
        document.getElementById('signals-count').innerText = stats.signals_today || 0;
        document.getElementById('trades-count').innerText = stats.trades_today || 0;
        document.getElementById('active-trades').innerText = stats.active_trades || 0;
        
        // Update active profile if available
        if (stats.active_profile) {
            document.getElementById('active-profile').innerText = stats.active_profile;
            appState.activeProfile = stats.active_profile;
        }
        
        return stats;
    } catch (error) {
        console.error('Error fetching bot stats:', error);
    }
}

// Fetch parameters and profiles
async function fetchParameters() {
    try {
        const data = await apiRequest('parameters');
        
        appState.parameters = data.parameters || {};
        appState.profiles = data.profiles || {};
        appState.activeProfile = data.active_profile || 'default';
        
        // Update parameters UI
        updateParametersDisplay(appState.parameters);
        
        // Update profiles UI
        updateProfilesDisplay(appState.profiles, appState.activeProfile);
        
        return data;
    } catch (error) {
        console.error('Error fetching parameters:', error);
    }
}

// Fetch analytics data
async function fetchAnalytics() {
    try {
        const data = await apiRequest('analytics/summary');
        
        // Update success rate if available
        if (data.daily_summary && data.daily_summary.trades) {
            const winRate = data.daily_summary.trades.win_rate || 0;
            document.getElementById('success-rate').innerText = `${(winRate * 100).toFixed(1)}%`;
        }
        
        // Update recent trades table
        if (data.recent_trades && data.recent_trades.length > 0) {
            updateRecentTradesTable(data.recent_trades);
        }
        
        // Update daily PnL chart
        if (data.daily_summary && data.daily_summary.hourly_breakdown) {
            updateDailyPnlChart(data.daily_summary.hourly_breakdown);
        }
        
        return data;
    } catch (error) {
        console.error('Error fetching analytics:', error);
    }
}

// Update parameters display
function updateParametersDisplay(parameters) {
    const container = document.getElementById('parameters-container');
    if (!container) return;
    
    // Clear loading spinner
    container.innerHTML = '';
    
    // Key parameters to display
    const keyParams = [
        { id: 'CONFIDENCE_THRESHOLD', name: 'Confidence Threshold', format: (v) => `${(v * 100).toFixed(0)}%` },
        { id: 'MAX_TRADES_PER_DAY', name: 'Max Trades / Day', format: (v) => v },
        { id: 'POSITION_SIZE_PERCENT', name: 'Position Size', format: (v) => `${v}%` },
        { id: 'SUPERTREND_ADX_WEIGHT', name: 'ST+ADX Weight', format: (v) => v }
    ];
    
    // Create parameter elements
    keyParams.forEach(param => {
        if (parameters[param.id] !== undefined) {
            const value = parameters[param.id];
            const formattedValue = param.format(value);
            
            const paramHtml = `
                <div class="parameter-section mb-3">
                    <p class="parameter-name">${param.name}</p>
                    <h3 class="parameter-value">${formattedValue}</h3>
                </div>
            `;
            
            container.insertAdjacentHTML('beforeend', paramHtml);
        }
    });
}

// Update profiles display
function updateProfilesDisplay(profiles, activeProfile) {
    const container = document.getElementById('profiles-container');
    if (!container) return;
    
    // Clear loading spinner
    container.innerHTML = '';
    
    // Create profile buttons
    Object.keys(profiles).forEach(profileId => {
        const profile = profiles[profileId];
        const isActive = profileId === activeProfile;
        
        let buttonClass = 'btn profile-button ';
        switch (profileId) {
            case 'aggressive': buttonClass += 'btn-success'; break;
            case 'conservative': buttonClass += 'btn-warning'; break;
            case 'defensive': buttonClass += 'btn-danger'; break;
            default: buttonClass += 'btn-primary';
        }
        
        if (isActive) {
            buttonClass += ' active';
        }
        
        const profileButton = `
            <button class="${buttonClass}" data-profile-id="${profileId}" onclick="applyProfile('${profileId}')">
                ${profileId.charAt(0).toUpperCase() + profileId.slice(1)}
                ${isActive ? '<i class="bi bi-check-circle-fill ms-2"></i>' : ''}
            </button>
        `;
        
        container.insertAdjacentHTML('beforeend', profileButton);
    });
}

// Update recent trades table
function updateRecentTradesTable(trades) {
    const tableBody = document.getElementById('recent-trades-table');
    if (!tableBody) return;
    
    // Clear table
    tableBody.innerHTML = '';
    
    // Add trade rows
    trades.forEach(trade => {
        const isProfitable = trade.pnl > 0;
        const rowClass = isProfitable ? 'trade-row profitable' : 'trade-row loss';
        
        const row = `
            <tr class="${rowClass}">
                <td>${formatDateTime(trade.timestamp)}</td>
                <td>${trade.symbol}</td>
                <td>
                    <span class="badge ${trade.side === 'buy' ? 'bg-success' : 'bg-danger'}">
                        ${trade.side.toUpperCase()}
                    </span>
                </td>
                <td>${trade.entry_price}</td>
                <td>${trade.exit_price || '-'}</td>
                <td>${trade.quantity}</td>
                <td>${formatPnL(trade.pnl)}</td>
                <td>
                    <span class="badge ${getStatusBadgeClass(trade.status)}">
                        ${trade.status}
                    </span>
                </td>
                <td>${trade.strategy || '-'}</td>
            </tr>
        `;
        
        tableBody.insertAdjacentHTML('beforeend', row);
    });
}

// Get status badge class
function getStatusBadgeClass(status) {
    switch (status.toLowerCase()) {
        case 'open': return 'bg-primary';
        case 'closed': return 'bg-success';
        case 'cancelled': return 'bg-warning';
        case 'error': return 'bg-danger';
        default: return 'bg-secondary';
    }
}

// Update daily PnL chart
function updateDailyPnlChart(hourlyData) {
    const ctx = document.getElementById('daily-pnl-chart');
    if (!ctx) return;
    
    // Prepare chart data
    const hours = Object.keys(hourlyData).sort();
    const pnlValues = hours.map(hour => hourlyData[hour].net_pnl || 0);
    
    // Format hours for display
    const hourLabels = hours.map(hour => {
        const hourNum = parseInt(hour);
        return `${hourNum}:00`;
    });
    
    // Create or update chart
    if (dailyPnlChart) {
        dailyPnlChart.data.labels = hourLabels;
        dailyPnlChart.data.datasets[0].data = pnlValues;
        dailyPnlChart.update();
    } else {
        dailyPnlChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: hourLabels,
                datasets: [{
                    label: 'Hourly P&L (USDT)',
                    data: pnlValues,
                    backgroundColor: (context) => {
                        const value = context.dataset.data[context.dataIndex];
                        return value >= 0 ? 'rgba(40, 167, 69, 0.6)' : 'rgba(220, 53, 69, 0.6)';
                    },
                    borderColor: (context) => {
                        const value = context.dataset.data[context.dataIndex];
                        return value >= 0 ? 'rgb(40, 167, 69)' : 'rgb(220, 53, 69)';
                    },
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
}

// Apply parameter profile
async function applyProfile(profileId) {
    try {
        const response = await apiRequest(`profiles/${profileId}/apply`, {
            method: 'POST',
            body: JSON.stringify({
                reason: 'Manual application via dashboard'
            })
        });
        
        if (response.success) {
            showToast('Profile Applied', `Successfully applied ${profileId} profile`, 'success');
            
            // Update parameters and profiles
            fetchParameters();
        }
    } catch (error) {
        console.error('Error applying profile:', error);
    }
}
