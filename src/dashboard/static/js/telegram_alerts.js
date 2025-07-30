/**
 * Telegram Alert Module for Regime Analytics Dashboard
 * --------------------------------------------------
 * Handles sending real-time alerts to Telegram for:
 * - Top-performing regime detection
 * - Playbook matches
 * - Confidence threshold surpassing
 * - Regime changes
 */

/**
 * Send alert to Telegram
 * @param {Object} alertData - Alert data object containing type, title, message, and data
 * @returns {Promise} - Promise that resolves with the alert result
 */
/**
 * Send alert to Telegram with inline action buttons
 * @param {Object} alertData - Alert data object containing type, title, message, and data
 * @returns {Promise} - Promise that resolves with the alert result
 */
async function sendTelegramAlert(alertData) {
    // First check if alert should be sent based on user settings
    if (shouldSendAlert && typeof shouldSendAlert === 'function' && !shouldSendAlert(alertData)) {
        console.log('Alert suppressed by user settings:', alertData.type);
        return false;
    }
    
    // Check if this is a duplicate alert we should suppress
    if (shouldSuppressAlert(alertData)) {
        console.log('Suppressing duplicate alert:', alertData.type);
        return false;
    }
    
    // Generate inline action buttons based on alert type
    const actionButtons = generateActionButtons(alertData);
    
    try {
        const response = await fetch(`${DASHBOARD_CONFIG.apiUrl}/api/v1/telegram/alert`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: alertData.title,
                message: alertData.message,
                alert_type: alertData.type,
                metadata: alertData.data || {},
                action_buttons: actionButtons
            })
        });
        
        if (!response.ok) {
            throw new Error(`Failed to send Telegram alert: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        // Cache alert to prevent duplicates
        cacheAlert(alertData);
        
        console.log('Telegram alert sent successfully:', result);
        return true;
    } catch (error) {
        console.error('Error sending Telegram alert:', error);
        return false;
    }
}

/**
 * Determine if we should suppress a duplicate alert
 * @param {Object} alertData - Alert data object
 * @returns {Boolean} - Whether to suppress the alert
 */
function shouldSuppressAlert(alertData) {
    const now = Date.now();
    const alertKey = generateAlertKey(alertData);
    
    // Check if this alert was sent recently
    if (state.telegramAlertHistory[alertKey]) {
        const timeSinceLastAlert = now - state.telegramAlertHistory[alertKey];
        
        // Different cooldown periods based on alert type
        let cooldown = 300000; // Default 5 minutes
        
        switch (alertData.type) {
            case 'regime_change':
                cooldown = 120000; // 2 minutes
                break;
            case 'high_performer':
                cooldown = 1800000; // 30 minutes
                break;
            case 'playbook_match':
                cooldown = 300000; // 5 minutes
                break;
            case 'confidence_threshold':
                cooldown = 600000; // 10 minutes
                break;
        }
        
        // Suppress if within cooldown period
        if (timeSinceLastAlert < cooldown) {
            return true;
        }
    }
    
    return false;
}

/**
 * Cache alert to prevent duplicates
 * @param {Object} alertData - Alert data object
 */
function cacheAlert(alertData) {
    const alertKey = generateAlertKey(alertData);
    state.telegramAlertHistory[alertKey] = Date.now();
    
    // Clean up old cache entries
    cleanAlertCache();
}

/**
 * Generate a unique key for an alert
 * @param {Object} alertData - Alert data object
 * @returns {String} - Unique key
 */
function generateAlertKey(alertData) {
    // Create a unique identifier based on alert type and content
    switch (alertData.type) {
        case 'regime_change':
            return `regime_change_${alertData.data?.regime}`;
        case 'high_performer':
            return `high_performer_${alertData.data?.regime_type}_${Date.now().toString().slice(0, -5)}`;
        case 'playbook_match':
            return `playbook_match_${alertData.data?.id}_${Date.now().toString().slice(0, -5)}`;
        case 'confidence_threshold':
            return `confidence_${alertData.data?.regime}_${Date.now().toString().slice(0, -5)}`;
        default:
            return `${alertData.type}_${Date.now().toString().slice(0, -3)}`;
    }
}

/**
 * Clean up old cache entries
 */
function cleanAlertCache() {
    const now = Date.now();
    const oldestAllowed = now - 7200000; // 2 hours
    
    // Remove entries older than 2 hours
    Object.keys(state.telegramAlertHistory).forEach(key => {
        if (state.telegramAlertHistory[key] < oldestAllowed) {
            delete state.telegramAlertHistory[key];
        }
    });
}

/**
 * Generate inline action buttons for Telegram alerts based on alert type
 * @param {Object} alertData - Alert data object
 * @returns {Array} - Array of action button objects
 */
function generateActionButtons(alertData) {
    const baseUrl = window.location.origin;
    const buttons = [];
    
    // Common "View Dashboard" button for all alerts
    buttons.push({
        text: "📊 View Dashboard",
        url: `${baseUrl}/dashboard/performance`
    });
    
    // Type-specific buttons
    switch (alertData.type) {
        case 'regime_change':
            // Add button to view regime details
            if (alertData.data && alertData.data.id) {
                buttons.push({
                    text: "🔍 View Regime Details",
                    url: `${baseUrl}/dashboard/performance#regime-${alertData.data.id}`
                });
            }
            break;
            
        case 'high_performer':
            // Add button to view performance details
            if (alertData.data && alertData.data.id) {
                buttons.push({
                    text: "📈 View Performance",
                    url: `${baseUrl}/dashboard/performance#performer-${alertData.data.id}`
                });
            }
            break;
            
        case 'playbook_match':
            // Add button to view playbook details
            if (alertData.data && alertData.data.id) {
                buttons.push({
                    text: "📘 View Playbook",
                    url: `${baseUrl}/dashboard/performance#playbook-${alertData.data.id}`
                });
            }
            break;
            
        case 'confidence_threshold':
            // Add button to view current regime
            buttons.push({
                text: "🎯 View Current Regime",
                url: `${baseUrl}/dashboard/performance#current-regime`
            });
            break;
            
        case 'trade_execution':
            // Add button to view trade history
            if (alertData.data && alertData.data.id) {
                buttons.push({
                    text: "💹 View Trade",
                    url: `${baseUrl}/dashboard/trades#trade-${alertData.data.id}`
                });
            }
            break;
            
        case 'regime_snapshot':
            // Add button to view snapshot
            if (alertData.data && alertData.data.timestamp) {
                const timestamp = new Date(alertData.data.timestamp).getTime();
                buttons.push({
                    text: "📸 View Snapshot",
                    url: `${baseUrl}/dashboard/performance#snapshot-${timestamp}`
                });
            }
            break;
    }
    
    return buttons;
}

/**
 * Take a snapshot of the current regime and send it to Telegram
 * This includes market data, charts, and analytics
 */
function takeRegimeSnapshot() {
    if (!state.currentRegime) {
        showToast('No current regime data available for snapshot', 'warning');
        return;
    }
    
    showLoading('Creating regime snapshot...');
    
    // Prepare snapshot data
    const snapshotData = {
        regime: state.currentRegime.regime,
        confidence: state.currentRegime.confidence,
        start_time: state.currentRegime.start_time,
        metrics: state.currentRegime.metrics || {},
        market_context: {
            adx: state.currentRegime.metrics?.adx,
            rsi: state.currentRegime.metrics?.rsi,
            volatility: state.currentRegime.metrics?.volatility,
            trend_direction: state.currentRegime.metrics?.trend_direction,
            market_phase: state.currentRegime.metrics?.market_phase
        },
        matching_playbooks: state.matchingPlaybooks.map(p => p.name),
        timestamp: new Date().toISOString(),
        snapshot_type: 'manual'
    };
    
    // Send the snapshot to the API
    fetch(`${DASHBOARD_CONFIG.apiUrl}/api/v1/regime/snapshot`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(snapshotData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Send snapshot to Telegram as well
            sendTelegramAlert({
                type: 'regime_snapshot',
                title: '📊 Regime Snapshot Created',
                message: `${state.currentRegime.regime} | Confidence: ${(state.currentRegime.confidence * 100).toFixed(0)}% | ${formatDateTime(new Date())}`,
                data: snapshotData
            });
            
            showToast('Regime snapshot created and sent to Telegram', 'success');
        } else {
            showToast(`Error creating snapshot: ${data.error}`, 'error');
        }
        hideLoading();
    })
    .catch(error => {
        console.error('Error creating regime snapshot:', error);
        showToast('Failed to create regime snapshot', 'error');
        hideLoading();
    });
}

/**
 * Send trade alert to Telegram with regime context
 * @param {Object} tradeData - Trade data object
 */
function sendTradeAlert(tradeData) {
    if (!DASHBOARD_CONFIG.telegram.enableAlerts) {
        return false;
    }
    
    // Get current regime context
    const regimeContext = state.currentRegime ? 
        `Regime: ${state.currentRegime.regime} (${(state.currentRegime.confidence * 100).toFixed(0)}%)` : 
        'No regime data';
    
    // Create trade alert
    const direction = tradeData.direction.toUpperCase();
    const symbol = tradeData.symbol;
    const price = tradeData.entry_price;
    const emoji = direction === 'BUY' ? '🟢' : '🔴';
    
    // Check if there's a matching playbook
    let playbookInfo = '';
    if (state.matchingPlaybooks && state.matchingPlaybooks.length > 0) {
        const topPlaybook = state.matchingPlaybooks[0];
        playbookInfo = `\nPlaybook: "${topPlaybook.name}" (${(topPlaybook.confidence_threshold * 100).toFixed(0)}% match)`;
    }
    
    sendTelegramAlert({
        type: 'trade_execution',
        title: `${emoji} ${direction} Signal Executed`,
        message: `${symbol} @ ${price}\n${regimeContext}${playbookInfo}`,
        data: tradeData
    });
    
    return true;
}
