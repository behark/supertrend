// Apply filters to trade data
function applyFilters() {
    // Get filter values
    const dateRange = document.getElementById('date-range-filter').value;
    const symbol = document.getElementById('symbol-filter').value;
    const direction = document.getElementById('direction-filter').value;
    const strategy = document.getElementById('strategy-filter').value;
    const result = document.getElementById('result-filter').value;
    const exitType = document.getElementById('exit-type-filter').value;
    
    // Start with all trades
    let filtered = [...allTrades];
    
    // Apply date filter
    if (dateRange !== 'all') {
        const now = new Date();
        let startDate;
        
        switch (dateRange) {
            case 'today':
                startDate = new Date(now.setHours(0, 0, 0, 0));
                break;
            case 'week':
                startDate = new Date(now);
                startDate.setDate(now.getDate() - now.getDay());
                startDate.setHours(0, 0, 0, 0);
                break;
            case 'month':
                startDate = new Date(now.getFullYear(), now.getMonth(), 1);
                break;
            case 'custom':
                const startDateInput = document.getElementById('start-date-filter').value;
                const endDateInput = document.getElementById('end-date-filter').value;
                
                if (startDateInput) {
                    startDate = new Date(startDateInput);
                    startDate.setHours(0, 0, 0, 0);
                }
                
                if (endDateInput) {
                    const endDate = new Date(endDateInput);
                    endDate.setHours(23, 59, 59, 999);
                    
                    filtered = filtered.filter(trade => {
                        const tradeDate = new Date(trade.entry_time);
                        return tradeDate >= startDate && tradeDate <= endDate;
                    });
                    
                    // Skip the default date filter below
                    startDate = null;
                }
                break;
        }
        
        if (startDate) {
            filtered = filtered.filter(trade => {
                return new Date(trade.entry_time) >= startDate;
            });
        }
    }
    
    // Apply symbol filter
    if (symbol !== 'all') {
        filtered = filtered.filter(trade => trade.symbol === symbol);
    }
    
    // Apply direction filter
    if (direction !== 'all') {
        filtered = filtered.filter(trade => trade.direction === direction);
    }
    
    // Apply strategy filter
    if (strategy !== 'all') {
        filtered = filtered.filter(trade => {
            if (strategy === 'supertrend_adx') {
                return trade.strategy && trade.strategy.includes('SuperTrend');
            } else if (strategy === 'inside_bar') {
                return trade.strategy && trade.strategy.includes('Inside Bar');
            }
            return true;
        });
    }
    
    // Apply result filter
    if (result !== 'all') {
        filtered = filtered.filter(trade => {
            const isWin = (trade.profit_percent || 0) > 0;
            return result === 'win' ? isWin : !isWin;
        });
    }
    
    // Apply exit type filter
    if (exitType !== 'all') {
        filtered = filtered.filter(trade => trade.exit_type === exitType);
    }
    
    // Update filtered trades
    filteredTrades = filtered;
    
    // Update filter badges
    updateFilterBadges();
    
    // Reset to first page and update trade table
    currentPage = 1;
    updateTradeTable();
}

// Update filter badges display
function updateFilterBadges() {
    const badgeContainer = document.getElementById('filter-badges');
    const activeFiltersSection = document.getElementById('active-filters');
    
    if (!badgeContainer || !activeFiltersSection) return;
    
    // Clear current badges
    badgeContainer.innerHTML = '';
    
    // Get filter values
    const filters = {
        'Date Range': document.getElementById('date-range-filter').value,
        'Symbol': document.getElementById('symbol-filter').value,
        'Direction': document.getElementById('direction-filter').value,
        'Strategy': document.getElementById('strategy-filter').value,
        'Result': document.getElementById('result-filter').value,
        'Exit Type': document.getElementById('exit-type-filter').value
    };
    
    // Custom date range
    if (filters['Date Range'] === 'custom') {
        const startDate = document.getElementById('start-date-filter').value;
        const endDate = document.getElementById('end-date-filter').value;
        
        if (startDate && endDate) {
            filters['Date Range'] = `${startDate} to ${endDate}`;
        } else if (startDate) {
            filters['Date Range'] = `From ${startDate}`;
        } else if (endDate) {
            filters['Date Range'] = `Until ${endDate}`;
        }
    }
    
    // Create badges for active filters
    let hasActiveFilters = false;
    
    Object.entries(filters).forEach(([filterName, value]) => {
        if (value !== 'all') {
            hasActiveFilters = true;
            
            // Format display value
            let displayValue = value;
            if (filterName === 'Strategy') {
                if (value === 'supertrend_adx') displayValue = 'SuperTrend+ADX';
                if (value === 'inside_bar') displayValue = 'Inside Bar';
            }
            
            // Create badge
            const badge = document.createElement('span');
            badge.className = 'filter-badge';
            badge.innerHTML = `
                ${filterName}: ${displayValue}
                <span class="close" data-filter="${filterName}">&times;</span>
            `;
            
            badgeContainer.appendChild(badge);
            
            // Add click handler to remove filter
            const closeBtn = badge.querySelector('.close');
            closeBtn.addEventListener('click', () => {
                removeFilter(filterName);
            });
        }
    });
    
    // Show/hide active filters section
    activeFiltersSection.style.display = hasActiveFilters ? 'block' : 'none';
}

// Remove a single filter
function removeFilter(filterName) {
    // Map filter name to element ID
    const filterMap = {
        'Date Range': 'date-range-filter',
        'Symbol': 'symbol-filter',
        'Direction': 'direction-filter',
        'Strategy': 'strategy-filter',
        'Result': 'result-filter',
        'Exit Type': 'exit-type-filter'
    };
    
    const elementId = filterMap[filterName];
    
    if (elementId) {
        // Reset to default value
        const element = document.getElementById(elementId);
        if (element) {
            element.value = 'all';
            
            // If date range, hide custom fields
            if (elementId === 'date-range-filter') {
                document.getElementById('custom-date-range').style.display = 'none';
                
                // Clear date inputs
                document.getElementById('start-date-filter').value = '';
                document.getElementById('end-date-filter').value = '';
            }
        }
    }
    
    // Reapply filters
    applyFilters();
}

// Clear all filters
function clearFilters() {
    // Reset all filter selects to default
    document.getElementById('date-range-filter').value = 'all';
    document.getElementById('symbol-filter').value = 'all';
    document.getElementById('direction-filter').value = 'all';
    document.getElementById('strategy-filter').value = 'all';
    document.getElementById('result-filter').value = 'all';
    document.getElementById('exit-type-filter').value = 'all';
    
    // Hide custom date range
    document.getElementById('custom-date-range').style.display = 'none';
    
    // Clear date inputs
    document.getElementById('start-date-filter').value = '';
    document.getElementById('end-date-filter').value = '';
    
    // Reset filtered trades to all trades
    filteredTrades = [...allTrades];
    
    // Update badges
    updateFilterBadges();
    
    // Reset to first page and update table
    currentPage = 1;
    updateTradeTable();
    
    // Show toast notification
    showToast('Filters Cleared', 'All trade filters have been reset', 'info');
}

// Update trade table with filtered and paginated data
function updateTradeTable() {
    const tableBody = document.getElementById('trades-table').querySelector('tbody');
    const noTradesMsg = document.getElementById('no-trades-message');
    
    if (!tableBody || !noTradesMsg) return;
    
    // Clear table
    tableBody.innerHTML = '';
    
    // Check if there are any trades
    if (filteredTrades.length === 0) {
        noTradesMsg.style.display = 'block';
        
        // Update pagination
        updatePagination(0);
        return;
    }
    
    // Hide no trades message
    noTradesMsg.style.display = 'none';
    
    // Calculate pagination
    const total = filteredTrades.length;
    const start = (currentPage - 1) * pageSize;
    const end = Math.min(start + pageSize, total);
    
    // Get paginated data
    const pagedTrades = filteredTrades.slice(start, end);
    
    // Add rows to table
    pagedTrades.forEach((trade, index) => {
        const row = document.createElement('tr');
        
        // Calculate profit class
        const profitClass = (trade.profit_percent || 0) >= 0 ? 'profit' : 'loss';
        
        // Format trade data
        const formattedEntryTime = formatDateTime(trade.entry_time);
        const formattedExitTime = trade.exit_time ? formatDateTime(trade.exit_time) : '--';
        const formattedProfit = trade.profit_percent ? 
            `${trade.profit_percent > 0 ? '+' : ''}${trade.profit_percent.toFixed(2)}%` : '--';
        
        // Determine status badge class
        let statusBadgeClass = 'bg-secondary';
        if (trade.status === 'COMPLETED') {
            statusBadgeClass = (trade.profit_percent || 0) >= 0 ? 'bg-success' : 'bg-danger';
        } else if (trade.status === 'ACTIVE') {
            statusBadgeClass = 'bg-warning text-dark';
        } else if (trade.status === 'CANCELLED') {
            statusBadgeClass = 'bg-secondary';
        }
        
        // Create row HTML
        row.innerHTML = `
            <td>
                <button class="btn btn-sm btn-outline-secondary expand-row-btn" data-index="${index}">
                    <i class="bi bi-chevron-down"></i>
                </button>
            </td>
            <td>${trade.id || '--'}</td>
            <td>${formattedEntryTime}</td>
            <td>${trade.symbol || '--'}</td>
            <td>
                <span class="trade-badge ${trade.direction || 'UNKNOWN'}">
                    ${trade.direction || '--'}
                </span>
            </td>
            <td>${trade.entry_price || '--'}</td>
            <td>${trade.exit_price || '--'}</td>
            <td class="trade-profit ${profitClass}">${formattedProfit}</td>
            <td>
                <span class="badge ${statusBadgeClass}">
                    ${trade.status || 'UNKNOWN'}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-primary view-details-btn" data-trade-id="${trade.id}">
                    <i class="bi bi-info-circle"></i> Details
                </button>
            </td>
        `;
        
        tableBody.appendChild(row);
        
        // Create expandable details row
        const detailsRow = document.createElement('tr');
        detailsRow.className = 'trade-details-row';
        detailsRow.style.display = 'none';
        
        // Format strategy and exit type
        let strategyDisplay = trade.strategy || '--';
        let exitTypeDisplay = trade.exit_type || '--';
        
        if (exitTypeDisplay === 'TP') exitTypeDisplay = 'Take Profit';
        if (exitTypeDisplay === 'SL') exitTypeDisplay = 'Stop Loss';
        
        detailsRow.innerHTML = `
            <td colspan="10">
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Strategy:</strong> <span class="trade-strategy">${strategyDisplay}</span></p>
                        <p><strong>Size:</strong> ${trade.size || '--'}</p>
                        <p><strong>Entry Note:</strong> ${trade.entry_note || '--'}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>Exit Type:</strong> ${exitTypeDisplay}</p>
                        <p><strong>Exit Time:</strong> ${formattedExitTime}</p>
                        <p><strong>Exit Note:</strong> ${trade.exit_note || '--'}</p>
                    </div>
                </div>
            </td>
        `;
        
        tableBody.appendChild(detailsRow);
        
        // Add click handlers
        row.querySelector('.expand-row-btn').addEventListener('click', (e) => {
            const button = e.currentTarget;
            const icon = button.querySelector('i');
            const detailsRow = button.closest('tr').nextElementSibling;
            
            if (detailsRow.style.display === 'none') {
                detailsRow.style.display = 'table-row';
                icon.classList.replace('bi-chevron-down', 'bi-chevron-up');
            } else {
                detailsRow.style.display = 'none';
                icon.classList.replace('bi-chevron-up', 'bi-chevron-down');
            }
        });
        
        row.querySelector('.view-details-btn').addEventListener('click', () => {
            showTradeDetails(trade);
        });
    });
    
    // Update pagination
    updatePagination(total);
}
