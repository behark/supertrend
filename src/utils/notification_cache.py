#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import os
from threading import Lock
from datetime import datetime
from typing import Dict, Optional, List, Tuple

# Configure logging
logger = logging.getLogger(__name__)

class NotificationCache:
    """Enhanced notification cache with severity levels and summary notifications"""
    
    # Class variables shared across all instances
    _instance = None
    _lock = Lock()
    
    # Cache of notification info by type and key
    _notification_data = {}
    
    # Suppressed notification counters
    _suppressed_counts = {}
    
    # Last time a summary was sent
    _last_summary_time = 0
    _summary_cooldown = 3600  # 1 hour between summaries
    
    # Default cooldown periods (seconds)
    DEFAULT_COOLDOWNS = {
        # Standard notification types
        'insufficient_balance': 7200,  # 2 hours (reduced from 4 hours)
        'error': 3600,                 # 1 hour (reduced from 4 hours)
        'critical_error': 300,         # 5 minutes for critical errors
        'signal': 14400,               # 4 hours
        'general': 3600,               # 1 hour
        'position_update': 1800,       # 30 minutes
        
        # Severity-based cooldowns
        'low': 14400,     # 4 hours for low severity
        'medium': 3600,   # 1 hour for medium severity
        'high': 900,      # 15 minutes for high severity
        'critical': 300   # 5 minutes for critical severity
    }
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(NotificationCache, cls).__new__(cls)
                logger.info("Initializing enhanced notification cache with severity tracking")
            return cls._instance
    
    def should_send(self, notification_type: str, key: Optional[str] = None, 
                    cooldown: Optional[int] = None, severity: str = 'medium',
                    always_notify_critical: bool = True) -> bool:
        """Check if notification should be sent based on cooldown period and severity
        
        Args:
            notification_type: Type of notification (e.g., 'error', 'signal')
            key: Optional key to distinguish notifications of same type
            cooldown: Optional override of default cooldown period (seconds)
            severity: Notification severity ('low', 'medium', 'high', 'critical')
            always_notify_critical: If True, critical severity notifications bypass cooldown
            
        Returns:
            bool: True if notification should be sent
        """
        # Generate a composite key for the cache
        cache_key = f"{notification_type}:{key if key else 'global'}"
        
        # Get current time
        current_time = time.time()
        
        # Critical notifications can bypass cooldown
        if severity == 'critical' and always_notify_critical:
            logger.info(f"Critical notification allowed: {cache_key}")
            
            # Track in notification data
            self._notification_data[cache_key] = {
                'last_time': current_time,
                'count': self._notification_data.get(cache_key, {}).get('count', 0) + 1,
                'type': notification_type,
                'key': key,
                'severity': severity
            }
            return True
        
        # Use provided cooldown, severity-based cooldown, or type-based cooldown
        if cooldown is None:
            # Try severity cooldown first, then type cooldown, then default
            cooldown = self.DEFAULT_COOLDOWNS.get(
                severity, 
                self.DEFAULT_COOLDOWNS.get(
                    notification_type, 
                    self.DEFAULT_COOLDOWNS['general']
                )
            )
        
        # Check if we've sent this notification recently
        last_data = self._notification_data.get(cache_key, {'last_time': 0, 'count': 0})
        last_time = last_data.get('last_time', 0)
        time_since_last = current_time - last_time
        
        # If cooldown period has passed, allow the notification
        if time_since_last > cooldown:
            # Update the notification data
            self._notification_data[cache_key] = {
                'last_time': current_time,
                'count': 1,  # Reset count to 1 for a new notification cycle
                'type': notification_type,
                'key': key,
                'severity': severity
            }
            
            # Check if we need to send a summary of suppressed notifications
            self._maybe_send_summary(current_time)
            
            logger.info(f"Allowing notification: {cache_key} (last was {time_since_last:.1f}s ago)")
            return True
        else:
            # Increment suppressed count for this key
            self._suppressed_counts[cache_key] = self._suppressed_counts.get(cache_key, 0) + 1
            
            # Increment count in notification data
            count = last_data.get('count', 0) + 1
            self._notification_data[cache_key]['count'] = count
            
            # Log that we're suppressing a duplicate
            logger.info(f"Suppressing duplicate notification: {cache_key} (last was {time_since_last:.1f}s ago, count: {count})")
            
            # For high severity, force notification after multiple suppressions
            if severity in ['high', 'critical'] and count % 5 == 0:  # Every 5th occurrence for high severity
                logger.info(f"Forcing notification due to repeated high severity issue: {cache_key} (occurrence {count})")
                return True
                
            return False
    
    def _maybe_send_summary(self, current_time: float) -> None:
        """Send a summary of suppressed notifications if cooldown period has passed"""
        if not self._suppressed_counts or current_time - self._last_summary_time < self._summary_cooldown:
            return
            
        # Generate summary message
        summary = self._generate_summary()
        if summary:
            # Try to send via Telegram if available
            try:
                from src.integrations.telegram import TelegramNotifier
                telegram = TelegramNotifier()
                if telegram.is_configured:
                    telegram.send_message(summary)
                    logger.info("Sent suppressed notifications summary via Telegram")
            except Exception as e:
                logger.error(f"Failed to send summary via Telegram: {e}")
                
            # Reset the suppressed counts after sending summary
            self._suppressed_counts.clear()
            self._last_summary_time = current_time
    
    def _generate_summary(self) -> str:
        """Generate a summary message of suppressed notifications"""
        if not self._suppressed_counts:
            return ""
            
        summary_lines = ["📊 *Suppressed Notifications Summary*\n"]
        
        # Group by notification type
        grouped_counts = {}
        for key, count in self._suppressed_counts.items():
            notification_type = key.split(':', 1)[0]
            if notification_type not in grouped_counts:
                grouped_counts[notification_type] = []
            
            # Get specific key and data
            specific_key = key.split(':', 1)[1] if ':' in key else 'global'
            notification_data = self._notification_data.get(key, {})
            severity = notification_data.get('severity', 'medium')
            
            grouped_counts[notification_type].append((specific_key, count, severity))
        
        # Format the summary by type
        for notification_type, items in grouped_counts.items():
            summary_lines.append(f"*{notification_type.upper()}*")
            for key, count, severity in items:
                severity_emoji = {'low': '🟢', 'medium': '🟡', 'high': '🔴', 'critical': '⚠️'}.get(severity, '•')
                summary_lines.append(f"{severity_emoji} {key}: {count} occurrences")
            summary_lines.append("")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary_lines.append(f"Generated at {timestamp}")
        
        return "\n".join(summary_lines)
    
    def reset(self, notification_type: Optional[str] = None, key: Optional[str] = None) -> None:
        """Reset notification cache for a type, key, or all"""
        with self._lock:
            if notification_type and key:
                # Reset specific notification
                cache_key = f"{notification_type}:{key}"
                if cache_key in self._notification_data:
                    del self._notification_data[cache_key]
                if cache_key in self._suppressed_counts:
                    del self._suppressed_counts[cache_key]
                logger.info(f"Reset notification cache for {cache_key}")
            elif notification_type:
                # Reset all of a type
                keys_to_remove = [k for k in self._notification_data if k.startswith(f"{notification_type}:")]
                for k in keys_to_remove:
                    del self._notification_data[k]
                    if k in self._suppressed_counts:
                        del self._suppressed_counts[k]
                logger.info(f"Reset notification cache for type {notification_type}")
            else:
                # Reset all
                self._notification_data.clear()
                self._suppressed_counts.clear()
                self._last_summary_time = 0
                logger.info("Reset all notification cache data")

# Singleton instance for easy import
notification_cache = NotificationCache()
