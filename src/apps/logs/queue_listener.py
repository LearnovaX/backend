"""
Queue listener management for in-memory logging system.

Handles setup, lifecycle, and shutdown of queue listeners that drain
in-memory buffers asynchronously.
"""

import logging
import logging.handlers
import queue
import threading
from typing import List, Optional

from .in_memory_logger import BufferedQueueListener, InMemoryLogHandler


class QueueListenerManager:
    """
    Manages the lifecycle of queue listeners for async log processing.
    
    This ensures that logs buffered in memory are processed by actual
    handlers (database, file, etc.) without blocking application threads.
    """
    
    def __init__(self, flush_interval: float = 5.0):
        """
        Initialize the queue listener manager.
        
        Args:
            flush_interval: How often to flush buffers in seconds
        """
        self.flush_interval = flush_interval
        self.listeners: dict[str, BufferedQueueListener] = {}
        self.queues: dict[str, queue.Queue] = {}
        self.lock = threading.Lock()
        self._running = False
    
    def create_queue_handler(
        self,
        name: str,
        in_memory_handler: InMemoryLogHandler,
        target_handlers: List[logging.Handler],
        queue_size: int = 10000,
    ) -> logging.handlers.QueueHandler:
        """
        Create a queue handler that drains the in-memory buffer asynchronously.
        
        Args:
            name: Name for this queue handler
            in_memory_handler: The InMemoryLogHandler to drain
            target_handlers: Handlers to process the drained records
            queue_size: Maximum size of the internal queue
        
        Returns:
            QueueHandler configured for the in-memory buffer
        """
        with self.lock:
            if name in self.listeners:
                raise ValueError(f"Queue listener '{name}' already exists")
            
            # Create queue and queue handler
            log_queue = queue.Queue(maxsize=queue_size)
            self.queues[name] = log_queue
            
            queue_handler = logging.handlers.QueueHandler(log_queue)
            
            # Create and start the listener
            listener = BufferedQueueListener(
                log_queue,
                *target_handlers,
                flush_interval=self.flush_interval,
            )
            
            self.listeners[name] = listener
            
            return queue_handler
    
    def start_all(self) -> None:
        """Start all queue listeners."""
        with self.lock:
            for name, listener in self.listeners.items():
                if not listener._thread or not listener._thread.is_alive():
                    listener.start()
            self._running = True
    
    def stop_all(self, timeout: float = 10.0) -> None:
        """
        Stop all queue listeners gracefully.
        
        Args:
            timeout: Maximum time to wait for listeners to stop
        """
        with self.lock:
            for name, listener in self.listeners.items():
                try:
                    listener.stop()
                except Exception:
                    pass
            
            self._running = False
    
    def get_listener(self, name: str) -> Optional[BufferedQueueListener]:
        """Get a queue listener by name."""
        return self.listeners.get(name)
    
    def is_running(self) -> bool:
        """Check if listeners are running."""
        return self._running


# Global manager instance
_queue_listener_manager: Optional[QueueListenerManager] = None


def get_queue_listener_manager(
    flush_interval: float = 5.0,
) -> QueueListenerManager:
    """
    Get or create the global queue listener manager.
    
    Args:
        flush_interval: Flush interval for the manager
    
    Returns:
        QueueListenerManager instance
    """
    global _queue_listener_manager
    
    if _queue_listener_manager is None:
        _queue_listener_manager = QueueListenerManager(flush_interval=flush_interval)
    
    return _queue_listener_manager


def setup_queue_listener(
    name: str,
    in_memory_handler: InMemoryLogHandler,
    target_handlers: List[logging.Handler],
    queue_size: int = 10000,
    flush_interval: float = 5.0,
) -> logging.handlers.QueueHandler:
    """
    Setup a queue listener for an in-memory handler.
    
    This is a convenience function that combines manager creation and setup.
    
    Args:
        name: Name for this queue handler
        in_memory_handler: The InMemoryLogHandler to drain
        target_handlers: Handlers to process the drained records
        queue_size: Maximum size of the internal queue
        flush_interval: How often to flush buffers
    
    Returns:
        QueueHandler configured for async processing
    """
    manager = get_queue_listener_manager(flush_interval=flush_interval)
    
    queue_handler = manager.create_queue_handler(
        name=name,
        in_memory_handler=in_memory_handler,
        target_handlers=target_handlers,
        queue_size=queue_size,
    )
    
    # Start listeners if not already running
    if not manager.is_running():
        manager.start_all()
    
    return queue_handler


def shutdown_queue_listeners(timeout: float = 10.0) -> None:
    """
    Shutdown all queue listeners gracefully.
    
    Args:
        timeout: Maximum time to wait for shutdown
    """
    global _queue_listener_manager
    
    if _queue_listener_manager:
        _queue_listener_manager.stop_all(timeout=timeout)
        _queue_listener_manager = None
