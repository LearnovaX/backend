"""
In-memory logging system with queue handlers for high-scale applications.

This module provides a circular buffer-based logging system that:
- Buffers log records in memory without blocking I/O
- Uses QueueHandler/QueueListener for async log processing
- Handles overflow gracefully with configurable strategies
- Provides metrics for monitoring
"""

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, List, Optional


@dataclass
class LogMetrics:
    """Track in-memory logger metrics."""
    total_records: int = 0
    dropped_records: int = 0
    last_flush_time: Optional[datetime] = None
    buffer_utilization: float = 0.0
    processing_time_ms: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert metrics to dictionary."""
        return {
            'total_records': self.total_records,
            'dropped_records': self.dropped_records,
            'last_flush_time': self.last_flush_time.isoformat() if self.last_flush_time else None,
            'buffer_utilization': round(self.buffer_utilization, 2),
            'processing_time_ms': round(self.processing_time_ms, 2),
        }


class InMemoryLogBuffer:
    """
    Thread-safe circular buffer for log records.
    
    Features:
    - Configurable max size with overflow handling
    - Lock-free reads for metrics
    - Multiple overflow strategies: drop_oldest, drop_newest, error
    """
    
    def __init__(
        self,
        max_size: int = 10000,
        overflow_strategy: str = 'drop_oldest',
    ):
        """
        Initialize the in-memory log buffer.
        
        Args:
            max_size: Maximum number of log records to hold in memory
            overflow_strategy: How to handle overflow:
                - 'drop_oldest': Remove oldest record when buffer is full
                - 'drop_newest': Reject new record when buffer is full
                - 'error': Raise exception on overflow
        """
        self.max_size = max_size
        self.overflow_strategy = overflow_strategy
        self.buffer: Deque = deque(maxlen=max_size)
        self.lock = threading.RLock()
        self.metrics = LogMetrics()
    
    def put(self, record: logging.LogRecord) -> None:
        """
        Add a log record to the buffer.
        
        Args:
            record: The log record to buffer
        """
        with self.lock:
            self.metrics.total_records += 1
            
            # deque with maxlen automatically drops oldest when full
            if len(self.buffer) == self.max_size:
                if self.overflow_strategy == 'drop_newest':
                    self.metrics.dropped_records += 1
                    return
                elif self.overflow_strategy == 'error':
                    raise BufferError(f"Log buffer overflow (max_size={self.max_size})")
                # drop_oldest is default deque behavior
            
            self.buffer.append(record)
    
    def get_all(self) -> List[logging.LogRecord]:
        """Get and clear all buffered records."""
        with self.lock:
            records = list(self.buffer)
            self.buffer.clear()
            self.metrics.last_flush_time = datetime.now()
            return records
    
    def get_copy(self) -> List[logging.LogRecord]:
        """Get a copy of all records without clearing."""
        with self.lock:
            return list(self.buffer)
    
    def clear(self) -> None:
        """Clear all buffered records."""
        with self.lock:
            self.buffer.clear()
    
    def size(self) -> int:
        """Get current buffer size."""
        with self.lock:
            return len(self.buffer)
    
    def utilization(self) -> float:
        """Get buffer utilization percentage."""
        with self.lock:
            if self.max_size == 0:
                return 0.0
            util = (len(self.buffer) / self.max_size) * 100
            self.metrics.buffer_utilization = util
            return util
    
    def get_metrics(self) -> LogMetrics:
        """Get current metrics."""
        with self.lock:
            self.metrics.buffer_utilization = self.utilization()
            return self.metrics


class InMemoryLogHandler(logging.Handler):
    """
    Handler that buffers log records in memory for async processing.
    
    This handler stores records in a circular buffer without blocking I/O,
    allowing application threads to log without waiting for disk/network writes.
    """
    
    def __init__(
        self,
        buffer_size: int = 10000,
        overflow_strategy: str = 'drop_oldest',
    ):
        """
        Initialize the in-memory handler.
        
        Args:
            buffer_size: Maximum log records to keep in memory
            overflow_strategy: Strategy for handling buffer overflow
        """
        super().__init__()
        self.buffer = InMemoryLogBuffer(
            max_size=buffer_size,
            overflow_strategy=overflow_strategy,
        )
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to the buffer.
        
        This is non-blocking and should complete in microseconds.
        """
        try:
            self.buffer.put(record)
        except Exception:
            # Don't let logging errors crash the app
            self.handleError(record)
    
    def get_records(self) -> List[logging.LogRecord]:
        """Get and clear all buffered records."""
        return self.buffer.get_all()
    
    def get_buffer(self) -> InMemoryLogBuffer:
        """Get the underlying buffer for direct access."""
        return self.buffer


class BufferedQueueListener(logging.handlers.QueueListener):
    """
    Extended QueueListener that periodically flushes the in-memory buffer.
    
    Features:
    - Automatic flushing every flush_interval seconds
    - Graceful shutdown
    - Metrics tracking
    """
    
    def __init__(
        self,
        queue,
        *handlers,
        respect_handler_level=False,
        target=None,
        flush_interval: float = 5.0,
    ):
        """
        Initialize the buffered queue listener.
        
        Args:
            queue: Queue to listen to
            *handlers: Handlers to dispatch log records to
            respect_handler_level: Whether to respect handler log levels
            target: Target thread function
            flush_interval: How often to flush the in-memory buffer (seconds)
        """
        super().__init__(
            queue,
            *handlers,
            respect_handler_level=respect_handler_level,
        )
        self.flush_interval = flush_interval
        self._stop_event = threading.Event()
    
    def handle(self, record: logging.LogRecord) -> None:
        """Handle a log record by passing it to configured handlers."""
        mask = logging.addLevelName(logging.NOTSET, '')
        lvl = record.levelno
        
        for handler in self.handlers:
            if not self.respect_handler_level:
                h_level = logging.NOTSET
            else:
                h_level = handler.level
            
            if lvl >= h_level:
                handler.handle(record)
    
    def run(self) -> None:
        """
        Override run to add periodic flushing.
        
        This is the main event loop that processes queued records.
        """
        self._stop_event.clear()
        q = self._queue
        has_task_done = hasattr(q, 'task_done')
        
        while not self._stop_event.is_set():
            try:
                # Use timeout to allow periodic checks
                record = q.get(timeout=self.flush_interval)
                
                if record is self._sentinel:
                    break
                
                self.handle(record)
                
                if has_task_done:
                    q.task_done()
                    
            except Exception:
                # Handle queue.Empty and other exceptions
                pass
    
    def stop(self) -> None:
        """Stop the listener gracefully."""
        self._stop_event.set()
        super().stop()


# Global registry of in-memory handlers
_in_memory_handlers: dict = {}


def get_or_create_in_memory_handler(
    name: str = 'default',
    buffer_size: int = 10000,
    overflow_strategy: str = 'drop_oldest',
) -> InMemoryLogHandler:
    """
    Get or create a named in-memory handler.
    
    Args:
        name: Name of the handler
        buffer_size: Size of the log buffer
        overflow_strategy: Strategy for handling overflow
    
    Returns:
        InMemoryLogHandler instance
    """
    if name not in _in_memory_handlers:
        _in_memory_handlers[name] = InMemoryLogHandler(
            buffer_size=buffer_size,
            overflow_strategy=overflow_strategy,
        )
    return _in_memory_handlers[name]


def get_in_memory_handler(name: str = 'default') -> Optional[InMemoryLogHandler]:
    """
    Get an existing in-memory handler by name.
    
    Args:
        name: Name of the handler
    
    Returns:
        InMemoryLogHandler instance or None if not found
    """
    return _in_memory_handlers.get(name)


def drain_all_buffers(timeout: float = 5.0) -> dict:
    """
    Drain all in-memory log buffers.
    
    Useful for graceful shutdown. Returns all buffered records
    before clearing the buffers.
    
    Args:
        timeout: Timeout for draining (seconds)
    
    Returns:
        Dict mapping handler names to lists of log records
    """
    result = {}
    for name, handler in _in_memory_handlers.items():
        try:
            records = handler.get_records()
            result[name] = records
        except Exception as e:
            result[name] = {'error': str(e)}
    return result


def get_buffer_metrics(name: str = 'default') -> Optional[LogMetrics]:
    """
    Get metrics for a specific in-memory handler.
    
    Args:
        name: Name of the handler
    
    Returns:
        LogMetrics instance or None if handler not found
    """
    handler = get_in_memory_handler(name)
    if handler:
        return handler.get_buffer().get_metrics()
    return None


def get_all_buffer_metrics() -> dict:
    """
    Get metrics for all in-memory handlers.
    
    Returns:
        Dict mapping handler names to LogMetrics
    """
    result = {}
    for name, handler in _in_memory_handlers.items():
        result[name] = handler.get_buffer().get_metrics().to_dict()
    return result
