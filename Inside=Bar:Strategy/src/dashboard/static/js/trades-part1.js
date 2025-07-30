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
