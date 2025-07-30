/**
 * Performance Analytics API Service
 * --------------------------------
 * Handles all API calls for the regime performance and playbook features
 */

/**
 * Load all performance entries from the API
 */
async function loadPerformanceEntries() {
    showLoading('Loading performance data...');
    
    try {
        const response = await fetch(`${DASHBOARD_CONFIG.apiUrl}/api/v1/performance/entries`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch performance entries: ${response.statusText}`);
        }
        
        const data = await response.json();
        state.performanceEntries = data;
        
        // Update charts and stats
        updatePerformanceStats();
        updateTimelineChart();
        updatePerformanceCharts();
        
        hideLoading();
    } catch (error) {
        console.error('Error loading performance entries:', error);
        showToast(`Error loading performance data: ${error.message}`, 'danger');
        hideLoading();
    }
}

/**
 * Load top performing regimes
 */
async function loadTopPerformers() {
    try {
        const response = await fetch(`${DASHBOARD_CONFIG.apiUrl}/api/v1/performance/top?limit=${state.pageSize}`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch top performers: ${response.statusText}`);
        }
        
        const data = await response.json();
        state.topPerformers = data;
        
        // Render top performers table
        renderTopPerformers();
    } catch (error) {
        console.error('Error loading top performers:', error);
        showToast(`Error loading top performers: ${error.message}`, 'danger');
    }
}

/**
 * Load all playbooks
 */
async function loadPlaybooks() {
    try {
        const response = await fetch(`${DASHBOARD_CONFIG.apiUrl}/api/v1/performance/playbooks`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch playbooks: ${response.statusText}`);
        }
        
        const data = await response.json();
        state.playbooks = data;
        
        // Render playbooks
        renderPlaybooks();
    } catch (error) {
        console.error('Error loading playbooks:', error);
        showToast(`Error loading playbooks: ${error.message}`, 'danger');
    }
}

/**
 * Load current regime status
 */
async function loadCurrentRegimeStatus() {
    try {
        const response = await fetch(`${DASHBOARD_CONFIG.apiUrl}/api/v1/market/current_regime`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch current regime: ${response.statusText}`);
        }
        
        const data = await response.json();
        state.currentRegime = data;
        
        // Render current regime
        renderCurrentRegimeStatus();
        
        // Also load matching playbooks
        await loadMatchingPlaybooks();
    } catch (error) {
        console.error('Error loading current regime status:', error);
        showToast(`Error loading current regime: ${error.message}`, 'danger');
    }
}

/**
 * Load playbooks that match current regime
 */
async function loadMatchingPlaybooks() {
    if (!state.currentRegime) {
        return;
    }
    
    try {
        const response = await fetch(`${DASHBOARD_CONFIG.apiUrl}/api/v1/performance/matching_playbooks`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch matching playbooks: ${response.statusText}`);
        }
        
        const data = await response.json();
        state.matchingPlaybooks = data;
        
        // Render matching playbooks
        renderMatchingPlaybooks();
    } catch (error) {
        console.error('Error loading matching playbooks:', error);
        showToast(`Error loading matching playbooks: ${error.message}`, 'danger');
    }
}

/**
 * Create a new playbook manually
 */
async function createPlaybook(playbookData) {
    showLoading('Creating playbook...');
    
    try {
        const response = await fetch(`${DASHBOARD_CONFIG.apiUrl}/api/v1/performance/playbooks`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(playbookData)
        });
        
        if (!response.ok) {
            throw new Error(`Failed to create playbook: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Add to local state
        state.playbooks.push(data);
        
        // Refresh playbooks display
        renderPlaybooks();
        
        // Show success message
        showToast('Playbook created successfully!', 'success');
        hideLoading();
        
        return true;
    } catch (error) {
        console.error('Error creating playbook:', error);
        showToast(`Error creating playbook: ${error.message}`, 'danger');
        hideLoading();
        
        return false;
    }
}

/**
 * Create a playbook from performance entry
 */
async function createPlaybookFromPerformance(performanceId) {
    showLoading('Generating playbook...');
    
    try {
        const response = await fetch(`${DASHBOARD_CONFIG.apiUrl}/api/v1/performance/generate_playbook/${performanceId}`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`Failed to generate playbook: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Add to local state
        state.playbooks.push(data);
        
        // Refresh playbooks display
        renderPlaybooks();
        
        // Show success message
        showToast('Playbook generated successfully!', 'success');
        hideLoading();
        
        // Close performance details modal if open
        const performanceModal = bootstrap.Modal.getInstance(document.getElementById('performanceDetailsModal'));
        if (performanceModal) {
            performanceModal.hide();
        }
        
        // Switch to playbooks tab
        document.getElementById('playbooks-tab').click();
        
        return true;
    } catch (error) {
        console.error('Error generating playbook:', error);
        showToast(`Error generating playbook: ${error.message}`, 'danger');
        hideLoading();
        
        return false;
    }
}

/**
 * Update playbook active status
 */
async function updatePlaybookActive(playbookId, isActive) {
    try {
        const response = await fetch(`${DASHBOARD_CONFIG.apiUrl}/api/v1/performance/playbooks/${playbookId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ is_active: isActive })
        });
        
        if (!response.ok) {
            throw new Error(`Failed to update playbook: ${response.statusText}`);
        }
        
        // Update in local state
        const playbook = state.playbooks.find(p => p.id === playbookId);
        if (playbook) {
            playbook.is_active = isActive;
        }
        
        // Refresh playbooks display
        renderPlaybooks();
        
        // Show success message
        showToast(`Playbook ${isActive ? 'activated' : 'deactivated'} successfully!`, 'success');
        
        return true;
    } catch (error) {
        console.error('Error updating playbook:', error);
        showToast(`Error updating playbook: ${error.message}`, 'danger');
        
        return false;
    }
}

/**
 * Apply playbook to current regime
 */
async function applyPlaybook(playbookId) {
    showLoading('Applying playbook...');
    
    try {
        const response = await fetch(`${DASHBOARD_CONFIG.apiUrl}/api/v1/performance/apply_playbook/${playbookId}`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`Failed to apply playbook: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Show success message with details
        showToast(`Playbook applied successfully! ${data.message || ''}`, 'success');
        hideLoading();
        
        return true;
    } catch (error) {
        console.error('Error applying playbook:', error);
        showToast(`Error applying playbook: ${error.message}`, 'danger');
        hideLoading();
        
        return false;
    }
}

/**
 * Rate a playbook (1-5 stars)
 */
async function ratePlaybook(playbookId, rating) {
    try {
        const response = await fetch(`${DASHBOARD_CONFIG.apiUrl}/api/v1/performance/playbooks/${playbookId}/rate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ rating })
        });
        
        if (!response.ok) {
            throw new Error(`Failed to rate playbook: ${response.statusText}`);
        }
        
        // Update in local state
        const playbook = state.playbooks.find(p => p.id === playbookId);
        if (playbook) {
            playbook.user_rating = rating;
        }
        
        // Show success message
        showToast('Rating updated successfully!', 'success');
        
        return true;
    } catch (error) {
        console.error('Error rating playbook:', error);
        showToast(`Error updating rating: ${error.message}`, 'danger');
        
        return false;
    }
}

/**
 * Export performance data to CSV
 */
function exportPerformanceData() {
    if (!state.performanceEntries || state.performanceEntries.length === 0) {
        showToast('No performance data to export', 'warning');
        return;
    }
    
    // Define CSV header
    let csvContent = 'Regime Type,Start Time,End Time,Duration,Confidence,ROI (%),Win Rate (%),Trade Count,Avg Profit (%),Max Drawdown (%),ADX,Volatility,Market Phase,Preceding Regime,Pattern Score\n';
    
    // Add each row
    state.performanceEntries.forEach(entry => {
        const startDate = new Date(entry.start_time);
        const endDate = entry.end_time ? new Date(entry.end_time) : new Date();
        const duration = calculateDuration(startDate, endDate);
        
        const row = [
            `"${entry.regime_type}"`,
            `"${formatDateTime(entry.start_time)}"`,
            `"${entry.end_time ? formatDateTime(entry.end_time) : 'Ongoing'}"`,
            `"${duration}"`,
            entry.confidence,
            entry.performance.roi_pct,
            entry.performance.win_rate,
            entry.performance.trade_count,
            entry.performance.avg_profit_pct,
            entry.performance.max_drawdown_pct,
            entry.market_context.adx || '',
            entry.market_context.volatility || '',
            `"${entry.market_context.market_phase || ''}"`,
            `"${entry.market_context.preceding_regime || ''}"`,
            entry.pattern_analysis.pattern_score || ''
        ];
        
        csvContent += row.join(',') + '\n';
    });
    
    // Create and download CSV file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    link.setAttribute('href', url);
    link.setAttribute('download', `regime_performance_${formatDate(new Date())}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast('Performance data exported successfully!', 'success');
}

/**
 * Export playbooks to JSON
 */
function exportPlaybooks() {
    if (!state.playbooks || state.playbooks.length === 0) {
        showToast('No playbooks to export', 'warning');
        return;
    }
    
    // Filter out internal fields and prepare export data
    const exportData = state.playbooks.map(playbook => {
        const { id, created_at, updated_at, ...exportPlaybook } = playbook;
        return exportPlaybook;
    });
    
    // Create and download JSON file
    const blob = new Blob([JSON.stringify(exportData, null, 2)], 
        { type: 'application/json;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    link.setAttribute('href', url);
    link.setAttribute('download', `playbooks_${formatDate(new Date())}.json`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast('Playbooks exported successfully!', 'success');
}

/**
 * Import playbooks from JSON file
 */
function importPlaybooks(file) {
    if (!file) {
        showToast('No file selected', 'warning');
        return;
    }
    
    const reader = new FileReader();
    
    reader.onload = async function(e) {
        try {
            const playbooks = JSON.parse(e.target.result);
            
            if (!Array.isArray(playbooks)) {
                throw new Error('Invalid playbooks file format. Expected an array.');
            }
            
            showLoading(`Importing ${playbooks.length} playbooks...`);
            
            // Import each playbook
            const response = await fetch(`${DASHBOARD_CONFIG.apiUrl}/api/v1/performance/import_playbooks`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(playbooks)
            });
            
            if (!response.ok) {
                throw new Error(`Failed to import playbooks: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Reload playbooks
            await loadPlaybooks();
            
            showToast(`Imported ${result.imported} playbooks successfully!`, 'success');
            hideLoading();
        } catch (error) {
            console.error('Error importing playbooks:', error);
            showToast(`Error importing playbooks: ${error.message}`, 'danger');
            hideLoading();
        }
    };
    
    reader.readAsText(file);
}
