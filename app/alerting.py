"""Alerting system for Y-Connect WhatsApp Bot

Monitors application metrics and triggers alerts based on thresholds.
"""

import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio
from collections import deque

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data structure"""
    name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    metric_value: Optional[float] = None
    threshold: Optional[float] = None


class AlertManager:
    """
    Manages alerting based on application metrics.
    
    Monitors:
    - Error rate >5% over 5 minutes
    - Response time >10s for >10% of requests
    - Database/vector store unavailability
    - LLM API failures
    """
    
    def __init__(self):
        """Initialize AlertManager"""
        self.alert_handlers: List[Callable] = []
        self.alert_history: deque = deque(maxlen=1000)
        
        # Metric tracking windows
        self.error_window = deque(maxlen=100)  # Last 100 requests
        self.response_time_window = deque(maxlen=100)  # Last 100 requests
        
        # Alert cooldown to prevent spam (5 minutes)
        self.alert_cooldown: Dict[str, datetime] = {}
        self.cooldown_duration = timedelta(minutes=5)
        
        # Thresholds
        self.error_rate_threshold = 0.05  # 5%
        self.slow_response_threshold = 10.0  # 10 seconds
        self.slow_response_percentage_threshold = 0.10  # 10%
        
        logger.info("AlertManager initialized")
    
    def register_alert_handler(self, handler: Callable[[Alert], None]):
        """
        Register a handler function to be called when alerts are triggered
        
        Args:
            handler: Function that takes an Alert object
        """
        self.alert_handlers.append(handler)
        logger.info(f"Registered alert handler: {handler.__name__}")
    
    def _should_send_alert(self, alert_name: str) -> bool:
        """
        Check if alert should be sent based on cooldown
        
        Args:
            alert_name: Name of the alert
            
        Returns:
            True if alert should be sent, False if in cooldown
        """
        if alert_name not in self.alert_cooldown:
            return True
        
        last_alert_time = self.alert_cooldown[alert_name]
        if datetime.utcnow() - last_alert_time > self.cooldown_duration:
            return True
        
        return False
    
    def _trigger_alert(self, alert: Alert):
        """
        Trigger an alert by calling all registered handlers
        
        Args:
            alert: Alert object to send
        """
        if not self._should_send_alert(alert.name):
            logger.debug(f"Alert {alert.name} in cooldown, skipping")
            return
        
        # Update cooldown
        self.alert_cooldown[alert.name] = datetime.utcnow()
        
        # Add to history
        self.alert_history.append(alert)
        
        # Log alert
        logger.warning(
            f"ALERT [{alert.severity.value.upper()}] {alert.name}: {alert.message}",
            extra={
                "alert_name": alert.name,
                "severity": alert.severity.value,
                "metric_value": alert.metric_value,
                "threshold": alert.threshold
            }
        )
        
        # Call handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler {handler.__name__}: {e}")
    
    def track_request_error(self, is_error: bool):
        """
        Track a request result for error rate monitoring
        
        Args:
            is_error: True if request resulted in error
        """
        self.error_window.append(1 if is_error else 0)
        
        # Check error rate if we have enough samples
        if len(self.error_window) >= 20:  # Minimum 20 requests
            error_rate = sum(self.error_window) / len(self.error_window)
            
            if error_rate > self.error_rate_threshold:
                alert = Alert(
                    name="high_error_rate",
                    severity=AlertSeverity.ERROR,
                    message=f"Error rate {error_rate:.1%} exceeds threshold {self.error_rate_threshold:.1%}",
                    timestamp=datetime.utcnow(),
                    metric_value=error_rate,
                    threshold=self.error_rate_threshold
                )
                self._trigger_alert(alert)
    
    def track_response_time(self, duration: float):
        """
        Track a request response time for SLA monitoring
        
        Args:
            duration: Response time in seconds
        """
        self.response_time_window.append(duration)
        
        # Check slow response percentage if we have enough samples
        if len(self.response_time_window) >= 20:  # Minimum 20 requests
            slow_count = sum(1 for d in self.response_time_window if d > self.slow_response_threshold)
            slow_percentage = slow_count / len(self.response_time_window)
            
            if slow_percentage > self.slow_response_percentage_threshold:
                alert = Alert(
                    name="high_response_time",
                    severity=AlertSeverity.WARNING,
                    message=f"{slow_percentage:.1%} of requests exceed {self.slow_response_threshold}s threshold",
                    timestamp=datetime.utcnow(),
                    metric_value=slow_percentage,
                    threshold=self.slow_response_percentage_threshold
                )
                self._trigger_alert(alert)
    
    def alert_database_unavailable(self, database_name: str, error: str):
        """
        Alert on database unavailability
        
        Args:
            database_name: Name of the database (postgres, redis, vector_store)
            error: Error message
        """
        alert = Alert(
            name=f"database_unavailable_{database_name}",
            severity=AlertSeverity.CRITICAL,
            message=f"Database {database_name} is unavailable: {error}",
            timestamp=datetime.utcnow()
        )
        self._trigger_alert(alert)
    
    def alert_llm_api_failure(self, provider: str, error: str, failure_count: int = 1):
        """
        Alert on LLM API failures
        
        Args:
            provider: LLM provider name
            error: Error message
            failure_count: Number of consecutive failures
        """
        severity = AlertSeverity.WARNING if failure_count < 3 else AlertSeverity.ERROR
        
        alert = Alert(
            name=f"llm_api_failure_{provider}",
            severity=severity,
            message=f"LLM API {provider} failure (count: {failure_count}): {error}",
            timestamp=datetime.utcnow(),
            metric_value=float(failure_count)
        )
        self._trigger_alert(alert)
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """
        Get recent alert history
        
        Args:
            limit: Maximum number of alerts to return
            
        Returns:
            List of recent alerts
        """
        return list(self.alert_history)[-limit:]
    
    def clear_alert_cooldown(self, alert_name: Optional[str] = None):
        """
        Clear alert cooldown (for testing or manual reset)
        
        Args:
            alert_name: Specific alert to clear, or None to clear all
        """
        if alert_name:
            if alert_name in self.alert_cooldown:
                del self.alert_cooldown[alert_name]
                logger.info(f"Cleared cooldown for alert: {alert_name}")
        else:
            self.alert_cooldown.clear()
            logger.info("Cleared all alert cooldowns")


# Global alert manager instance
alert_manager = AlertManager()


# Default alert handlers

def log_alert_handler(alert: Alert):
    """
    Default handler that logs alerts
    
    Args:
        alert: Alert to log
    """
    logger.warning(
        f"Alert Handler: [{alert.severity.value.upper()}] {alert.name}",
        extra={
            "alert_name": alert.name,
            "severity": alert.severity.value,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat()
        }
    )


# Register default handler
alert_manager.register_alert_handler(log_alert_handler)
