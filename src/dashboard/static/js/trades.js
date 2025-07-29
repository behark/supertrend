/**
 * Trading Bot Dashboard - Trades Page JS
 * 
 * Handles trade history visualization, filtering, and detailed view
 */

// Store trade data
let allTrades = [];
let filteredTrades = [];
let currentPage = 1;
let pageSize = 10;
let totalPages = 1;

// Chart references
let performanceChart = null;

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
    // Add event listeners
    document.getElementById('refresh-trades-btn').addEventListener('click', fetchTradeHistory);
    document.getElementById('apply-filters-btn').addEventListener('click', applyFilters);
    document.getElementById('clear-filters-btn').addEventListener('click', clearFilters);
    document.getElementById('date-range-filter').addEventListener('change', toggleCustomDateFields);
    document.getElementById('page-size').addEventListener('change', changePageSize);
    document.getElementById('export-btn').addEventListener('click', exportTradeHistory);
    
    // Initialize page
    fetchTradeHistory();
    
    // Set refresh interval
    setInterval(fetchTradeHistory, DASHBOARD_CONFIG.refreshInterval * 2);
});

// Fetch trade history
async function fetchTradeHistory() {
    try {
        const response = await apiRequest('trades/history');
        
        if (response.trades) {
            // Store all trades
            allTrades = response.trades;
            
            // Initialize with all trades
            filteredTrades = [...allTrades];
            
            // Update UI
            updateTradeSummary(response.summary || {});
            updatePerformanceChart(allTrades);
            populateSymbolFilter();
            
            // Apply any active filters
            applyFilters();
        }
        
        return response;
    } catch (error) {
        console.error('Error fetching trade history:', error);
        showToast('Error', 'Failed to fetch trade history', 'error');
    }
}

// Update trade summary statistics
function updateTradeSummary(summary) {
    document.getElementById('total-trades-count').innerText = summary.total_trades || 0;
    
    const winRate = summary.win_rate !== undefined ? 
        `${(summary.win_rate * 100).toFixed(1)}%` : '--';
    document.getElementById('win-rate').innerText = winRate;
    
    const totalProfit = summary.total_profit !== undefined ?
        `${summary.total_profit > 0 ? '+' : ''}${summary.total_profit.toFixed(2)}%` : '--';
    document.getElementById('total-profit').innerText = totalProfit;
    
    if (summary.total_profit > 0) {
        document.getElementById('total-profit').className = 'text-success';
    } else if (summary.total_profit < 0) {
        document.getElementById('total-profit').className = 'text-danger';
    }
    
    const avgProfit = summary.avg_profit !== undefined ?
        `${summary.avg_profit > 0 ? '+' : ''}${summary.avg_profit.toFixed(2)}%` : '--';
    document.getElementById('avg-profit').innerText = avgProfit;
    
    if (summary.avg_profit > 0) {
        document.getElementById('avg-profit').className = 'text-success';
    } else if (summary.avg_profit < 0) {
        document.getElementById('avg-profit').className = 'text-danger';
    }
}

// Update performance chart
function updatePerformanceChart(trades) {
    const canvas = document.getElementById('trade-performance-chart');
    if (!canvas) return;
    
    // Prepare data
    const sortedTrades = [...trades].sort((a, b) => {
        return new Date(a.entry_time) - new Date(b.entry_time);
    });
    
    const labels = sortedTrades.map(trade => new Date(trade.entry_time));
    
    // Calculate cumulative profit
    let cumulativeProfit = 0;
    const profitData = sortedTrades.map(trade => {
        const profit = trade.profit_percent || 0;
        cumulativeProfit += profit;
        return cumulativeProfit;
    });
    
    // Extract individual trade profits for bar chart
    const tradeData = sortedTrades.map(trade => trade.profit_percent || 0);
    
    // Create or update chart
    if (performanceChart) {
        performanceChart.data.labels = labels;
        performanceChart.data.datasets[0].data = profitData;
        performanceChart.data.datasets[1].data = tradeData;
        performanceChart.update();
    } else {
        performanceChart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        type: 'line',
                        label: 'Cumulative Performance (%)',
                        data: profitData,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        borderWidth: 2,
                        tension: 0.1,
                        fill: true,
                        yAxisID: 'y'
                    },
                    {
                        type: 'bar',
                        label: 'Trade P/L (%)',
                        data: tradeData,
                        backgroundColor: tradeData.map(value => 
                            value >= 0 ? 'rgba(40, 167, 69, 0.6)' : 'rgba(220, 53, 69, 0.6)'
                        ),
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
                            unit: 'day',
                            displayFormats: {
                                day: 'MMM d'
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
                            text: 'Cumulative P/L (%)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false
                        },
                        title: {
                            display: true,
                            text: 'Trade P/L (%)'
                        }
                    }
                }
            }
        });
    }
}

// Populate symbol filter dropdown
function populateSymbolFilter() {
    const symbolFilter = document.getElementById('symbol-filter');
    if (!symbolFilter) return;
    
    // Get unique symbols
    const symbols = [...new Set(allTrades.map(trade => trade.symbol))];
    
    // Clear options except first
    while (symbolFilter.options.length > 1) {
        symbolFilter.remove(1);
    }
    
    // Add symbol options
    symbols.forEach(symbol => {
        const option = document.createElement('option');
        option.value = symbol;
        option.textContent = symbol;
        symbolFilter.appendChild(option);
    });
}

// Toggle custom date fields based on date range selection
function toggleCustomDateFields() {
    const dateRangeValue = document.getElementById('date-range-filter').value;
    const customDateFields = document.getElementById('custom-date-range');
    
    if (dateRangeValue === 'custom') {
        customDateFields.style.display = 'flex';
    } else {
        customDateFields.style.display = 'none';
    }
}
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
// Update pagination controls
function updatePagination(totalItems) {
    const paginationContainer = document.getElementById('trades-pagination');
    const pageInfo = document.getElementById('page-info');
    
    if (!paginationContainer || !pageInfo) return;
    
    // Clear current pagination
    paginationContainer.innerHTML = '';
    
    // Calculate total pages
    totalPages = Math.ceil(totalItems / pageSize);
    
    // Update page info
    if (totalItems === 0) {
        pageInfo.textContent = 'No trades found';
    } else {
        const start = (currentPage - 1) * pageSize + 1;
        const end = Math.min(currentPage * pageSize, totalItems);
        pageInfo.textContent = `Showing ${start} to ${end} of ${totalItems} trades`;
    }
    
    // Create pagination controls if needed
    if (totalPages > 1) {
        // Previous button
        const prevBtn = document.createElement('li');
        prevBtn.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
        prevBtn.innerHTML = '<a class="page-link" href="#" aria-label="Previous"><span aria-hidden="true">&laquo;</span></a>';
        paginationContainer.appendChild(prevBtn);
        
        if (currentPage > 1) {
            prevBtn.addEventListener('click', () => {
                currentPage--;
                updateTradeTable();
            });
        }
        
        // Page numbers
        const maxPageButtons = 5;
        let startPage = Math.max(1, currentPage - Math.floor(maxPageButtons / 2));
        const endPage = Math.min(totalPages, startPage + maxPageButtons - 1);
        
        // Adjust start page if needed
        if (endPage - startPage < maxPageButtons - 1) {
            startPage = Math.max(1, endPage - maxPageButtons + 1);
        }
        
        // Add first page if not included in range
        if (startPage > 1) {
            const firstPageBtn = document.createElement('li');
            firstPageBtn.className = 'page-item';
            firstPageBtn.innerHTML = '<a class="page-link" href="#">1</a>';
            paginationContainer.appendChild(firstPageBtn);
            
            firstPageBtn.addEventListener('click', () => {
                currentPage = 1;
                updateTradeTable();
            });
            
            // Add ellipsis if needed
            if (startPage > 2) {
                const ellipsisBtn = document.createElement('li');
                ellipsisBtn.className = 'page-item disabled';
                ellipsisBtn.innerHTML = '<a class="page-link" href="#">...</a>';
                paginationContainer.appendChild(ellipsisBtn);
            }
        }
        
        // Add page numbers
        for (let i = startPage; i <= endPage; i++) {
            const pageBtn = document.createElement('li');
            pageBtn.className = `page-item ${i === currentPage ? 'active' : ''}`;
            pageBtn.innerHTML = `<a class="page-link" href="#">${i}</a>`;
            paginationContainer.appendChild(pageBtn);
            
            if (i !== currentPage) {
                pageBtn.addEventListener('click', () => {
                    currentPage = i;
                    updateTradeTable();
                });
            }
        }
        
        // Add last page if not included in range
        if (endPage < totalPages) {
            // Add ellipsis if needed
            if (endPage < totalPages - 1) {
                const ellipsisBtn = document.createElement('li');
                ellipsisBtn.className = 'page-item disabled';
                ellipsisBtn.innerHTML = '<a class="page-link" href="#">...</a>';
                paginationContainer.appendChild(ellipsisBtn);
            }
            
            const lastPageBtn = document.createElement('li');
            lastPageBtn.className = 'page-item';
            lastPageBtn.innerHTML = `<a class="page-link" href="#">${totalPages}</a>`;
            paginationContainer.appendChild(lastPageBtn);
            
            lastPageBtn.addEventListener('click', () => {
                currentPage = totalPages;
                updateTradeTable();
            });
        }
        
        // Next button
        const nextBtn = document.createElement('li');
        nextBtn.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
        nextBtn.innerHTML = '<a class="page-link" href="#" aria-label="Next"><span aria-hidden="true">&raquo;</span></a>';
        paginationContainer.appendChild(nextBtn);
        
        if (currentPage < totalPages) {
            nextBtn.addEventListener('click', () => {
                currentPage++;
                updateTradeTable();
            });
        }
    }
}

// Change page size
function changePageSize() {
    const newPageSize = parseInt(document.getElementById('page-size').value);
    
    if (newPageSize && newPageSize !== pageSize) {
        pageSize = newPageSize;
        
        // Reset to first page and update table
        currentPage = 1;
        updateTradeTable();
    }
}

// Format date and time for display
function formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return '--';
    
    const date = new Date(dateTimeStr);
    
    return date.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Format date only for display
function formatDate(dateTimeStr) {
    if (!dateTimeStr) return '--';
    
    const date = new Date(dateTimeStr);
    
    return date.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Format time only for display
function formatTime(dateTimeStr) {
    if (!dateTimeStr) return '--';
    
    const date = new Date(dateTimeStr);
    
    return date.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// Show trade details in modal
function showTradeDetails(trade) {
    const modal = document.getElementById('trade-detail-modal');
    if (!modal) return;
    
    // Update modal title with trade ID
    const modalTitle = modal.querySelector('.modal-title');
    if (modalTitle) {
        modalTitle.textContent = `Trade Details - ${trade.id || 'Unknown ID'}`;
    }
    
    // Format trade data
    const formattedEntryTime = formatDateTime(trade.entry_time);
    const formattedExitTime = trade.exit_time ? formatDateTime(trade.exit_time) : '--';
    const formattedProfit = trade.profit_percent ? 
        `${trade.profit_percent > 0 ? '+' : ''}${trade.profit_percent.toFixed(2)}%` : '--';
    
    // Trade direction badge class
    const directionClass = trade.direction === 'LONG' ? 'bg-success' : 'bg-danger';
    
    // Trade status badge class
    let statusBadgeClass = 'bg-secondary';
    if (trade.status === 'COMPLETED') {
        statusBadgeClass = (trade.profit_percent || 0) >= 0 ? 'bg-success' : 'bg-danger';
    } else if (trade.status === 'ACTIVE') {
        statusBadgeClass = 'bg-warning text-dark';
    } else if (trade.status === 'CANCELLED') {
        statusBadgeClass = 'bg-secondary';
    }
    
    // Trade outcome
    const isWin = (trade.profit_percent || 0) > 0;
    const outcomeClass = isWin ? 'text-success' : 'text-danger';
    const outcomeText = isWin ? 'WIN' : 'LOSS';
    
    // Format strategy and exit type
    let strategyDisplay = trade.strategy || '--';
    let exitTypeDisplay = trade.exit_type || '--';
    
    if (exitTypeDisplay === 'TP') exitTypeDisplay = 'Take Profit';
    if (exitTypeDisplay === 'SL') exitTypeDisplay = 'Stop Loss';
    
    // Update modal body
    const modalBody = modal.querySelector('.modal-body');
    if (modalBody) {
        modalBody.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h5>Trade Overview</h5>
                    <table class="table table-sm">
                        <tr>
                            <td>Symbol:</td>
                            <td><strong>${trade.symbol || '--'}</strong></td>
                        </tr>
                        <tr>
                            <td>Direction:</td>
                            <td><span class="badge ${directionClass}">${trade.direction || '--'}</span></td>
                        </tr>
                        <tr>
                            <td>Status:</td>
                            <td><span class="badge ${statusBadgeClass}">${trade.status || '--'}</span></td>
                        </tr>
                        <tr>
                            <td>Strategy:</td>
                            <td>${strategyDisplay}</td>
                        </tr>
                        <tr>
                            <td>Size:</td>
                            <td>${trade.size || '--'}</td>
                        </tr>
                        <tr>
                            <td>Leverage:</td>
                            <td>${trade.leverage || '--'}x</td>
                        </tr>
                        <tr>
                            <td>Outcome:</td>
                            <td class="${outcomeClass}"><strong>${outcomeText}</strong></td>
                        </tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h5>Performance</h5>
                    <table class="table table-sm">
                        <tr>
                            <td>Entry Price:</td>
                            <td><strong>${trade.entry_price || '--'}</strong></td>
                        </tr>
                        <tr>
                            <td>Exit Price:</td>
                            <td><strong>${trade.exit_price || '--'}</strong></td>
                        </tr>
                        <tr>
                            <td>Profit/Loss:</td>
                            <td class="${isWin ? 'text-success' : 'text-danger'}">
                                <strong>${formattedProfit}</strong>
                            </td>
                        </tr>
                        <tr>
                            <td>Exit Type:</td>
                            <td>${exitTypeDisplay}</td>
                        </tr>
                        <tr>
                            <td>Entry Time:</td>
                            <td>${formattedEntryTime}</td>
                        </tr>
                        <tr>
                            <td>Exit Time:</td>
                            <td>${formattedExitTime}</td>
                        </tr>
                        <tr>
                            <td>Duration:</td>
                            <td>${calculateTradeDuration(trade.entry_time, trade.exit_time)}</td>
                        </tr>
                    </table>
                </div>
            </div>
            
            <hr />
            
            <div class="row">
                <div class="col-12">
                    <h5>Notes</h5>
                    <div class="mb-3">
                        <label class="form-label">Entry Note:</label>
                        <div class="note-box">${trade.entry_note || 'No entry note provided.'}</div>
                    </div>
                    <div>
                        <label class="form-label">Exit Note:</label>
                        <div class="note-box">${trade.exit_note || 'No exit note provided.'}</div>
                    </div>
                </div>
            </div>
            
            <hr />
            
            <div class="row">
                <div class="col-12">
                    <h5>Order History</h5>
                    ${generateOrderHistory(trade.orders)}
                </div>
            </div>
        `;
    }
    
    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

// Calculate trade duration
function calculateTradeDuration(entryTime, exitTime) {
    if (!entryTime || !exitTime) return '--';
    
    const entry = new Date(entryTime);
    const exit = new Date(exitTime);
    
    // Calculate duration in milliseconds
    const duration = exit - entry;
    
    // Convert to human-readable format
    const seconds = Math.floor(duration / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) {
        return `${days}d ${hours % 24}h`;
    } else if (hours > 0) {
        return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
        return `${minutes}m ${seconds % 60}s`;
    } else {
        return `${seconds}s`;
    }
}

// Generate order history table
function generateOrderHistory(orders) {
    if (!orders || orders.length === 0) {
        return '<p>No order history available.</p>';
    }
    
    let html = `
        <table class="table table-sm table-striped">
            <thead>
                <tr>
                    <th>Order ID</th>
                    <th>Type</th>
                    <th>Side</th>
                    <th>Status</th>
                    <th>Price</th>
                    <th>Size</th>
                    <th>Time</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    orders.forEach(order => {
        // Order status badge class
        let statusClass = 'bg-secondary';
        
        if (order.status === 'FILLED') {
            statusClass = 'bg-success';
        } else if (order.status === 'CANCELED') {
            statusClass = 'bg-warning text-dark';
        } else if (order.status === 'REJECTED') {
            statusClass = 'bg-danger';
        }
        
        html += `
            <tr>
                <td>${order.order_id || '--'}</td>
                <td>${order.type || '--'}</td>
                <td>${order.side || '--'}</td>
                <td><span class="badge ${statusClass}">${order.status || '--'}</span></td>
                <td>${order.price || '--'}</td>
                <td>${order.size || '--'}</td>
                <td>${formatDateTime(order.time) || '--'}</td>
            </tr>
        `;
    });
    
    html += `
            </tbody>
        </table>
    `;
    
    return html;
}
// Export trade history
async function exportTradeHistory() {
    // Get export modal elements
    const modal = document.getElementById('export-modal');
    const formatSelect = document.getElementById('export-format');
    const filterCheckbox = document.getElementById('export-filtered');
    const detailsCheckbox = document.getElementById('export-details');
    const exportBtn = document.getElementById('confirm-export-btn');
    
    if (!modal || !formatSelect || !filterCheckbox || !detailsCheckbox || !exportBtn) return;
    
    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    
    // Set up export button handler
    exportBtn.onclick = async () => {
        // Get export options
        const format = formatSelect.value;
        const useFiltered = filterCheckbox.checked;
        const includeDetails = detailsCheckbox.checked;
        
        // Get trades to export
        const trades = useFiltered ? filteredTrades : allTrades;
        
        // Check if there are trades to export
        if (trades.length === 0) {
            showToast('Export Error', 'No trades available to export', 'error');
            return;
        }
        
        // Clone trades to avoid modifying the original data
        const exportData = JSON.parse(JSON.stringify(trades));
        
        // Remove order details if not requested
        if (!includeDetails) {
            exportData.forEach(trade => {
                if (trade.orders) {
                    delete trade.orders;
                }
            });
        }
        
        // Export based on format
        if (format === 'json') {
            exportAsJson(exportData);
        } else {
            exportAsCsv(exportData);
        }
        
        // Hide modal
        bsModal.hide();
        
        // Show success toast
        showToast('Export Complete', `${trades.length} trades exported as ${format.toUpperCase()}`, 'success');
    };
}

// Export data as JSON file
function exportAsJson(data) {
    const jsonString = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const today = new Date().toISOString().split('T')[0];
    
    downloadFile(blob, `trade_history_${today}.json`);
}

// Export data as CSV file
function exportAsCsv(data) {
    if (data.length === 0) return;
    
    // Define CSV headers
    const headers = [
        'ID', 
        'Symbol', 
        'Direction', 
        'Status',
        'Entry Time', 
        'Entry Price', 
        'Exit Time', 
        'Exit Price', 
        'Profit (%)', 
        'Exit Type',
        'Strategy', 
        'Size',
        'Entry Note',
        'Exit Note'
    ];
    
    // Check for order details
    const hasOrders = data.some(trade => trade.orders && trade.orders.length > 0);
    
    if (hasOrders) {
        headers.push('Order Count');
    }
    
    // Create CSV content
    let csvContent = headers.join(',') + '\n';
    
    data.forEach(trade => {
        // Format data with quotes to handle commas in text
        const row = [
            `"${trade.id || ''}"`,
            `"${trade.symbol || ''}"`,
            `"${trade.direction || ''}"`,
            `"${trade.status || ''}"`,
            `"${trade.entry_time || ''}"`,
            `"${trade.entry_price || ''}"`,
            `"${trade.exit_time || ''}"`,
            `"${trade.exit_price || ''}"`,
            `"${trade.profit_percent ? trade.profit_percent.toFixed(2) : ''}"`,
            `"${trade.exit_type || ''}"`,
            `"${trade.strategy || ''}"`,
            `"${trade.size || ''}"`,
            `"${(trade.entry_note || '').replace(/"/g, '""')}"`,
            `"${(trade.exit_note || '').replace(/"/g, '""')}"`
        ];
        
        // Add order count if applicable
        if (hasOrders) {
            const orderCount = (trade.orders && trade.orders.length) || 0;
            row.push(`"${orderCount}"`);
        }
        
        csvContent += row.join(',') + '\n';
    });
    
    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const today = new Date().toISOString().split('T')[0];
    
    downloadFile(blob, `trade_history_${today}.csv`);
}

// Helper function to download a file
function downloadFile(blob, filename) {
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    
    document.body.appendChild(link);
    link.click();
    
    setTimeout(() => {
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }, 100);
}
