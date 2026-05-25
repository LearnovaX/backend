# In-Memory Logging with Queue Handlers

High-performance, scalable logging system designed for production applications that need to handle high-volume log production without suffering I/O bottlenecks.

## Architecture Overview

### Components

1. **InMemoryLogHandler**: Buffers log records in a circular buffer (non-blocking)
2. **InMemoryLogBuffer**: Thread-safe circular buffer with configurable overflow strategies
3. **BufferedQueueListener**: Processes buffered records asynchronously
4. **QueueListenerManager**: Manages lifecycle of queue listeners
5. **OptimizedDatabaseHandler**: Batches database writes for efficiency

### Flow

```
Application Thread                Background Thread
    |                                    |
    v                                    |
  log()                                  |
    |                                    |
    v                                    |
InMemoryLogHandler                       |
  (Non-blocking buffer put)              |
    |                                    |
    +--- LogRecord                       |
    |    (appended to circular           |
    |     buffer instantly)              |
    |                                    |
    v                                    v
                              BufferedQueueListener
                                    |
                                    v
                          Queue.get() (with timeout)
                                    |
                                    v
                          OptimizedDatabaseHandler
                                    |
                                    v (batch)
                              Database.bulk_create()
```

## Performance Benefits

- **Non-blocking Application Threads**: Log writes complete in microseconds
- **Asynchronous Processing**: Database writes happen in background thread
- **Batched Writes**: Reduces database round trips
- **Circular Buffer**: Automatic overflow handling without memory leaks
- **Low Latency**: No I/O wait on application critical path

## Configuration

### Environment Variables

```bash
# Buffer size (number of log records to hold in memory)
IN_MEMORY_LOG_BUFFER_SIZE=10000

# Overflow strategy: drop_oldest, drop_newest, or error
IN_MEMORY_LOG_OVERFLOW=drop_oldest

# Queue size for processing logs
IN_MEMORY_LOG_QUEUE_SIZE=5000

# How often to flush logs (seconds)
IN_MEMORY_LOG_FLUSH_INTERVAL=5.0

# Batch size for database writes
IN_MEMORY_LOG_BATCH_SIZE=100
```

### Settings (Django)

All configuration is in `src/core/settings/base.py`:

```python
# In-memory logging configuration
IN_MEMORY_LOG_BUFFER_SIZE = 10000           # Tuned for your scale
IN_MEMORY_LOG_OVERFLOW = 'drop_oldest'      # Prefer oldest logs dropped
IN_MEMORY_LOG_QUEUE_SIZE = 5000             # Should be < buffer size
IN_MEMORY_LOG_FLUSH_INTERVAL = 5.0          # Balance latency vs throughput
IN_MEMORY_LOG_BATCH_SIZE = 100              # Tune based on DB performance
```

## Tuning for Different Scales

### Development (Low Volume)

```python
IN_MEMORY_LOG_BUFFER_SIZE = 1000
IN_MEMORY_LOG_QUEUE_SIZE = 500
IN_MEMORY_LOG_FLUSH_INTERVAL = 10.0
IN_MEMORY_LOG_BATCH_SIZE = 50
```

### Production (Medium Volume)

```python
IN_MEMORY_LOG_BUFFER_SIZE = 10000
IN_MEMORY_LOG_QUEUE_SIZE = 5000
IN_MEMORY_LOG_FLUSH_INTERVAL = 5.0
IN_MEMORY_LOG_BATCH_SIZE = 100
```

### High Scale (High Volume)

```python
IN_MEMORY_LOG_BUFFER_SIZE = 50000
IN_MEMORY_LOG_QUEUE_SIZE = 20000
IN_MEMORY_LOG_FLUSH_INTERVAL = 2.0
IN_MEMORY_LOG_BATCH_SIZE = 500
```

### Ultra High Scale (Very High Volume, Multi-Instance)

```python
IN_MEMORY_LOG_BUFFER_SIZE = 100000
IN_MEMORY_LOG_QUEUE_SIZE = 50000
IN_MEMORY_LOG_FLUSH_INTERVAL = 1.0
IN_MEMORY_LOG_BATCH_SIZE = 1000
```

## Usage

### Basic Usage (Automatic)

The system initializes automatically when Django starts. No code changes needed:

```python
import logging

logger = logging.getLogger(__name__)
logger.info("This is buffered in memory")  # Returns instantly
```

### Getting Buffer Metrics

```python
from src.apps.logs.utils import LoggingMetricsCollector

# Get all metrics
metrics = LoggingMetricsCollector.get_buffer_health()

# Metrics include:
# - total_records: Total logs processed
# - total_dropped: Logs dropped due to overflow
# - avg_buffer_utilization: % of buffer used
# - buffers: Per-buffer detailed metrics
```

### Draining Buffers

```python
from src.apps.logs.utils import LoggingShutdownManager

# Drain all buffers before shutdown
summary = LoggingShutdownManager.shutdown(timeout=10.0)
```

### Getting Buffered Logs

```python
from src.apps.logs.utils import get_buffered_logs_as_dicts

# Get all buffered logs as dictionaries
logs = get_buffered_logs_as_dicts()

# Each log contains:
# - timestamp: When the log was created
# - level: Log level (INFO, ERROR, etc)
# - logger: Logger name
# - message: Log message
# - module: Module where log was created
# - function: Function name
# - line: Line number
```

### Changing Log Levels at Runtime

```python
from src.apps.logs.utils import set_log_level

# Change log level without restart
set_log_level('django.db.backends', 'DEBUG')
```

## Monitoring

### Management Command

```bash
# Show current metrics
python manage.py logging_monitor stats

# Drain all buffers
python manage.py logging_monitor drain

# Watch metrics in real-time
python manage.py logging_monitor watch --interval 2.0 --duration 60.0
```

### REST API Endpoints (Admin Only)

All endpoints require admin authentication.

#### Get Metrics
```
GET /api/logs/metrics/
```

Response:
```json
{
  "status": "success",
  "data": {
    "total_records": 5234,
    "total_dropped": 0,
    "avg_buffer_utilization": 42.34,
    "buffers": {
      "default": {
        "total_records": 5234,
        "dropped_records": 0,
        "buffer_utilization": 42.34,
        "last_flush_time": "2026-05-26T12:34:56.789012"
      }
    }
  }
}
```

#### Get Buffered Logs
```
GET /api/logs/buffered-logs/?limit=100&clear=false
```

#### Drain Logs
```
POST /api/logs/drain/?timeout=10
```

#### Health Check
```
GET /api/logs/health/
```

Response:
```json
{
  "status": "healthy",
  "buffer_health": { ... },
  "warnings": []
}
```

## Overflow Strategies

The circular buffer can handle overflow with three strategies:

### 1. drop_oldest (Default)
Automatically removes the oldest log record when buffer is full. Good for capturing recent activity.

```python
IN_MEMORY_LOG_OVERFLOW = 'drop_oldest'
```

### 2. drop_newest
Rejects new log records when buffer is full. Preserves older logs, useful if you want to keep historical context.

```python
IN_MEMORY_LOG_OVERFLOW = 'drop_newest'
```

### 3. error
Raises an exception when buffer overflows. Good for development to catch buffer sizing issues.

```python
IN_MEMORY_LOG_OVERFLOW = 'error'
```

## Performance Considerations

### Buffer Size vs Memory Usage

- Each log record: ~1-2 KB
- 10,000 records: ~10-20 MB
- 50,000 records: ~50-100 MB
- 100,000 records: ~100-200 MB

### Queue Size

Should be slightly smaller than buffer size to allow room for incoming records while listener is busy.

**Formula**: `QUEUE_SIZE = BUFFER_SIZE * 0.5 to 0.7`

### Flush Interval

Lower values = lower latency but more database load
Higher values = better throughput but higher latency

- Development: 10-30 seconds
- Production: 3-5 seconds  
- High-scale: 1-2 seconds

### Batch Size

Larger batches = fewer database round trips but higher memory usage per write

**Database Performance Impact**:
- batch_size 50: ~5ms per 50 records
- batch_size 100: ~8ms per 100 records
- batch_size 500: ~30ms per 500 records

## Best Practices

1. **Set buffer size based on peak volume**: Peak logs/sec * 10 seconds of data
2. **Monitor buffer utilization**: Should stay below 80%
3. **Use environment variables**: Make tuning easy without code changes
4. **Enable metrics collection**: Monitor via `/api/logs/health/`
5. **Drain on shutdown**: Ensure all logs are flushed before restart
6. **Test under load**: Run load tests to find optimal settings
7. **Alert on dropped records**: Set up monitoring for non-zero dropped_records

## Troubleshooting

### Dropped Records

**Symptom**: `total_dropped > 0` in metrics

**Causes**:
- Buffer size too small for log volume
- Queue listener falling behind
- Database writes taking too long

**Solutions**:
1. Increase `IN_MEMORY_LOG_BUFFER_SIZE`
2. Increase `IN_MEMORY_LOG_BATCH_SIZE` (optimize DB writes)
3. Check database performance
4. Lower `IN_MEMORY_LOG_FLUSH_INTERVAL` to process faster

### High Buffer Utilization

**Symptom**: `avg_buffer_utilization > 80%`

**Solutions**:
1. Increase `IN_MEMORY_LOG_BUFFER_SIZE`
2. Lower `IN_MEMORY_LOG_FLUSH_INTERVAL` to drain faster
3. Reduce log volume by adjusting logger levels

### Memory Usage Too High

**Symptom**: Application using too much RAM

**Solutions**:
1. Reduce `IN_MEMORY_LOG_BUFFER_SIZE`
2. Lower `IN_MEMORY_LOG_FLUSH_INTERVAL`
3. Use smaller `IN_MEMORY_LOG_BATCH_SIZE`

### Logs Not Appearing

**Symptom**: Logs not showing up in database

**Causes**:
- Logs not yet flushed (normal, wait for flush interval)
- Queue listener crashed
- Database connection issues

**Debug**:
1. Check `/api/logs/health/` endpoint
2. Run `python manage.py logging_monitor stats`
3. Check Django logs for errors

## Integration with Existing Loggers

The system automatically integrates with Django's logging configuration. Your existing loggers will be buffered in memory:

```python
# Your existing code continues to work unchanged
import logging

logger = logging.getLogger(__name__)
logger.info("User logged in")  # Now buffered in memory
```

### Custom Integration

To integrate custom handlers with the queue system:

```python
from src.apps.logs.queue_listener import setup_queue_listener
from src.apps.logs.in_memory_logger import get_or_create_in_memory_handler
import logging

# Get or create in-memory handler
in_memory = get_or_create_in_memory_handler(name='custom')

# Create your custom handler
custom_handler = logging.StreamHandler()

# Setup queue listener
queue_handler = setup_queue_listener(
    name='custom',
    in_memory_handler=in_memory,
    target_handlers=[custom_handler],
)

# Add to logger
logger = logging.getLogger('my.module')
logger.addHandler(queue_handler)
```

## Graceful Shutdown

Ensure logs are flushed on shutdown:

```python
# In your Django shutdown/signal handler
from src.apps.logs.utils import LoggingShutdownManager

def django_shutdown(sender, **kwargs):
    summary = LoggingShutdownManager.shutdown(timeout=10.0)
    print(f"Logs shutdown: {summary}")

from django.core.signals import request_finished
request_finished.connect(django_shutdown)
```

## Advanced: Custom Overflow Handlers

Create custom overflow behavior:

```python
from src.apps.logs.in_memory_logger import InMemoryLogBuffer

class CustomBuffer(InMemoryLogBuffer):
    def put(self, record):
        # Custom logic before putting
        super().put(record)
        
        # Custom logic after putting
        if self.utilization() > 90:
            self.alert_high_utilization()
```

## Monitoring Dashboard (Future)

Consider adding a Grafana dashboard with metrics:

```yaml
- Logs buffered per second
- Buffer utilization percentage
- Dropped records count
- Queue processing latency
- Database write batch performance
```

This integrates with Prometheus metrics:

```python
from prometheus_client import Counter, Gauge

logs_buffered = Counter('logs_buffered_total', 'Total logs buffered')
buffer_utilization = Gauge('logs_buffer_utilization_percent', 'Buffer utilization')
logs_dropped = Counter('logs_dropped_total', 'Total logs dropped')
```
