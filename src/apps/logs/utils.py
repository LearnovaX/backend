"""
Utilities for managing and monitoring in-memory logging.

Provides APIs for:
- Getting buffer metrics and statistics
- Draining buffers for shutdown
- Configuring logging behavior at runtime
"""

import logging
from typing import Dict, List, Optional

from .in_memory_logger import (
    get_all_buffer_metrics,
    get_buffer_metrics,
    get_in_memory_handler,
    drain_all_buffers,
)
from .queue_listener import shutdown_queue_listeners


class LoggingMetricsCollector:
    """Collect and expose logging metrics for monitoring."""
    
    @staticmethod
    def get_buffer_health() -> Dict[str, any]:
        """
        Get health metrics for all in-memory log buffers.
        
        Returns:
            Dictionary with buffer statistics and health status
        """
        metrics = get_all_buffer_metrics()
        
        total_records = sum(m.get('total_records', 0) for m in metrics.values())
        total_dropped = sum(m.get('dropped_records', 0) for m in metrics.values())
        avg_utilization = sum(m.get('buffer_utilization', 0) for m in metrics.values()) / len(metrics) if metrics else 0
        
        return {
            'total_records': total_records,
            'total_dropped': total_dropped,
            'avg_buffer_utilization': round(avg_utilization, 2),
            'buffers': metrics,
        }
    
    @staticmethod
    def get_handler_metrics(name: str = 'default') -> Optional[Dict]:
        """
        Get metrics for a specific handler.
        
        Args:
            name: Name of the handler
        
        Returns:
            Dictionary with handler metrics or None if not found
        """
        metrics = get_buffer_metrics(name)
        if metrics:
            return metrics.to_dict()
        return None


class LoggingShutdownManager:
    """Manage graceful logging shutdown."""
    
    @staticmethod
    def shutdown(timeout: float = 10.0) -> Dict[str, any]:
        """
        Shutdown logging and drain all buffers.
        
        Should be called during application shutdown to ensure all logs
        are flushed to their final destinations.
        
        Args:
            timeout: Maximum time to wait for shutdown
        
        Returns:
            Summary of shutdown process
        """
        summary = {
            'status': 'shutting_down',
            'drained_buffers': {},
            'final_metrics': None,
            'shutdown_time': timeout,
        }
        
        # Get final metrics before shutdown
        summary['final_metrics'] = LoggingMetricsCollector.get_buffer_health()
        
        # Drain all buffers
        drained = drain_all_buffers(timeout=timeout)
        summary['drained_buffers'] = {
            name: len(records) if isinstance(records, list) else 0
            for name, records in drained.items()
        }
        
        # Shutdown queue listeners
        try:
            shutdown_queue_listeners(timeout=timeout)
            summary['status'] = 'shutdown_complete'
        except Exception as e:
            summary['status'] = 'shutdown_error'
            summary['error'] = str(e)
        
        return summary


def get_buffered_logs(name: str = 'default') -> List[logging.LogRecord]:
    """
    Get and clear all buffered log records.
    
    Args:
        name: Name of the handler
    
    Returns:
        List of buffered log records
    """
    handler = get_in_memory_handler(name)
    if handler:
        return handler.get_records()
    return []


def get_buffered_logs_as_dicts(name: str = 'default') -> List[Dict]:
    """
    Get all buffered log records as dictionaries.
    
    Useful for API responses and JSON serialization.
    
    Args:
        name: Name of the handler
    
    Returns:
        List of log record dictionaries
    """
    records = get_buffered_logs(name)
    return [
        {
            'timestamp': record.created,
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        for record in records
    ]


def set_log_level(logger_name: str, level: str) -> None:
    """
    Change the log level for a specific logger at runtime.
    
    Args:
        logger_name: Name of the logger
        level: Log level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper()))


def get_log_level(logger_name: str) -> str:
    """
    Get the current log level for a logger.
    
    Args:
        logger_name: Name of the logger
    
    Returns:
        Log level as string
    """
    logger = logging.getLogger(logger_name)
    return logging.getLevelName(logger.level)


def configure_logging_for_high_scale(
    buffer_size: int = 20000,
    queue_size: int = 10000,
    flush_interval: float = 3.0,
    batch_size: int = 200,
) -> None:
    """
    Reconfigure logging for high-scale scenarios.
    
    Increases buffer sizes and reduces flush intervals for better throughput.
    
    Args:
        buffer_size: Size of in-memory buffer
        queue_size: Size of processing queue
        flush_interval: How often to flush (seconds)
        batch_size: Database batch size
    
    Note:
        This should be called early in application initialization.
    """
    from django.conf import settings
    
    settings.IN_MEMORY_LOG_BUFFER_SIZE = buffer_size
    settings.IN_MEMORY_LOG_QUEUE_SIZE = queue_size
    settings.IN_MEMORY_LOG_FLUSH_INTERVAL = flush_interval
    settings.IN_MEMORY_LOG_BATCH_SIZE = batch_size
