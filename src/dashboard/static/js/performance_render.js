/**
 * Performance Analytics Rendering Module
 * -------------------------------------
 * Handles UI rendering and chart generation for the
 * regime performance analytics dashboard
 */

/**
 * Render the top performers table
 */
function renderTopPerformers() {
    const tableBody = document.getElementById('top-performers-table');
    
    if (!state.topPerformers || state.topPerformers.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center">No performance data available yet.</td>
            </tr>
        `;
        return;
    }
    
    // Clear existing content
    tableBody.innerHTML = '';
    
    // Add rows for each top performer
    state.topPerformers.forEach(entry => {
        // Create regime tag class based on regime type
        const regimeClass = getRegimeTagClass(entry.regime_type);
        
        // Create confidence badge style based on confidence value
        const confidenceStyle = getConfidenceBadgeStyle(entry.confidence);
        
        // Format ROI with + or - sign
        const roiFormatted = formatPercentage(entry.roi_pct);
        const roiClass = entry.roi_pct >= 0 ? 'positive-value' : 'negative-value';
        
        // Create pattern score bar
        const patternScoreHtml = entry.pattern_score ? `
            <div class="pattern-score-bar">
                <div class="pattern-score-fill" style="width: ${entry.pattern_score * 100}%"></div>
            </div>
            ${(entry.pattern_score * 100).toFixed(0)}%
        ` : 'N/A';
        
        // Create row HTML
        const row = document.createElement('tr');
        row.className = 'performance-row';
        row.innerHTML = `
            <td>
                <span class="regime-tag ${regimeClass}">${entry.regime_type}</span>
            </td>
            <td>
                <div class="confidence-badge" style="${confidenceStyle}">
                    ${(entry.confidence * 100).toFixed(0)}%
                </div>
            </td>
            <td class="${roiClass}">${roiFormatted}</td>
            <td>${formatPercentage(entry.win_rate)}</td>
            <td>
                ${entry.market_phase ? `<span class="market-phase-badge">${entry.market_phase}</span>` : 'N/A'}
            </td>
            <td>${patternScoreHtml}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary view-performance" data-id="${entry.id}">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-success create-playbook" data-id="${entry.id}">
                    <i class="fas fa-book"></i>
                </button>
            </td>
        `;
        
        // Add click event for viewing performance details
        row.querySelector('.view-performance').addEventListener('click', () => {
            showPerformanceDetails(entry.id);
        });
        
        // Add click event for creating playbook
        row.querySelector('.create-playbook').addEventListener('click', () => {
            showCreatePlaybookModal(entry.id);
        });
        
        tableBody.appendChild(row);
    });
    
    // Add pagination if needed
    updatePagination();
}

/**
 * Render playbooks list
 */
function renderPlaybooks() {
    const container = document.getElementById('playbooks-container');
    
    if (!state.playbooks || state.playbooks.length === 0) {
        container.innerHTML = `
            <div class="col-12 text-center py-5">
                <p class="text-muted">No playbooks available yet.</p>
                <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#createPlaybookModal">
                    <i class="fas fa-plus"></i> Create Your First Playbook
                </button>
            </div>
        `;
        return;
    }
    
    // Filter playbooks based on search and active filter
    const filteredPlaybooks = state.playbooks.filter(playbook => {
        // Apply search filter if exists
        if (state.currentFilters.search && !playbook.name.toLowerCase().includes(state.currentFilters.search) && 
            !playbook.regime_type.toLowerCase().includes(state.currentFilters.search)) {
            return false;
        }
        
        // Apply active only filter
        if (state.currentFilters.activeOnly && !playbook.is_active) {
            return false;
        }
        
        return true;
    });
    
    if (filteredPlaybooks.length === 0) {
        container.innerHTML = `
            <div class="col-12 text-center py-4">
                <p class="text-muted">No playbooks match your current filters.</p>
                <button class="btn btn-secondary" id="clear-filters-btn">
                    <i class="fas fa-times"></i> Clear Filters
                </button>
            </div>
        `;
        
        // Add click event for clearing filters
        document.getElementById('clear-filters-btn').addEventListener('click', () => {
            document.getElementById('playbook-search').value = '';
            document.getElementById('show-active-only').checked = true;
            state.currentFilters.search = '';
            state.currentFilters.activeOnly = true;
            renderPlaybooks();
        });
        return;
    }
    
    // Clear container
    container.innerHTML = '';
    
    // Add each playbook card
    filteredPlaybooks.forEach(playbook => {
        const cardClass = playbook.is_auto_generated ? 'auto-generated' : 'user-created';
        const activeClass = playbook.is_active ? 'text-success' : 'text-muted';
        const activeIcon = playbook.is_active ? 'fa-check-circle' : 'fa-times-circle';
        
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
        }
        
        // Create parameter tags
        let paramTags = '';
        if (playbook.strategy.parameter_settings) {
            const params = playbook.strategy.parameter_settings;
            for (const [key, value] of Object.entries(params)) {
                if (value !== null && value !== undefined) {
                    paramTags += `<span class="param-tag">${key}: ${value}</span>`;
                }
            }
        }
        
        // Create playbook card
        const playbookCard = document.createElement('div');
        playbookCard.className = 'col-md-6 col-lg-4';
        playbookCard.innerHTML = `
            <div class="playbook-card ${cardClass}">
                <div class="playbook-header">
                    <h5 class="mb-0">${playbook.name}</h5>
                    <div>
                        <span class="${activeClass}" title="${playbook.is_active ? 'Active' : 'Inactive'}">
                            <i class="fas ${activeIcon}"></i>
                        </span>
                    </div>
                </div>
                <div class="playbook-body">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="regime-tag ${getRegimeTagClass(playbook.regime_type)}">
                            ${playbook.regime_type}
                        </span>
                        ${ratingHtml}
                    </div>
                    <p class="text-muted small mb-3">${playbook.description || 'No description available.'}</p>
                    
                    <div class="playbook-strategy-section">
                        <h5><i class="fas fa-sign-in-alt"></i> Entry</h5>
                        <p class="small">${playbook.strategy.entry_conditions.split('\n')[0]}...</p>
                    </div>
                    
                    <div class="playbook-strategy-section">
                        <h5><i class="fas fa-sign-out-alt"></i> Exit</h5>
                        <p class="small">${playbook.strategy.exit_conditions.split('\n')[0]}...</p>
                    </div>
                    
                    <div class="mt-3">
                        ${paramTags}
                    </div>
                </div>
                <div class="playbook-footer">
                    <div>
                        <small class="text-muted">Min. Confidence: ${(playbook.confidence_threshold * 100).toFixed(0)}%</small>
                    </div>
                    <div>
                        <button class="btn btn-sm btn-outline-primary view-playbook" data-id="${playbook.id}">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-success apply-playbook" data-id="${playbook.id}" 
                            ${!playbook.is_active ? 'disabled' : ''}>
                            <i class="fas fa-check"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Add click event for viewing playbook details
        playbookCard.querySelector('.view-playbook').addEventListener('click', () => {
            showPlaybookDetails(playbook.id);
        });
        
        // Add click event for applying playbook
        playbookCard.querySelector('.apply-playbook').addEventListener('click', () => {
            if (playbook.is_active) {
                applyPlaybook(playbook.id);
            }
        });
        
        container.appendChild(playbookCard);
    });
}

/**
 * Render current regime status
 */
function renderCurrentRegimeStatus() {
    if (!state.currentRegime) {
        // Hide elements if no regime data available
        document.getElementById('current-regime-confidence').innerText = 'N/A';
        document.getElementById('current-regime-type').innerText = 'No regime data available';
        document.getElementById('current-regime-start').innerText = 'N/A';
        document.getElementById('current-regime-duration').innerText = 'N/A';
        document.getElementById('current-regime-phase').innerText = 'N/A';
        return;
    }
    
    // Update regime information
    const confidenceBadge = document.getElementById('current-regime-confidence');
    confidenceBadge.innerText = `${(state.currentRegime.confidence * 100).toFixed(0)}%`;
    confidenceBadge.style.backgroundColor = getConfidenceColor(state.currentRegime.confidence);
    confidenceBadge.style.color = 'white';
    
    document.getElementById('current-regime-type').innerText = state.currentRegime.regime;
    document.getElementById('current-regime-start').innerText = formatDateTime(state.currentRegime.start_time);
    
    const duration = calculateDuration(new Date(state.currentRegime.start_time), new Date());
    document.getElementById('current-regime-duration').innerText = duration;
    
    document.getElementById('current-regime-phase').innerText = 
        state.currentRegime.metrics?.market_phase || 'Unknown';
    
    // Add regime tag class
    const regimeTag = document.getElementById('current-regime-type');
    regimeTag.className = ''; // Clear existing classes
    regimeTag.classList.add(getRegimeTagClass(state.currentRegime.regime).replace('tag-', ''));
}

/**
 * Render matching playbooks for current regime
 */
function renderMatchingPlaybooks() {
    const container = document.getElementById('matching-playbooks');
    
    if (!state.matchingPlaybooks || state.matchingPlaybooks.length === 0) {
        container.innerHTML = `
            <p class="text-muted text-center">No matching playbooks found for current regime.</p>
        `;
        return;
    }
    
    // Clear container
    container.innerHTML = '';
    
    // Add each matching playbook
    state.matchingPlaybooks.forEach((playbook, index) => {
        const card = document.createElement('div');
        card.className = 'mb-3 playbook-card';
        card.innerHTML = `
            <div class="playbook-header">
                <h6 class="mb-0">${playbook.name}</h6>
                <span class="badge bg-primary">${(playbook.confidence_threshold * 100).toFixed(0)}% match</span>
            </div>
            <div class="playbook-body p-2">
                <small class="text-muted">Entry: ${playbook.strategy.entry_conditions.split('\n')[0]}...</small>
            </div>
            <div class="playbook-footer p-2">
                <button class="btn btn-sm btn-outline-success apply-matching-playbook" data-id="${playbook.id}">
                    Apply
                </button>
                <button class="btn btn-sm btn-outline-primary view-matching-playbook" data-id="${playbook.id}">
                    Details
                </button>
            </div>
        `;
        
        // Add click events
        card.querySelector('.apply-matching-playbook').addEventListener('click', () => {
            applyPlaybook(playbook.id);
        });
        
        card.querySelector('.view-matching-playbook').addEventListener('click', () => {
            showPlaybookDetails(playbook.id);
        });
        
        container.appendChild(card);
        
        // Add separator if not last item
        if (index < state.matchingPlaybooks.length - 1) {
            container.appendChild(document.createElement('hr'));
        }
    });
}

/**
 * Setup charts for performance visualization
 */
function setupCharts() {
    // Timeline chart
    const timelineCtx = document.getElementById('regime-timeline-chart');
    state.charts.timeline = new Chart(timelineCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Regime Timeline',
                data: [],
                backgroundColor: [],
                borderColor: [],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const entry = state.performanceEntries[context.dataIndex];
                            if (!entry) return '';
                            
                            const lines = [
                                `Regime: ${entry.regime_type}`,
                                `Confidence: ${(entry.confidence * 100).toFixed(1)}%`,
                                `Duration: ${calculateDuration(new Date(entry.start_time), new Date(entry.end_time))}`,
                                `ROI: ${formatPercentage(entry.performance.roi_pct)}`
                            ];
                            
                            if (entry.market_context.adx) {
                                lines.push(`ADX: ${entry.market_context.adx.toFixed(1)}`);
                            }
                            
                            if (entry.market_context.volatility) {
                                lines.push(`Volatility: ${entry.market_context.volatility.toFixed(4)}`);
                            }
                            
                            if (entry.market_context.trend_direction) {
                                lines.push(`Trend: ${entry.market_context.trend_direction}`);
                            }
                            
                            return lines;
                        }
                    }
                },
                legend: {
                    display: false
                },
                zoom: {
                    zoom: {
                        wheel: {
                            enabled: true
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'x'
                    },
                    pan: {
                        enabled: true,
                        mode: 'x'
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: {
                        display: false
                    },
                    ticks: {
                        callback: function(value, index) {
                            // Show fewer x-axis labels for clarity
                            const totalLabels = this.getLabelForValue.length;
                            if (totalLabels > 10) {
                                return index % Math.ceil(totalLabels / 10) === 0 ? 
                                    this.getLabelForValue(value) : '';
                            }
                            return this.getLabelForValue(value);
                        }
                    }
                },
                y: {
                    stacked: true,
                    display: false
                }
            }
        }
    });
    
    // Regime comparison chart
    const comparisonCtx = document.getElementById('regime-comparison-chart');
    state.charts.comparison = new Chart(comparisonCtx, {
        type: 'bar',
        data: {
            labels: ['Strong Uptrend', 'Strong Downtrend', 'Ranging', 'High Volatility', 'Transition'],
            datasets: [
                {
                    label: 'Average ROI',
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: 'rgba(59, 130, 246, 0.7)'
                },
                {
                    label: 'Win Rate',
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: 'rgba(16, 185, 129, 0.7)'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const datasetLabel = context.dataset.label;
                            return `${datasetLabel}: ${datasetLabel.includes('ROI') ? 
                                formatPercentage(value) : (value * 100).toFixed(1) + '%'}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatPercentage(value);
                        }
                    }
                }
            }
        }
    });
    
    // Confidence vs Performance chart
    const confidenceCtx = document.getElementById('confidence-performance-chart');
    state.charts.confidencePerformance = new Chart(confidenceCtx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Regime Performance',
                data: [],
                backgroundColor: function(context) {
                    if (!context.raw) return 'rgba(59, 130, 246, 0.7)';
                    
                    // Color based on regime type
                    const regimeType = context.raw.regime_type;
                    return getRegimeColor(regimeType);
                },
                pointRadius: 8,
                pointHoverRadius: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const point = context.raw;
                            if (!point) return '';
                            
                            return [
                                `Regime: ${point.regime_type}`,
                                `Confidence: ${(point.x * 100).toFixed(1)}%`,
                                `ROI: ${formatPercentage(point.y)}`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Confidence'
                    },
                    min: 0,
                    max: 1,
                    ticks: {
                        callback: function(value) {
                            return (value * 100).toFixed(0) + '%';
                        }
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'ROI'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatPercentage(value);
                        }
                    }
                }
            }
        }
    });
}
