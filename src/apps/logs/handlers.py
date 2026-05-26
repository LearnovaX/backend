"""
Logging handlers for the application.

Includes:
- DatabaseHandler: Writes logs to the database
- QueueAwareLoggingMixin: Makes handlers work well with queue listeners
"""

import logging
from typing import Optional

from django.utils import timezone


class DatabaseHandler(logging.Handler):
    """
    Handler that writes log records to the database.
    
    Best used with QueueHandler to avoid blocking I/O on application threads.
    """
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to the database.
        
        Args:
            record: The log record to write
        """
        try:
            from src.apps.logs.models import LogEntry

            LogEntry.objects.create(
                timestamp=timezone.now(),
                level=record.levelname,
                logger_name=record.name,
                message=self.format(record),
                pathname=record.pathname,
                line_no=record.lineno,
                exception=record.exc_info if record.exc_info else None,
            )
        except Exception:
            # Silently ignore errors to prevent logging from breaking the app
            pass


class QueueAwareLoggingMixin:
    """
    Mixin to make handlers aware of queue-based logging.
    
    Useful for handlers that need to behave differently when processing
    records from a queue vs directly emitted records.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the mixin."""
        super().__init__(*args, **kwargs)
        self._is_processing_queue = False
    
    def set_queue_mode(self, enabled: bool) -> None:
        """
        Set whether this handler is processing queue records.
        
        Args:
            enabled: True if processing queued records, False otherwise
        """
        self._is_processing_queue = enabled
    
    def is_queue_mode(self) -> bool:
        """Check if handler is in queue processing mode."""
        return self._is_processing_queue


class OptimizedDatabaseHandler(QueueAwareLoggingMixin, DatabaseHandler):
    """
    Database handler optimized for queue-based logging.
    
    Can batch database writes when processing queued records.
    """
    
    def __init__(self, batch_size: int = 100, *args, **kwargs):
        """
        Initialize the optimized database handler.
        
        Args:
            batch_size: Number of records to batch before writing
        """
        super().__init__(*args, **kwargs)
        self.batch_size = batch_size
        self._batch = []
        self._batch_lock = __import__('threading').Lock()
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record, optionally batching for efficiency.
        
        Args:
            record: The log record to write
        """
        if not self.is_queue_mode():
            # Direct mode: write immediately
            super().emit(record)
            return
        
        # Queue mode: batch writes
        with self._batch_lock:
            self._batch.append(record)
            if len(self._batch) >= self.batch_size:
                self._flush_batch()
    
    def _flush_batch(self) -> None:
        """Flush the batch of records to the database."""
        if not self._batch:
            return
        
        try:
            from src.apps.logs.models import LogEntry
            
            entries = [
                LogEntry(
                    timestamp=timezone.now(),
                    level=record.levelname,
                    logger_name=record.name,
                    message=self.format(record),
                    pathname=record.pathname,
                    line_no=record.lineno,
                    exception=record.exc_info if record.exc_info else None,
                )
                for record in self._batch
            ]
            
            LogEntry.objects.bulk_create(entries)
            self._batch.clear()
            
        except Exception:
            # Clear batch and continue on error
            self._batch.clear()
    
    def close(self) -> None:
        """Close the handler and flush remaining batch."""
        self._flush_batch()
        super().close()
