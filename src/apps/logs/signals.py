"""
Signal handlers for logging system lifecycle management.

Ensures graceful shutdown and buffer flushing on app termination.
"""

import logging
import signal
import sys

from django.core.signals import request_finished

from .utils import LoggingShutdownManager, LoggingMetricsCollector

logger = logging.getLogger(__name__)


def handle_sigterm(signum, frame):
    """Handle SIGTERM signal (graceful shutdown)."""
    logger.info("Received SIGTERM signal, draining logging buffers...")
    
    summary = LoggingShutdownManager.shutdown(timeout=10.0)
    logger.info(f"Logging shutdown summary: {summary}")
    
    sys.exit(0)


def handle_sigint(signum, frame):
    """Handle SIGINT signal (Ctrl+C)."""
    logger.info("Received SIGINT signal, draining logging buffers...")
    
    summary = LoggingShutdownManager.shutdown(timeout=5.0)
    logger.info(f"Logging shutdown summary: {summary}")
    
    sys.exit(0)


def setup_logging_signals():
    """
    Setup signal handlers for logging lifecycle.
    
    Should be called during app initialization.
    """
    try:
        signal.signal(signal.SIGTERM, handle_sigterm)
        signal.signal(signal.SIGINT, handle_sigint)
        logger.debug("Logging signal handlers installed")
    except Exception as e:
        logger.warning(f"Could not install logging signal handlers: {e}")


def check_logging_health():
    """
    Check logging health and log warnings if necessary.
    
    Should be called periodically (e.g., via a task).
    """
    try:
        metrics = LoggingMetricsCollector.get_buffer_health()
        
        # Check for dropped records
        if metrics['total_dropped'] > 0:
            logger.warning(
                f"Logging health check: {metrics['total_dropped']} logs dropped "
                f"(buffer utilization: {metrics['avg_buffer_utilization']}%)"
            )
        
        # Check for high utilization
        if metrics['avg_buffer_utilization'] > 80:
            logger.warning(
                f"Logging health check: High buffer utilization "
                f"{metrics['avg_buffer_utilization']}% - consider increasing buffer size"
            )
        
        return True
        
    except Exception as e:
        logger.error(f"Logging health check failed: {e}")
        return False
