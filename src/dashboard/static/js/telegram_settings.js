/**
 * Telegram Alert Settings Module
 * -----------------------------
 * Provides UI and functionality for customizing Telegram alert preferences:
 * - Per-alert type toggles (regime change, top performers, playbook matches, confidence thresholds)
 * - Custom threshold controls for different metrics
 * - Mute timeframe settings
 * - Settings persistence via localStorage
 */

// Default settings configuration
const DEFAULT_SETTINGS = {
  enableAlerts: true,
  alertTypes: {
    regimeChange: true,
    topPerformer: true,
    playbookMatch: true,
    confidenceThreshold: true,
    tradeExecution: true
  },
  thresholds: {
    confidenceThreshold: 0.80, // 80%
    roiThreshold: 1.5, // 1.5%
    winRateThreshold: 60, // 60%
    playbookMatchConfidence: 75 // 75%
  },
  muteSettings: {
    enabled: false,
    startTime: "00:00", // 24hr format
    endTime: "08:00", // 24hr format
    mutedDays: [] // Empty array = no muted days
  }
};

/**
 * Initialize Telegram settings module
 */
function initTelegramSettings() {
  // Load settings from localStorage or use defaults
  loadSettings();
  
  // Set initial UI state based on settings
  updateSettingsUI();
  
  // Attach event listeners to settings controls
  attachSettingsEventListeners();
}

/**
 * Load settings from localStorage or use defaults
 */
function loadSettings() {
  try {
    const savedSettings = localStorage.getItem('telegram_alert_settings');
    
    if (savedSettings) {
      const parsedSettings = JSON.parse(savedSettings);
      // Merge with defaults to ensure all properties exist
      DASHBOARD_CONFIG.telegram = {
        ...DEFAULT_SETTINGS,
        ...parsedSettings
      };
    } else {
      // Use defaults
      DASHBOARD_CONFIG.telegram = {...DEFAULT_SETTINGS};
    }
    
    console.log('Loaded Telegram settings:', DASHBOARD_CONFIG.telegram);
  } catch (error) {
    console.error('Error loading Telegram settings:', error);
    DASHBOARD_CONFIG.telegram = {...DEFAULT_SETTINGS};
  }
}

/**
 * Save current settings to localStorage
 */
function saveSettings() {
  try {
    localStorage.setItem('telegram_alert_settings', JSON.stringify(DASHBOARD_CONFIG.telegram));
    console.log('Saved Telegram settings:', DASHBOARD_CONFIG.telegram);
  } catch (error) {
    console.error('Error saving Telegram settings:', error);
  }
}

/**
 * Update settings UI to reflect current settings
 */
function updateSettingsUI() {
  const settings = DASHBOARD_CONFIG.telegram;
  
  // Main toggle
  document.getElementById('telegram-alerts-toggle').checked = settings.enableAlerts;
  
  // Alert type toggles
  document.getElementById('regime-change-alerts').checked = settings.alertTypes.regimeChange;
  document.getElementById('top-performer-alerts').checked = settings.alertTypes.topPerformer;
  document.getElementById('playbook-match-alerts').checked = settings.alertTypes.playbookMatch;
  document.getElementById('confidence-threshold-alerts').checked = settings.alertTypes.confidenceThreshold;
  document.getElementById('trade-execution-alerts').checked = settings.alertTypes.tradeExecution;
  
  // Threshold sliders
  document.getElementById('confidence-threshold-slider').value = settings.thresholds.confidenceThreshold * 100;
  document.getElementById('confidence-threshold-value').textContent = `${Math.round(settings.thresholds.confidenceThreshold * 100)}%`;
  
  document.getElementById('roi-threshold-slider').value = settings.thresholds.roiThreshold;
  document.getElementById('roi-threshold-value').textContent = `${settings.thresholds.roiThreshold}%`;
  
  document.getElementById('win-rate-threshold-slider').value = settings.thresholds.winRateThreshold;
  document.getElementById('win-rate-threshold-value').textContent = `${settings.thresholds.winRateThreshold}%`;
  
  document.getElementById('playbook-match-confidence-slider').value = settings.thresholds.playbookMatchConfidence;
  document.getElementById('playbook-match-confidence-value').textContent = `${settings.thresholds.playbookMatchConfidence}%`;
  
  // Mute settings
  document.getElementById('mute-alerts-toggle').checked = settings.muteSettings.enabled;
  document.getElementById('mute-start-time').value = settings.muteSettings.startTime;
  document.getElementById('mute-end-time').value = settings.muteSettings.endTime;
  
  // Update muted days checkboxes
  const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
  days.forEach(day => {
    document.getElementById(`mute-${day}`).checked = settings.muteSettings.mutedDays.includes(day);
  });
  
  // Toggle visibility of sections based on main toggle
  toggleSettingsSectionsVisibility(settings.enableAlerts);
}

/**
 * Toggle visibility of settings sections based on main toggle
 * @param {Boolean} isEnabled - Whether alerts are enabled
 */
function toggleSettingsSectionsVisibility(isEnabled) {
  const sections = document.querySelectorAll('.telegram-settings-section');
  sections.forEach(section => {
    section.style.opacity = isEnabled ? '1' : '0.5';
    section.style.pointerEvents = isEnabled ? 'auto' : 'none';
  });
}

/**
 * Attach event listeners to all settings controls
 */
function attachSettingsEventListeners() {
  // Main toggle
  document.getElementById('telegram-alerts-toggle').addEventListener('change', e => {
    DASHBOARD_CONFIG.telegram.enableAlerts = e.target.checked;
    toggleSettingsSectionsVisibility(e.target.checked);
    saveSettings();
  });
  
  // Alert type toggles
  document.getElementById('regime-change-alerts').addEventListener('change', e => {
    DASHBOARD_CONFIG.telegram.alertTypes.regimeChange = e.target.checked;
    saveSettings();
  });
  
  document.getElementById('top-performer-alerts').addEventListener('change', e => {
    DASHBOARD_CONFIG.telegram.alertTypes.topPerformer = e.target.checked;
    saveSettings();
  });
  
  document.getElementById('playbook-match-alerts').addEventListener('change', e => {
    DASHBOARD_CONFIG.telegram.alertTypes.playbookMatch = e.target.checked;
    saveSettings();
  });
  
  document.getElementById('confidence-threshold-alerts').addEventListener('change', e => {
    DASHBOARD_CONFIG.telegram.alertTypes.confidenceThreshold = e.target.checked;
    saveSettings();
  });
  
  document.getElementById('trade-execution-alerts').addEventListener('change', e => {
    DASHBOARD_CONFIG.telegram.alertTypes.tradeExecution = e.target.checked;
    saveSettings();
  });
  
  // Threshold sliders
  document.getElementById('confidence-threshold-slider').addEventListener('input', e => {
    const value = parseInt(e.target.value);
    document.getElementById('confidence-threshold-value').textContent = `${value}%`;
    DASHBOARD_CONFIG.telegram.thresholds.confidenceThreshold = value / 100;
    saveSettings();
  });
  
  document.getElementById('roi-threshold-slider').addEventListener('input', e => {
    const value = parseFloat(e.target.value);
    document.getElementById('roi-threshold-value').textContent = `${value}%`;
    DASHBOARD_CONFIG.telegram.thresholds.roiThreshold = value;
    saveSettings();
  });
  
  document.getElementById('win-rate-threshold-slider').addEventListener('input', e => {
    const value = parseInt(e.target.value);
    document.getElementById('win-rate-threshold-value').textContent = `${value}%`;
    DASHBOARD_CONFIG.telegram.thresholds.winRateThreshold = value;
    saveSettings();
  });
  
  document.getElementById('playbook-match-confidence-slider').addEventListener('input', e => {
    const value = parseInt(e.target.value);
    document.getElementById('playbook-match-confidence-value').textContent = `${value}%`;
    DASHBOARD_CONFIG.telegram.thresholds.playbookMatchConfidence = value;
    saveSettings();
  });
  
  // Mute settings
  document.getElementById('mute-alerts-toggle').addEventListener('change', e => {
    DASHBOARD_CONFIG.telegram.muteSettings.enabled = e.target.checked;
    saveSettings();
  });
  
  document.getElementById('mute-start-time').addEventListener('change', e => {
    DASHBOARD_CONFIG.telegram.muteSettings.startTime = e.target.value;
    saveSettings();
  });
  
  document.getElementById('mute-end-time').addEventListener('change', e => {
    DASHBOARD_CONFIG.telegram.muteSettings.endTime = e.target.value;
    saveSettings();
  });
  
  // Muted days checkboxes
  const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
  days.forEach(day => {
    document.getElementById(`mute-${day}`).addEventListener('change', e => {
      if (e.target.checked) {
        DASHBOARD_CONFIG.telegram.muteSettings.mutedDays.push(day);
      } else {
        DASHBOARD_CONFIG.telegram.muteSettings.mutedDays = 
          DASHBOARD_CONFIG.telegram.muteSettings.mutedDays.filter(d => d !== day);
      }
      saveSettings();
    });
  });
  
  // Reset to defaults button
  document.getElementById('reset-telegram-settings').addEventListener('click', () => {
    if (confirm('Are you sure you want to reset all Telegram alert settings to defaults?')) {
      DASHBOARD_CONFIG.telegram = {...DEFAULT_SETTINGS};
      updateSettingsUI();
      saveSettings();
      showToast('Telegram settings reset to defaults', 'info');
    }
  });
}

/**
 * Check if alerts should be muted based on current time and mute settings
 * @returns {Boolean} - Whether alerts should be muted
 */
function shouldMuteAlerts() {
  const settings = DASHBOARD_CONFIG.telegram;
  
  // If muting is not enabled, don't mute
  if (!settings.muteSettings.enabled) {
    return false;
  }
  
  const now = new Date();
  const currentDay = now.toLocaleString('en-us', { weekday: 'lowercase' });
  
  // Check if current day is muted
  if (settings.muteSettings.mutedDays.includes(currentDay)) {
    return true;
  }
  
  // Check if current time is within muted hours
  const currentHour = now.getHours();
  const currentMinute = now.getMinutes();
  const currentTime = currentHour * 60 + currentMinute; // Convert to minutes since midnight
  
  const [startHour, startMinute] = settings.muteSettings.startTime.split(':').map(Number);
  const [endHour, endMinute] = settings.muteSettings.endTime.split(':').map(Number);
  
  const startTime = startHour * 60 + startMinute; // Convert to minutes since midnight
  const endTime = endHour * 60 + endMinute; // Convert to minutes since midnight
  
  // Handle cases where mute period crosses midnight
  if (startTime > endTime) {
    return currentTime >= startTime || currentTime <= endTime;
  } else {
    return currentTime >= startTime && currentTime <= endTime;
  }
}

/**
 * Check if alert should be sent based on type and thresholds
 * @param {Object} alertData - Alert data object
 * @returns {Boolean} - Whether alert should be sent
 */
function shouldSendAlert(alertData) {
  const settings = DASHBOARD_CONFIG.telegram;
  
  // Master switch
  if (!settings.enableAlerts) {
    return false;
  }
  
  // Check if muted
  if (shouldMuteAlerts()) {
    return false;
  }
  
  // Check alert type
  switch (alertData.type) {
    case 'regime_change':
      if (!settings.alertTypes.regimeChange) return false;
      // Check confidence threshold
      return alertData.data.confidence >= settings.thresholds.confidenceThreshold;
      
    case 'high_performer':
      if (!settings.alertTypes.topPerformer) return false;
      // Check ROI threshold
      const roi = alertData.data.performance?.roi_pct || 0;
      return roi >= settings.thresholds.roiThreshold;
      
    case 'playbook_match':
      if (!settings.alertTypes.playbookMatch) return false;
      // Check match confidence
      const matchConfidence = (alertData.data.match_confidence || 0) * 100;
      return matchConfidence >= settings.thresholds.playbookMatchConfidence;
      
    case 'confidence_threshold':
      if (!settings.alertTypes.confidenceThreshold) return false;
      return true;
      
    case 'trade_execution':
      return settings.alertTypes.tradeExecution;
      
    default:
      return true;
  }
}
