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
