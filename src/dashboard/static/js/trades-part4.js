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
