#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Parameter Manager Module

Provides advanced parameter management capabilities:
- Dynamic parameter control with validation
- Parameter profiles for different market conditions
- Audit trail of parameter changes
- Scheduled parameter adjustments
- Parameter change notifications
"""

import os
import json
import logging
import threading
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
import time
import schedule
import copy
from pathlib import Path

# Configure module logger
logger = logging.getLogger(__name__)

# Try to import notification tools
try:
    from src.integrations.telegram import telegram_notifier
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

class ParameterManager:
    """
    Advanced parameter manager with profiles, audit trail, and scheduling
    """
    
    # Singleton implementation
    _instance = None
    _lock = threading.Lock()
    
    # Directory and file paths
    CONFIG_DIR = "config"
    PARAMETERS_FILE = "parameters.json"
    PROFILES_FILE = "parameter_profiles.json"
    AUDIT_FILE = "parameter_audit.jsonl"
    
    # Parameter constraints (min, max, default)
    PARAMETER_CONSTRAINTS = {
        "confidence_threshold": {
            "type": "float",
            "min": 50.0,
            "max": 100.0,
            "default": 95.0,
            "description": "Signal confidence threshold percentage"
        },
        "max_signals_per_day": {
            "type": "int",
            "min": 1,
            "max": 50,
            "default": 10,
            "description": "Maximum number of signals per day"
        },
        "max_trades_per_day": {
            "type": "int",
            "min": 1,
            "max": 20,
            "default": 5,
            "description": "Maximum number of trades per day"
        },
        "position_size_percent": {
            "type": "float",
            "min": 1.0,
            "max": 100.0,
            "default": 25.0,
            "description": "Position size as percentage of available balance"
        },
        "supertrend_adx_weight": {
            "type": "int",
            "min": 0,
            "max": 100,
            "default": 60,
            "description": "Weight of SupertrendADX strategy in combined signals"
        },
        "inside_bar_weight": {
            "type": "int",
            "min": 0,
            "max": 100,
            "default": 40,
            "description": "Weight of InsideBar strategy in combined signals"
        }
    }
    
    # Default parameter profiles
    DEFAULT_PROFILES = {
        "default": {
            "name": "Default",
            "description": "Standard balanced settings",
            "parameters": {
                "confidence_threshold": 95.0,
                "max_signals_per_day": 10,
                "max_trades_per_day": 5,
                "position_size_percent": 25.0,
                "supertrend_adx_weight": 60,
                "inside_bar_weight": 40
            }
        },
        "conservative": {
            "name": "Conservative",
            "description": "Lower risk settings for volatile markets",
            "parameters": {
                "confidence_threshold": 97.0,
                "max_signals_per_day": 5,
                "max_trades_per_day": 3,
                "position_size_percent": 15.0,
                "supertrend_adx_weight": 70,
                "inside_bar_weight": 30
            }
        },
        "aggressive": {
            "name": "Aggressive",
            "description": "Higher risk settings for trending markets",
            "parameters": {
                "confidence_threshold": 90.0,
                "max_signals_per_day": 15,
                "max_trades_per_day": 8,
                "position_size_percent": 40.0,
                "supertrend_adx_weight": 50,
                "inside_bar_weight": 50
            }
        }
    }
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ParameterManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
            
    def __init__(self):
        """Initialize the parameter manager"""
        if getattr(self, '_initialized', False):
            return
            
        # Create config directory if it doesn't exist
        self.base_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            self.CONFIG_DIR
        )
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Initialize parameters and profiles
        self.parameters = {}
        self.profiles = copy.deepcopy(self.DEFAULT_PROFILES)
        self.active_profile = "default"
        
        # Parameter change callbacks
        self.change_callbacks = []
        
        # Scheduled changes
        self.scheduled_changes = []
        
        # Load parameters and profiles
        self._load_parameters()
        self._load_profiles()
        
        # Initialize with default profile if needed
        if not self.parameters:
            self.apply_profile("default")
        
        # Set initialization flag
        self._initialized = True
        
        logger.info(f"Parameter manager initialized with active profile: {self.active_profile}")
    
    def _load_parameters(self) -> None:
        """Load parameters from file"""
        parameters_file = os.path.join(self.base_dir, self.PARAMETERS_FILE)
        try:
            if os.path.exists(parameters_file):
                with open(parameters_file, 'r') as f:
                    data = json.load(f)
                    self.parameters = data.get('parameters', {})
                    self.active_profile = data.get('active_profile', 'default')
                    logger.info(f"Loaded parameters from {parameters_file}")
        except Exception as e:
            logger.error(f"Error loading parameters: {e}", exc_info=True)
            # Load defaults if file can't be read
            self.parameters = self.profiles.get('default', {}).get('parameters', {})
    
    def _load_profiles(self) -> None:
        """Load parameter profiles from file"""
        profiles_file = os.path.join(self.base_dir, self.PROFILES_FILE)
        try:
            if os.path.exists(profiles_file):
                with open(profiles_file, 'r') as f:
                    self.profiles = json.load(f)
                    logger.info(f"Loaded parameter profiles from {profiles_file}")
        except Exception as e:
            logger.error(f"Error loading parameter profiles: {e}", exc_info=True)
            # Reset to defaults if file can't be read
            self.profiles = copy.deepcopy(self.DEFAULT_PROFILES)
    
    def _save_parameters(self) -> None:
        """Save parameters to file"""
        parameters_file = os.path.join(self.base_dir, self.PARAMETERS_FILE)
        try:
            data = {
                'parameters': self.parameters,
                'active_profile': self.active_profile,
                'last_updated': datetime.now().isoformat()
            }
            with open(parameters_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved parameters to {parameters_file}")
        except Exception as e:
            logger.error(f"Error saving parameters: {e}", exc_info=True)
    
    def _save_profiles(self) -> None:
        """Save parameter profiles to file"""
        profiles_file = os.path.join(self.base_dir, self.PROFILES_FILE)
        try:
            with open(profiles_file, 'w') as f:
                json.dump(self.profiles, f, indent=2)
            logger.info(f"Saved parameter profiles to {profiles_file}")
        except Exception as e:
            logger.error(f"Error saving parameter profiles: {e}", exc_info=True)
    
    def _log_parameter_change(self, parameter: str, old_value: Any, new_value: Any, 
                             source: str = "manual", reason: Optional[str] = None) -> None:
        """
        Log parameter change to audit trail
        
        Args:
            parameter: Name of parameter changed
            old_value: Previous value
            new_value: New value
            source: Source of change (manual, profile, scheduled)
            reason: Reason for change (optional)
        """
        audit_file = os.path.join(self.base_dir, self.AUDIT_FILE)
        try:
            # Create audit entry
            entry = {
                'timestamp': datetime.now().isoformat(),
                'parameter': parameter,
                'old_value': old_value,
                'new_value': new_value,
                'source': source,
                'profile': self.active_profile
            }
            
            if reason:
                entry['reason'] = reason
                
            # Append to audit file
            with open(audit_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
                
            # Notify via Telegram if available and significant change
            if TELEGRAM_AVAILABLE and telegram_notifier and telegram_notifier.is_configured:
                # Only notify for certain parameters or large changes
                should_notify = parameter in ['confidence_threshold', 'position_size_percent'] or source == 'profile'
                
                if should_notify:
                    msg = f"\ud83d\udcc8 *Parameter Change*\n\n"
                    msg += f"Parameter: `{parameter}`\n"
                    msg += f"Old value: `{old_value}`\n"
                    msg += f"New value: `{new_value}`\n"
                    msg += f"Source: {source}\n"
                    
                    if reason:
                        msg += f"Reason: {reason}\n"
                        
                    if source == 'profile':
                        msg += f"Profile: {self.active_profile}\n"
                        
                    telegram_notifier.send_message(msg)
                    
        except Exception as e:
            logger.error(f"Error logging parameter change: {e}", exc_info=True)
    
    def get_parameter(self, parameter: str, default: Any = None) -> Any:
        """
        Get parameter value
        
        Args:
            parameter: Name of parameter to get
            default: Default value if parameter not found
            
        Returns:
            Parameter value or default
        """
        # Check if parameter exists in current parameters
        if parameter in self.parameters:
            return self.parameters[parameter]
        
        # Check if parameter exists in constraints
        if parameter in self.PARAMETER_CONSTRAINTS:
            return self.PARAMETER_CONSTRAINTS[parameter]['default']
            
        # Return provided default
        return default
    
    def set_parameter(self, parameter: str, value: Any, source: str = "manual", 
                     reason: Optional[str] = None) -> bool:
        """
        Set parameter value with validation
        
        Args:
            parameter: Name of parameter to set
            value: Value to set
            source: Source of change (manual, profile, scheduled)
            reason: Reason for change (optional)
            
        Returns:
            True if parameter was set, False otherwise
        """
        # Check if parameter exists in constraints
        if parameter not in self.PARAMETER_CONSTRAINTS:
            logger.warning(f"Attempted to set unknown parameter: {parameter}")
            return False
            
        # Validate parameter value
        constraints = self.PARAMETER_CONSTRAINTS[parameter]
        param_type = constraints['type']
        
        # Convert value to the correct type
        try:
            if param_type == 'float':
                value = float(value)
            elif param_type == 'int':
                value = int(value)
            elif param_type == 'bool':
                if isinstance(value, str):
                    value = value.lower() in ['true', '1', 'yes']
                else:
                    value = bool(value)
        except (ValueError, TypeError):
            logger.error(f"Invalid type for parameter {parameter}: expected {param_type}")
            return False
            
        # Check value is within constraints
        if 'min' in constraints and value < constraints['min']:
            logger.warning(f"Value {value} for parameter {parameter} is below minimum {constraints['min']}")
            value = constraints['min']
            
        if 'max' in constraints and value > constraints['max']:
            logger.warning(f"Value {value} for parameter {parameter} is above maximum {constraints['max']}")
            value = constraints['max']
            
        # Get old value for audit trail
        old_value = self.parameters.get(parameter, constraints.get('default'))
        
        # Set parameter if it has changed
        if old_value != value:
            self.parameters[parameter] = value
            
            # Log change to audit trail
            self._log_parameter_change(parameter, old_value, value, source, reason)
            
            # Save parameters to file
            self._save_parameters()
            
            # Trigger callbacks
            self._trigger_change_callbacks(parameter, old_value, value)
            
            logger.info(f"Parameter {parameter} changed from {old_value} to {value} [{source}]")
            return True
        
        return False
    
    def get_all_parameters(self) -> Dict[str, Any]:
        """
        Get all parameters
        
        Returns:
            Dictionary of all parameters
        """
        return self.parameters.copy()
    
    def set_multiple_parameters(self, parameters: Dict[str, Any], source: str = "manual", 
                              reason: Optional[str] = None) -> Dict[str, bool]:
        """
        Set multiple parameters at once
        
        Args:
            parameters: Dictionary of parameter names and values
            source: Source of change
            reason: Reason for change
            
        Returns:
            Dictionary of parameter names and success/failure
        """
        results = {}
        
        for param, value in parameters.items():
            results[param] = self.set_parameter(param, value, source, reason)
            
        return results
    
    def reset_to_defaults(self) -> None:
        """Reset all parameters to default values"""
        default_params = {}
        for param, constraints in self.PARAMETER_CONSTRAINTS.items():
            default_params[param] = constraints['default']
            
        self.set_multiple_parameters(default_params, source="reset", reason="Reset to defaults")
        self.active_profile = "default"
        self._save_parameters()
        
        logger.info("Parameters reset to defaults")
    
    def get_profiles(self) -> Dict[str, Dict]:
        """
        Get all available parameter profiles
        
        Returns:
            Dictionary of profile IDs and metadata
        """
        return {k: {
            'name': v.get('name', k),
            'description': v.get('description', ''),
            'is_active': k == self.active_profile
        } for k, v in self.profiles.items()}
    
    def get_profile_details(self, profile_id: str) -> Optional[Dict]:
        """
        Get details of a specific profile
        
        Args:
            profile_id: ID of the profile to get
            
        Returns:
            Profile details or None if not found
        """
        if profile_id in self.profiles:
            return copy.deepcopy(self.profiles[profile_id])
        return None
    
    def create_profile(self, profile_id: str, name: str, description: str, 
                     parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a new parameter profile
        
        Args:
            profile_id: ID of the new profile
            name: Display name of the profile
            description: Description of the profile
            parameters: Parameter values for the profile (defaults to current parameters)
            
        Returns:
            True if profile was created, False otherwise
        """
        if profile_id in self.profiles:
            logger.warning(f"Profile {profile_id} already exists")
            return False
            
        # Use current parameters if none provided
        if parameters is None:
            parameters = self.parameters.copy()
            
        # Create profile
        self.profiles[profile_id] = {
            'name': name,
            'description': description,
            'parameters': parameters,
            'created': datetime.now().isoformat()
        }
        
        # Save profiles to file
        self._save_profiles()
        
        logger.info(f"Created new parameter profile: {profile_id}")
        return True
    
    def update_profile(self, profile_id: str, name: Optional[str] = None, 
                      description: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update an existing parameter profile
        
        Args:
            profile_id: ID of the profile to update
            name: New display name (optional)
            description: New description (optional)
            parameters: New parameter values (optional)
            
        Returns:
            True if profile was updated, False otherwise
        """
        if profile_id not in self.profiles:
            logger.warning(f"Profile {profile_id} does not exist")
            return False
            
        # Update profile fields
        profile = self.profiles[profile_id]
        
        if name is not None:
            profile['name'] = name
            
        if description is not None:
            profile['description'] = description
            
        if parameters is not None:
            profile['parameters'] = parameters
            
        profile['updated'] = datetime.now().isoformat()
        
        # Save profiles to file
        self._save_profiles()
        
        logger.info(f"Updated parameter profile: {profile_id}")
        return True
    
    def delete_profile(self, profile_id: str) -> bool:
        """
        Delete a parameter profile
        
        Args:
            profile_id: ID of the profile to delete
            
        Returns:
            True if profile was deleted, False otherwise
        """
        # Don't allow deleting the active profile
        if profile_id == self.active_profile:
            logger.warning(f"Cannot delete active profile: {profile_id}")
            return False
            
        # Don't allow deleting default profiles
        if profile_id in self.DEFAULT_PROFILES:
            logger.warning(f"Cannot delete default profile: {profile_id}")
            return False
            
        if profile_id in self.profiles:
            del self.profiles[profile_id]
            self._save_profiles()
            logger.info(f"Deleted parameter profile: {profile_id}")
            return True
            
        logger.warning(f"Profile {profile_id} does not exist")
        return False
    
    def apply_profile(self, profile_id: str, reason: Optional[str] = None) -> bool:
        """
        Apply a parameter profile
        
        Args:
            profile_id: ID of the profile to apply
            reason: Reason for profile change (optional)
            
        Returns:
            True if profile was applied, False otherwise
        """
        if profile_id not in self.profiles:
            logger.warning(f"Profile {profile_id} does not exist")
            return False
            
        # Get profile parameters
        profile = self.profiles[profile_id]
        profile_params = profile.get('parameters', {})
        
        # Apply all parameters
        self.set_multiple_parameters(profile_params, source="profile", 
                                   reason=reason or f"Applied profile: {profile['name']}")
        
        # Update active profile
        self.active_profile = profile_id
        self._save_parameters()
        
        logger.info(f"Applied parameter profile: {profile_id}")
        return True
    
    def register_change_callback(self, callback: Callable[[str, Any, Any], None]) -> None:
        """
        Register a callback for parameter changes
        
        Args:
            callback: Function to call when parameters change
                     Function signature: callback(parameter_name, old_value, new_value)
        """
        if callback not in self.change_callbacks:
            self.change_callbacks.append(callback)
    
    def _trigger_change_callbacks(self, parameter: str, old_value: Any, new_value: Any) -> None:
        """
        Trigger registered callbacks for parameter changes
        
        Args:
            parameter: Name of changed parameter
            old_value: Previous value
            new_value: New value
        """
        for callback in self.change_callbacks:
            try:
                callback(parameter, old_value, new_value)
            except Exception as e:
                logger.error(f"Error in parameter change callback: {e}", exc_info=True)
    
    def schedule_parameter_change(self, parameter: str, value: Any, 
                                when: Union[datetime, str], reason: Optional[str] = None) -> str:
        """
        Schedule a parameter change for a future time
        
        Args:
            parameter: Parameter to change
            value: New value to set
            when: When to apply the change (datetime or string like "2023-12-25 08:30:00")
            reason: Reason for the change
            
        Returns:
            ID of scheduled change
        """
        # Convert string time to datetime if needed
        if isinstance(when, str):
            try:
                when = datetime.fromisoformat(when.replace(' ', 'T'))
            except ValueError:
                logger.error(f"Invalid datetime format: {when}")
                return ""
                
        # Generate ID for the scheduled change
        change_id = f"change_{int(time.time())}_{parameter}"
        
        # Create scheduled change
        scheduled_change = {
            'id': change_id,
            'parameter': parameter,
            'value': value,
            'when': when.isoformat(),
            'reason': reason or f"Scheduled change of {parameter}",
            'created': datetime.now().isoformat()
        }
        
        # Add to scheduled changes
        self.scheduled_changes.append(scheduled_change)
        
        # Schedule the job
        schedule_time = when.strftime("%H:%M")
        schedule_job = schedule.every().day.at(schedule_time).do(
            self._apply_scheduled_change, change_id=change_id
        )
        
        logger.info(f"Scheduled parameter change: {parameter} to {value} at {when}")
        return change_id
    
    def cancel_scheduled_change(self, change_id: str) -> bool:
        """
        Cancel a scheduled parameter change
        
        Args:
            change_id: ID of the scheduled change to cancel
            
        Returns:
            True if change was cancelled, False otherwise
        """
        for i, change in enumerate(self.scheduled_changes):
            if change['id'] == change_id:
                # Remove from scheduled changes
                del self.scheduled_changes[i]
                logger.info(f"Cancelled scheduled parameter change: {change_id}")
                return True
                
        logger.warning(f"Scheduled change {change_id} not found")
        return False
    
    def get_scheduled_changes(self) -> List[Dict]:
        """
        Get all scheduled parameter changes
        
        Returns:
            List of scheduled changes
        """
        # Sort by scheduled time
        sorted_changes = sorted(self.scheduled_changes, key=lambda x: x['when'])
        return copy.deepcopy(sorted_changes)
    
    def _apply_scheduled_change(self, change_id: str) -> None:
        """
        Apply a scheduled parameter change
        
        Args:
            change_id: ID of the scheduled change to apply
        """
        # Find the scheduled change
        change = None
        for i, c in enumerate(self.scheduled_changes):
            if c['id'] == change_id:
                change = c
                del self.scheduled_changes[i]
                break
                
        if not change:
            logger.warning(f"Scheduled change {change_id} not found")
            return
            
        # Apply the change
        parameter = change['parameter']
        value = change['value']
        reason = change['reason']
        
        logger.info(f"Applying scheduled parameter change: {parameter} to {value}")
        self.set_parameter(parameter, value, source="scheduled", reason=reason)
    
    def get_parameter_constraints(self) -> Dict[str, Dict]:
        """
        Get all parameter constraints
        
        Returns:
            Dictionary of parameter constraints
        """
        return copy.deepcopy(self.PARAMETER_CONSTRAINTS)
    
    def get_parameter_audit_trail(self, parameter: Optional[str] = None, 
                                limit: int = 100) -> List[Dict]:
        """
        Get parameter change audit trail
        
        Args:
            parameter: Filter by specific parameter (optional)
            limit: Maximum number of entries to return
            
        Returns:
            List of audit trail entries
        """
        audit_file = os.path.join(self.base_dir, self.AUDIT_FILE)
        entries = []
        
        try:
            if os.path.exists(audit_file):
                with open(audit_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            # Filter by parameter if specified
                            if parameter is None or entry.get('parameter') == parameter:
                                entries.append(entry)
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON in audit trail: {line}")
                            
        except Exception as e:
            logger.error(f"Error reading audit trail: {e}", exc_info=True)
            
        # Sort by timestamp (newest first) and limit
        entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return entries[:limit]

# Singleton instance
parameter_manager = ParameterManager()
