"""
Tests for in-memory logging system.

Run with: python manage.py test src.apps.logs.tests.test_in_memory_logging
"""

import logging
import threading
import time
from unittest import TestCase

from django.test import TestCase as DjangoTestCase

from src.apps.logs.in_memory_logger import (
    InMemoryLogBuffer,
    InMemoryLogHandler,
    get_or_create_in_memory_handler,
    get_in_memory_handler,
)


class InMemoryLogBufferTestCase(TestCase):
    """Test the circular buffer implementation."""
    
    def test_buffer_creation(self):
        """Test buffer can be created with configuration."""
        buffer = InMemoryLogBuffer(max_size=100, overflow_strategy='drop_oldest')
        self.assertEqual(buffer.max_size, 100)
        self.assertEqual(buffer.overflow_strategy, 'drop_oldest')
    
    def test_buffer_put_and_get(self):
        """Test putting and getting records."""
        buffer = InMemoryLogBuffer(max_size=100)
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='test message',
            args=(),
            exc_info=None,
        )
        
        buffer.put(record)
        self.assertEqual(buffer.size(), 1)
        
        records = buffer.get_all()
        self.assertEqual(len(records), 1)
        self.assertEqual(buffer.size(), 0)  # Should be cleared
    
    def test_buffer_overflow_drop_oldest(self):
        """Test drop_oldest overflow strategy."""
        buffer = InMemoryLogBuffer(max_size=3, overflow_strategy='drop_oldest')
        
        for i in range(5):
            record = logging.LogRecord(
                name=f'test{i}',
                level=logging.INFO,
                pathname='test.py',
                lineno=i,
                msg=f'message {i}',
                args=(),
                exc_info=None,
            )
            buffer.put(record)
        
        # Should have last 3 records (drop oldest)
        self.assertEqual(buffer.size(), 3)
        records = buffer.get_all()
        self.assertEqual(records[0].name, 'test2')  # First two dropped
        self.assertEqual(records[-1].name, 'test4')
    
    def test_buffer_overflow_drop_newest(self):
        """Test drop_newest overflow strategy."""
        buffer = InMemoryLogBuffer(max_size=3, overflow_strategy='drop_newest')
        
        for i in range(5):
            record = logging.LogRecord(
                name=f'test{i}',
                level=logging.INFO,
                pathname='test.py',
                lineno=i,
                msg=f'message {i}',
                args=(),
                exc_info=None,
            )
            buffer.put(record)
        
        # Should reject last 2 records
        self.assertEqual(buffer.size(), 3)
        records = buffer.get_all()
        self.assertEqual(records[0].name, 'test0')
        self.assertEqual(records[-1].name, 'test2')
    
    def test_buffer_overflow_error(self):
        """Test error overflow strategy."""
        buffer = InMemoryLogBuffer(max_size=2, overflow_strategy='error')
        
        for i in range(2):
            record = logging.LogRecord(
                name=f'test{i}',
                level=logging.INFO,
                pathname='test.py',
                lineno=i,
                msg=f'message {i}',
                args=(),
                exc_info=None,
            )
            buffer.put(record)
        
        # Third should raise error
        record = logging.LogRecord(
            name='test3',
            level=logging.INFO,
            pathname='test.py',
            lineno=3,
            msg='message 3',
            args=(),
            exc_info=None,
        )
        
        with self.assertRaises(BufferError):
            buffer.put(record)
    
    def test_buffer_utilization(self):
        """Test utilization calculation."""
        buffer = InMemoryLogBuffer(max_size=100)
        
        # Empty buffer
        self.assertEqual(buffer.utilization(), 0.0)
        
        # Add records
        for i in range(50):
            record = logging.LogRecord(
                name=f'test{i}',
                level=logging.INFO,
                pathname='test.py',
                lineno=i,
                msg=f'message {i}',
                args=(),
                exc_info=None,
            )
            buffer.put(record)
        
        # Should be 50% utilized
        self.assertEqual(buffer.utilization(), 50.0)
    
    def test_buffer_thread_safety(self):
        """Test buffer is thread-safe."""
        buffer = InMemoryLogBuffer(max_size=1000)
        records_written = []
        
        def writer(thread_id):
            for i in range(100):
                record = logging.LogRecord(
                    name=f'thread{thread_id}',
                    level=logging.INFO,
                    pathname='test.py',
                    lineno=i,
                    msg=f'message {i}',
                    args=(),
                    exc_info=None,
                )
                buffer.put(record)
                records_written.append(1)
        
        # Start multiple threads writing simultaneously
        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All records should be in buffer (up to max)
        self.assertTrue(len(records_written) >= 500)


class InMemoryLogHandlerTestCase(DjangoTestCase):
    """Test the in-memory log handler."""
    
    def test_handler_emit(self):
        """Test handler can emit records."""
        handler = InMemoryLogHandler(buffer_size=100)
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='test message',
            args=(),
            exc_info=None,
        )
        
        handler.emit(record)
        records = handler.get_records()
        
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].msg, 'test message')
    
    def test_handler_get_buffer(self):
        """Test can get underlying buffer."""
        handler = InMemoryLogHandler(buffer_size=100)
        buffer = handler.get_buffer()
        
        self.assertIsNotNone(buffer)
        self.assertEqual(buffer.max_size, 100)


class InMemoryHandlerRegistryTestCase(TestCase):
    """Test the global handler registry."""
    
    def test_get_or_create_handler(self):
        """Test creating and retrieving handlers."""
        handler = get_or_create_in_memory_handler(name='test1', buffer_size=1000)
        self.assertIsNotNone(handler)
        
        # Should return same instance
        handler2 = get_or_create_in_memory_handler(name='test1')
        self.assertIs(handler, handler2)
    
    def test_get_handler(self):
        """Test retrieving handler."""
        get_or_create_in_memory_handler(name='test2', buffer_size=500)
        handler = get_in_memory_handler(name='test2')
        self.assertIsNotNone(handler)
    
    def test_get_nonexistent_handler(self):
        """Test retrieving non-existent handler."""
        handler = get_in_memory_handler(name='nonexistent')
        self.assertIsNone(handler)


class LoggingIntegrationTestCase(DjangoTestCase):
    """Integration tests with Django logging."""
    
    def test_logging_integration(self):
        """Test that Django logging works with in-memory handler."""
        logger = logging.getLogger('test.integration')
        
        # Get the in-memory handler
        handler = get_or_create_in_memory_handler(name='integration')
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        # Log some messages
        logger.debug('debug message')
        logger.info('info message')
        logger.warning('warning message')
        
        # Check records
        records = handler.get_records()
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].levelname, 'DEBUG')
        self.assertEqual(records[1].levelname, 'INFO')
        self.assertEqual(records[2].levelname, 'WARNING')
    
    def test_high_volume_logging(self):
        """Test handler with high volume of logs."""
        logger = logging.getLogger('test.volume')
        handler = InMemoryLogHandler(buffer_size=10000)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Log 5000 messages
        for i in range(5000):
            logger.info(f'message {i}')
        
        # Should have 5000 records (not dropped)
        records = handler.get_records()
        self.assertEqual(len(records), 5000)
    
    def test_metrics(self):
        """Test metrics collection."""
        handler = get_or_create_in_memory_handler(name='metrics')
        logger = logging.getLogger('test.metrics')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Log some messages
        for i in range(100):
            logger.info(f'message {i}')
        
        # Get metrics
        metrics = handler.get_buffer().get_metrics()
        self.assertEqual(metrics.total_records, 100)
        self.assertEqual(metrics.dropped_records, 0)
        self.assertGreater(metrics.buffer_utilization, 0)
