"""
Logs application configuration.

Initializes in-memory logging with queue listeners on startup.
"""

import logging

from django.apps import AppConfig


class LogsConfig(AppConfig):
    """Configuration for the logs application."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.apps.logs"
    
    def ready(self) -> None:
        """
        Initialize logging when Django is ready.
        
        Sets up the queue listener manager to drain in-memory log buffers
        asynchronously to configured handlers.
        """
        from django.conf import settings
        
        from .in_memory_logger import get_or_create_in_memory_handler
        from .queue_listener import setup_queue_listener
        from .signals import setup_logging_signals
        
        # Only setup if not already done
        if hasattr(self, '_logging_initialized'):
            return
        
        try:
            # Get the in-memory handler
            in_memory_handler = get_or_create_in_memory_handler(
                name='default',
                buffer_size=settings.IN_MEMORY_LOG_BUFFER_SIZE,
                overflow_strategy=settings.IN_MEMORY_LOG_OVERFLOW,
            )
            
            # Create target handlers for queue listener
            from .handlers import OptimizedDatabaseHandler
            
            db_handler = OptimizedDatabaseHandler(
                batch_size=settings.IN_MEMORY_LOG_BATCH_SIZE,
            )
            db_handler.setFormatter(
                logging.Formatter(
                    "[{asctime}] {levelname} {name}:{lineno} - {message}",
                    style="{",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            
            # Setup queue listener to drain the in-memory buffer
            # This runs in a background thread
            queue_handler = setup_queue_listener(
                name='default',
                in_memory_handler=in_memory_handler,
                target_handlers=[db_handler],
                queue_size=settings.IN_MEMORY_LOG_QUEUE_SIZE,
                flush_interval=settings.IN_MEMORY_LOG_FLUSH_INTERVAL,
            )
            
            # Add queue handler to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(queue_handler)
            
            # Setup signal handlers for graceful shutdown
            setup_logging_signals()
            
            self._logging_initialized = True
            
        except Exception as e:
            # Don't fail app startup if logging setup fails
            import sys
            print(f"Warning: Failed to setup in-memory logging: {e}", file=sys.stderr)


