/**
 * Trading Bot Dashboard - Parameters Page JS
 * 
 * Handles parameter management, profile switching, and adaptive regime configuration
 */

// Keep track of parameter changes
let parameterChanges = {};
let originalParameters = {};
let parameterConstraints = {};
let profileMappings = {};
let adaptiveEnabled = false;

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
    // Fetch initial data
    fetchParameters();
    fetchParameterHistory();
    
    // Set up event handlers
    document.getElementById('refresh-parameters-btn').addEventListener('click', fetchParameters);
    document.getElementById('save-parameters-btn').addEventListener('click', saveAllParameters);
    document.getElementById('save-regime-mappings').addEventListener('click', saveRegimeMappings);
    document.getElementById('save-parameter-btn').addEventListener('click', saveParameterEdit);
    document.getElementById('toggle-adaptive-parameters').addEventListener('change', toggleAdaptiveParameters);
    
    // Set up refresh intervals
    setInterval(fetchParameterHistory, DASHBOARD_CONFIG.refreshInterval * 2);
});

// Fetch parameters and profiles
async function fetchParameters() {
    try {
        const data = await apiRequest('parameters');
        
        // Store parameter data
        originalParameters = data.parameters || {};
        parameterConstraints = data.constraints || {};
        const profiles = data.profiles || {};
        const activeProfile = data.active_profile || 'default';
        
        // Reset parameter changes
        parameterChanges = {};
        
        // Update UI elements
        document.getElementById('active-profile-name').innerText = activeProfile;
        
        // Update parameter form
        updateParameterForm(originalParameters, parameterConstraints);
        
        // Update profiles UI
        updateProfilesUI(profiles, activeProfile);
        
        // Update regime mappings
        updateRegimeMappings(data.regime_mappings || {});
        
        // Set adaptive toggle state
        adaptiveEnabled = data.adaptive_enabled || false;
        document.getElementById('toggle-adaptive-parameters').checked = adaptiveEnabled;
        
        return data;
    } catch (error) {
        console.error('Error fetching parameters:', error);
    }
}

// Update parameter form
function updateParameterForm(parameters, constraints) {
    const container = document.getElementById('parameters-form');
    if (!container) return;
    
    // Clear container
    container.innerHTML = '';
    
    // Group parameters by category
    const categories = {
        'Signal Parameters': ['CONFIDENCE_THRESHOLD', 'MAX_SIGNALS_PER_DAY', 'MAX_TRADES_PER_DAY'],
        'Position Parameters': ['POSITION_SIZE_PERCENT', 'MAX_ACTIVE_POSITIONS', 'STOP_LOSS_PERCENT', 'TAKE_PROFIT_PERCENT'],
        'Strategy Parameters': ['SUPERTREND_ADX_WEIGHT', 'INSIDE_BAR_WEIGHT']
    };
    
    // Add each category
    Object.entries(categories).forEach(([categoryName, paramKeys]) => {
        const categoryParams = paramKeys.filter(key => parameters[key] !== undefined);
        if (categoryParams.length === 0) return;
        
        // Create category card
        const categoryCard = document.createElement('div');
        categoryCard.className = 'mb-4';
        categoryCard.innerHTML = `
            <h5 class="mb-3">${categoryName}</h5>
            <div class="card-category-container"></div>
        `;
        
        container.appendChild(categoryCard);
        const paramContainer = categoryCard.querySelector('.card-category-container');
        
        // Add each parameter in category
        categoryParams.forEach(paramName => {
            const value = parameters[paramName];
            const constraint = constraints[paramName] || {};
            
            // Create parameter control
            const paramControl = document.createElement('div');
            paramControl.className = 'parameter-control mb-4';
            
            // Format display value based on parameter name
            let displayValue = value;
            let inputType = 'text';
            let inputStep = '0.01';
            let inputMin = constraint.min !== undefined ? constraint.min : '';
            let inputMax = constraint.max !== undefined ? constraint.max : '';
            
            if (paramName === 'CONFIDENCE_THRESHOLD') {
                displayValue = `${(value * 100).toFixed(0)}%`;
                inputType = 'range';
                inputMin = '0';
                inputMax = '1';
                inputStep = '0.05';
            } else if (paramName.includes('PERCENT')) {
                displayValue = `${value}%`;
                inputType = 'number';
                inputStep = '0.5';
            } else if (['MAX_SIGNALS_PER_DAY', 'MAX_TRADES_PER_DAY', 'MAX_ACTIVE_POSITIONS'].includes(paramName)) {
                inputType = 'number';
                inputStep = '1';
            } else if (paramName.includes('WEIGHT')) {
                inputType = 'number';
                inputStep = '0.1';
            }
            
            // Create parameter HTML
            const paramHtml = `
                <label for="param-${paramName}" class="form-label">
                    ${paramName}
                    <span class="value-indicator">${displayValue}</span>
                </label>
                
                <div class="input-group mb-2">
                    <input 
                        type="${inputType}" 
                        class="form-control" 
                        id="param-${paramName}" 
                        name="${paramName}" 
                        value="${value}" 
                        min="${inputMin}" 
                        max="${inputMax}" 
                        step="${inputStep}"
                        ${constraint.readonly ? 'disabled' : ''}
                    >
                    <button class="btn btn-outline-primary edit-param-btn" data-param-name="${paramName}">
                        <i class="bi bi-pencil"></i>
                    </button>
                </div>
                
                <div class="form-text small">
                    ${constraint.description || `Configure ${paramName}`}
                </div>
            `;
            
            paramControl.innerHTML = paramHtml;
            paramContainer.appendChild(paramControl);
            
            // Add event listeners
            const input = paramControl.querySelector(`#param-${paramName}`);
            const valueIndicator = paramControl.querySelector('.value-indicator');
            const editBtn = paramControl.querySelector('.edit-param-btn');
            
            // Update on input change
            input.addEventListener('input', (e) => {
                let newValue = e.target.value;
                
                // Format display based on parameter
                if (paramName === 'CONFIDENCE_THRESHOLD') {
                    valueIndicator.innerText = `${(newValue * 100).toFixed(0)}%`;
                } else if (paramName.includes('PERCENT')) {
                    valueIndicator.innerText = `${newValue}%`;
                } else {
                    valueIndicator.innerText = newValue;
                }
                
                // Track changes
                if (newValue != originalParameters[paramName]) {
                    parameterChanges[paramName] = newValue;
                    input.classList.add('is-changed');
                } else {
                    delete parameterChanges[paramName];
                    input.classList.remove('is-changed');
                }
                
                // Update save button state
                updateSaveButtonState();
            });
            
            // Open edit modal on button click
            editBtn.addEventListener('click', () => {
                openEditModal(paramName, parameters[paramName], constraint.description);
            });
        });
    });
    
    updateSaveButtonState();
}

// Update save button state based on changes
function updateSaveButtonState() {
    const saveBtn = document.getElementById('save-parameters-btn');
    
    if (Object.keys(parameterChanges).length > 0) {
        saveBtn.classList.remove('btn-secondary');
        saveBtn.classList.add('btn-success');
        saveBtn.removeAttribute('disabled');
    } else {
        saveBtn.classList.remove('btn-success');
        saveBtn.classList.add('btn-secondary');
        saveBtn.setAttribute('disabled', 'disabled');
    }
}

// Open parameter edit modal
function openEditModal(paramName, currentValue, description) {
    const modal = document.getElementById('editParameterModal');
    const nameInput = document.getElementById('edit-param-name');
    const valueInput = document.getElementById('edit-param-value');
    const descriptionEl = document.getElementById('edit-param-description');
    
    nameInput.value = paramName;
    valueInput.value = parameterChanges[paramName] !== undefined ? 
        parameterChanges[paramName] : currentValue;
        
    if (description) {
        descriptionEl.innerText = description;
        descriptionEl.style.display = 'block';
    } else {
        descriptionEl.style.display = 'none';
    }
    
    // Show modal
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

// Save parameter from edit modal
function saveParameterEdit() {
    const paramName = document.getElementById('edit-param-name').value;
    const paramValue = document.getElementById('edit-param-value').value;
    const reason = document.getElementById('edit-param-reason').value;
    
    // Update parameter input
    const input = document.getElementById(`param-${paramName}`);
    if (input) {
        input.value = paramValue;
        
        // Trigger input event to update value indicator
        const event = new Event('input');
        input.dispatchEvent(event);
    }
    
    // Track change
    if (paramValue != originalParameters[paramName]) {
        parameterChanges[paramName] = paramValue;
    } else {
        delete parameterChanges[paramName];
    }
    
    // Close modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('editParameterModal'));
    modal.hide();
    
    // Update save button state
    updateSaveButtonState();
}

// Save all changed parameters
async function saveAllParameters() {
    if (Object.keys(parameterChanges).length === 0) return;
    
    try {
        // Create a batch update request
        const response = await apiRequest('parameters/batch', {
            method: 'PUT',
            body: JSON.stringify({
                parameters: parameterChanges,
                reason: 'Manual update via dashboard'
            })
        });
        
        if (response.success) {
            showToast('Parameters Updated', 'Parameter changes applied successfully', 'success');
            
            // Refresh parameters
            fetchParameters();
        }
    } catch (error) {
        console.error('Error updating parameters:', error);
    }
}

// Update profiles UI
function updateProfilesUI(profiles, activeProfile) {
    const container = document.getElementById('profiles-container');
    if (!container) return;
    
    // Clear container
    container.innerHTML = '';
    
    // Add profile cards
    Object.entries(profiles).forEach(([profileId, profile]) => {
        const isActive = profileId === activeProfile;
        
        // Determine card style based on profile
        let cardBgClass = 'bg-light';
        let buttonClass = 'btn-primary';
        
        switch (profileId) {
            case 'aggressive':
                cardBgClass = 'bg-success bg-opacity-10';
                buttonClass = 'btn-success';
                break;
            case 'conservative':
                cardBgClass = 'bg-warning bg-opacity-10';
                buttonClass = 'btn-warning';
                break;
            case 'defensive':
                cardBgClass = 'bg-danger bg-opacity-10';
                buttonClass = 'btn-danger';
                break;
        }
        
        // Create profile card HTML
        const profileHtml = `
            <div class="card mb-3 ${cardBgClass} ${isActive ? 'border border-primary' : ''}">
                <div class="card-body">
                    <h5 class="card-title d-flex align-items-center">
                        ${profileId.charAt(0).toUpperCase() + profileId.slice(1)}
                        ${isActive ? '<span class="badge bg-primary ms-2">Active</span>' : ''}
                    </h5>
                    <p class="card-text small">${profile.description || 'Profile for different market conditions'}</p>
                    
                    <div class="d-flex justify-content-between align-items-center">
                        <button class="btn ${buttonClass} btn-sm" onclick="applyProfile('${profileId}')">
                            ${isActive ? 'Applied' : 'Apply Profile'}
                        </button>
                        
                        <button class="btn btn-sm btn-outline-secondary" 
                               data-bs-toggle="collapse" 
                               data-bs-target="#profile-details-${profileId}">
                            View Details
                        </button>
                    </div>
                    
                    <div class="collapse mt-3" id="profile-details-${profileId}">
                        <div class="card card-body bg-light">
                            <h6 class="mb-2">Profile Parameters:</h6>
                            <ul class="list-group list-group-flush small">
                                ${Object.entries(profile.parameters || {})
                                    .map(([param, value]) => `
                                        <li class="list-group-item d-flex justify-content-between align-items-center">
                                            <span>${param}</span>
                                            <span class="badge bg-primary rounded-pill">${value}</span>
                                        </li>
                                    `).join('')}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', profileHtml);
    });
    
    // Also update profile options in regime mappings
    updateProfileOptions(profiles, activeProfile);
}

// Update regime mappings UI
function updateRegimeMappings(mappings) {
    profileMappings = mappings || {};
    
    // Set select values for each regime
    Object.entries(profileMappings).forEach(([regime, profileId]) => {
        const select = document.getElementById(`regime-${regime}`);
        if (select) {
            select.value = profileId;
        }
    });
}

// Update profile options in regime mapping selects
function updateProfileOptions(profiles, activeProfile) {
    // Get all regime selects
    const regimeSelects = document.querySelectorAll('[id^="regime-"]');
    
    // Update options for each select
    regimeSelects.forEach(select => {
        // Keep selected value
        const selectedValue = select.value;
        
        // Clear options
        select.innerHTML = '<option value="">No Profile (Disable)</option>';
        
        // Add profile options
        Object.keys(profiles).forEach(profileId => {
            const option = document.createElement('option');
            option.value = profileId;
            option.text = profileId.charAt(0).toUpperCase() + profileId.slice(1);
            
            // Mark as selected if it matches
            if (profileId === selectedValue) {
                option.selected = true;
            }
            
            select.appendChild(option);
        });
    });
}

// Toggle adaptive parameters
function toggleAdaptiveParameters(event) {
    adaptiveEnabled = event.target.checked;
    
    // Enable/disable regime mapping selects
    const regimeSelects = document.querySelectorAll('[id^="regime-"]');
    regimeSelects.forEach(select => {
        select.disabled = !adaptiveEnabled;
    });
    
    // Save setting
    saveAdaptiveToggle(adaptiveEnabled);
}

// Save adaptive toggle setting
async function saveAdaptiveToggle(enabled) {
    try {
        const response = await apiRequest('market/adaptive-toggle', {
            method: 'POST',
            body: JSON.stringify({
                enabled: enabled
            })
        });
        
        if (response.success) {
            showToast(
                enabled ? 'Adaptive Mode Enabled' : 'Adaptive Mode Disabled',
                enabled ? 'Bot will automatically switch profiles based on market regime' : 'Manual profile selection active',
                'info'
            );
        }
    } catch (error) {
        console.error('Error toggling adaptive mode:', error);
    }
}

// Save regime mappings
async function saveRegimeMappings() {
    // Get mappings from select elements
    const mappings = {};
    const regimeSelects = document.querySelectorAll('[id^="regime-"]');
    
    regimeSelects.forEach(select => {
        const regime = select.id.replace('regime-', '');
        const profileId = select.value;
        
        if (profileId) {
            mappings[regime] = profileId;
        }
    });
    
    try {
        const response = await apiRequest('market/regime-mappings', {
            method: 'POST',
            body: JSON.stringify({
                mappings: mappings
            })
        });
        
        if (response.success) {
            showToast('Regime Mappings Updated', 'Profile mappings for market regimes updated', 'success');
            profileMappings = mappings;
        }
    } catch (error) {
        console.error('Error saving regime mappings:', error);
    }
}

// Fetch parameter change history
async function fetchParameterHistory() {
    try {
        const data = await apiRequest('parameters/history');
        
        if (data.history && data.history.length > 0) {
            updateParameterHistoryTable(data.history);
        }
        
        return data;
    } catch (error) {
        console.error('Error fetching parameter history:', error);
    }
}

// Update parameter history table
function updateParameterHistoryTable(history) {
    const tableBody = document.getElementById('parameter-history-table');
    if (!tableBody) return;
    
    // Clear table
    tableBody.innerHTML = '';
    
    // Add history rows
    history.forEach(entry => {
        const row = `
            <tr>
                <td>${formatDateTime(entry.timestamp)}</td>
                <td>${entry.parameter}</td>
                <td>${entry.old_value !== undefined ? entry.old_value : '-'}</td>
                <td>${entry.new_value}</td>
                <td>
                    <span class="badge ${entry.source === 'market_analyzer' ? 'bg-warning text-dark' : 'bg-info'}">
                        ${entry.source}
                    </span>
                </td>
            </tr>
        `;
        
        tableBody.insertAdjacentHTML('beforeend', row);
    });
}

// Apply a profile
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
            
            // Update UI
            document.getElementById('active-profile-name').innerText = profileId;
            
            // Refresh parameters
            fetchParameters();
        }
    } catch (error) {
        console.error('Error applying profile:', error);
    }
}
