"""
Performance benchmarking script for in-memory logging.

Compares performance of in-memory logging vs direct database writes.

Run with: python manage.py shell < benchmark_logging.py
"""

import logging
import time
from datetime import datetime

from src.apps.logs.in_memory_logger import InMemoryLogHandler
from src.apps.logs.handlers import DatabaseHandler, OptimizedDatabaseHandler


def benchmark_in_memory_handler(num_records=10000, buffer_size=20000):
    """Benchmark in-memory handler performance."""
    print("\n" + "="*60)
    print("BENCHMARKING: In-Memory Handler")
    print("="*60)
    print(f"Logging {num_records:,} records...")
    
    handler = InMemoryLogHandler(buffer_size=buffer_size)
    logger = logging.getLogger('benchmark.in_memory')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # Warm up
    logger.info("Warmup")
    
    # Benchmark
    start = time.perf_counter()
    
    for i in range(num_records):
        logger.info(f"Message {i}: This is a test log message")
    
    elapsed = time.perf_counter() - start
    
    # Results
    throughput = num_records / elapsed
    latency_us = (elapsed / num_records) * 1_000_000
    
    metrics = handler.get_buffer().get_metrics()
    
    print(f"\nResults:")
    print(f"  Total time: {elapsed:.3f}s")
    print(f"  Throughput: {throughput:,.0f} logs/sec")
    print(f"  Latency: {latency_us:.2f} μs per log")
    print(f"  Buffer utilization: {metrics.buffer_utilization:.2f}%")
    print(f"  Records dropped: {metrics.dropped_records}")
    
    return {
        'elapsed': elapsed,
        'throughput': throughput,
        'latency_us': latency_us,
    }


def benchmark_direct_database_handler(num_records=100):
    """Benchmark direct database handler (slow - only test small sample)."""
    print("\n" + "="*60)
    print("BENCHMARKING: Direct Database Handler (Sample)")
    print("="*60)
    print(f"Logging {num_records} records (small sample, DB writes are slow)...")
    
    handler = DatabaseHandler()
    logger = logging.getLogger('benchmark.database')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # Warm up
    logger.info("Warmup")
    
    # Benchmark
    start = time.perf_counter()
    
    for i in range(num_records):
        logger.info(f"Message {i}: This is a test log message")
    
    elapsed = time.perf_counter() - start
    
    # Results
    throughput = num_records / elapsed
    latency_ms = (elapsed / num_records) * 1000
    
    print(f"\nResults:")
    print(f"  Total time: {elapsed:.3f}s")
    print(f"  Throughput: {throughput:,.0f} logs/sec")
    print(f"  Latency: {latency_ms:.2f} ms per log")
    
    return {
        'elapsed': elapsed,
        'throughput': throughput,
        'latency_ms': latency_ms,
    }


def benchmark_optimized_database_handler(num_records=10000, batch_size=100):
    """Benchmark optimized database handler with batching."""
    print("\n" + "="*60)
    print("BENCHMARKING: Optimized Database Handler (Batched)")
    print("="*60)
    print(f"Logging {num_records:,} records with batch size {batch_size}...")
    
    handler = OptimizedDatabaseHandler(batch_size=batch_size)
    logger = logging.getLogger('benchmark.optimized_db')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # Set queue mode
    handler.set_queue_mode(True)
    
    # Warm up
    logger.info("Warmup")
    
    # Benchmark
    start = time.perf_counter()
    
    for i in range(num_records):
        logger.info(f"Message {i}: This is a test log message")
    
    # Flush any remaining records
    handler._flush_batch()
    
    elapsed = time.perf_counter() - start
    
    # Results
    throughput = num_records / elapsed
    latency_us = (elapsed / num_records) * 1_000_000
    
    print(f"\nResults:")
    print(f"  Total time: {elapsed:.3f}s")
    print(f"  Throughput: {throughput:,.0f} logs/sec")
    print(f"  Latency: {latency_us:.2f} μs per log")
    print(f"  Batch size: {batch_size}")
    
    return {
        'elapsed': elapsed,
        'throughput': throughput,
        'latency_us': latency_us,
    }


def benchmark_buffer_sizes(num_records=10000):
    """Benchmark different buffer sizes."""
    print("\n" + "="*60)
    print("BENCHMARKING: Different Buffer Sizes")
    print("="*60)
    
    buffer_sizes = [1000, 5000, 10000, 50000, 100000]
    results = {}
    
    for size in buffer_sizes:
        handler = InMemoryLogHandler(buffer_size=size)
        logger = logging.getLogger(f'benchmark.buffer.{size}')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        start = time.perf_counter()
        for i in range(num_records):
            logger.info(f"Message {i}")
        elapsed = time.perf_counter() - start
        
        throughput = num_records / elapsed
        results[size] = throughput
        
        print(f"  Buffer size {size:>6}: {throughput:>10,.0f} logs/sec")
    
    return results


def benchmark_overflow_strategies(num_records=5000):
    """Benchmark different overflow strategies."""
    print("\n" + "="*60)
    print("BENCHMARKING: Overflow Strategies")
    print("="*60)
    
    # Fill buffer beyond capacity
    buffer_size = 1000
    test_records = num_records  # More than buffer
    
    strategies = ['drop_oldest', 'drop_newest']
    
    for strategy in strategies:
        handler = InMemoryLogHandler(
            buffer_size=buffer_size,
            overflow_strategy=strategy,
        )
        logger = logging.getLogger(f'benchmark.overflow.{strategy}')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        start = time.perf_counter()
        for i in range(test_records):
            logger.info(f"Message {i}")
        elapsed = time.perf_counter() - start
        
        metrics = handler.get_buffer().get_metrics()
        throughput = test_records / elapsed
        
        print(f"\n  Strategy: {strategy}")
        print(f"    Throughput: {throughput:,.0f} logs/sec")
        print(f"    Dropped: {metrics.dropped_records:,}")
        print(f"    Final buffer size: {handler.get_buffer().size()}")


def show_comparison(in_memory_result, db_sample_result):
    """Show comparison between in-memory and direct database."""
    print("\n" + "="*60)
    print("PERFORMANCE COMPARISON")
    print("="*60)
    
    # Extrapolate DB performance to full scale
    full_scale_db_latency = db_sample_result['latency_ms'] * 1000  # Convert to μs
    
    speedup_latency = full_scale_db_latency / in_memory_result['latency_us']
    speedup_throughput = (in_memory_result['throughput'] / db_sample_result['throughput'])
    
    print(f"\nLatency:")
    print(f"  In-Memory:        {in_memory_result['latency_us']:.2f} μs per log")
    print(f"  Direct Database:  {full_scale_db_latency:.2f} μs per log (extrapolated)")
    print(f"  Speedup:          {speedup_latency:.0f}x faster")
    
    print(f"\nThroughput:")
    print(f"  In-Memory:        {in_memory_result['throughput']:,.0f} logs/sec")
    print(f"  Direct Database:  {db_sample_result['throughput']:,.0f} logs/sec")
    print(f"  Improvement:      {speedup_throughput:.0f}x higher")
    
    print(f"\nConclusion:")
    print(f"  In-memory logging is {speedup_latency:.0f}x faster for application threads")
    print(f"  allowing {speedup_throughput:.0f}x higher throughput")
    print(f"  Background thread handles database I/O asynchronously")


def run_full_benchmark():
    """Run complete benchmark suite."""
    print("\n" + "="*70)
    print("IN-MEMORY LOGGING PERFORMANCE BENCHMARK")
    print("="*70)
    print(f"Started at: {datetime.now()}")
    
    # Benchmark in-memory handler
    in_memory_result = benchmark_in_memory_handler(num_records=10000)
    
    # Benchmark direct database (small sample)
    db_sample_result = benchmark_direct_database_handler(num_records=50)
    
    # Show comparison
    show_comparison(in_memory_result, db_sample_result)
    
    # Benchmark different configurations
    print("\n")
    benchmark_buffer_sizes(num_records=10000)
    
    print("\n")
    benchmark_overflow_strategies(num_records=5000)
    
    # Final summary
    print("\n" + "="*70)
    print("BENCHMARK COMPLETE")
    print("="*70)
    print(f"Completed at: {datetime.now()}")
    print("\nRecommendations:")
    print("  1. Use in-memory logging for all high-volume scenarios")
    print("  2. Configure buffer size based on peak log volume")
    print("  3. Use 'drop_oldest' for recent activity capture")
    print("  4. Monitor buffer utilization via /api/logs/health/")
    print("  5. Set alert for buffer utilization > 80%")


if __name__ == '__main__':
    run_full_benchmark()
