"""
Django management command to monitor and manage in-memory logging.

Usage:
    python manage.py logging_monitor stats      - Show logging statistics
    python manage.py logging_monitor drain      - Drain all buffers
    python manage.py logging_monitor watch      - Watch buffer metrics in real-time
"""

import json
import time

from django.core.management.base import BaseCommand, CommandError

from src.apps.logs.utils import (
    LoggingMetricsCollector,
    LoggingShutdownManager,
    get_buffered_logs_as_dicts,
)


class Command(BaseCommand):
    """Management command for logging monitoring and management."""
    
    help = "Monitor and manage in-memory logging"
    
    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            'action',
            type=str,
            choices=['stats', 'drain', 'watch'],
            help='Action to perform: stats (show metrics), drain (drain buffers), watch (real-time)',
        )
        parser.add_argument(
            '--interval',
            type=float,
            default=2.0,
            help='Interval for watch mode (seconds)',
        )
        parser.add_argument(
            '--duration',
            type=float,
            default=60.0,
            help='How long to watch (seconds)',
        )
    
    def handle(self, *args, **options):
        """Handle the command."""
        action = options['action']
        
        if action == 'stats':
            self.show_stats()
        elif action == 'drain':
            self.drain_buffers()
        elif action == 'watch':
            self.watch_metrics(
                interval=options['interval'],
                duration=options['duration'],
            )
    
    def show_stats(self):
        """Show current logging statistics."""
        metrics = LoggingMetricsCollector.get_buffer_health()
        
        self.stdout.write(self.style.SUCCESS('\n=== Logging Statistics ===\n'))
        self.stdout.write(f"Total Records: {metrics['total_records']}")
        self.stdout.write(f"Total Dropped: {metrics['total_dropped']}")
        self.stdout.write(f"Avg Buffer Utilization: {metrics['avg_buffer_utilization']}%")
        
        self.stdout.write(self.style.SUCCESS('\n--- Per-Buffer Metrics ---\n'))
        for name, buffer_metrics in metrics['buffers'].items():
            self.stdout.write(self.style.WARNING(f"Buffer: {name}"))
            self.stdout.write(json.dumps(buffer_metrics, indent=2))
            self.stdout.write('')
        
        logs = get_buffered_logs_as_dicts()
        if logs:
            self.stdout.write(self.style.SUCCESS(f'\n--- Buffered Logs ({len(logs)} records) ---\n'))
            for i, log in logs[-10:]:  # Show last 10
                self.stdout.write(f"[{log['level']}] {log['logger']}: {log['message']}")
    
    def drain_buffers(self):
        """Drain all log buffers."""
        self.stdout.write(self.style.WARNING('Draining all log buffers...'))
        
        result = LoggingShutdownManager.shutdown(timeout=10.0)
        
        self.stdout.write(self.style.SUCCESS(f"\nStatus: {result['status']}"))
        self.stdout.write(f"Drained buffers: {result['drained_buffers']}")
        
        if result['status'] == 'shutdown_error':
            self.stdout.write(self.style.ERROR(f"Error: {result.get('error')}"))
    
    def watch_metrics(self, interval: float = 2.0, duration: float = 60.0):
        """Watch metrics in real-time."""
        self.stdout.write(self.style.SUCCESS(
            f'Watching metrics every {interval}s for {duration}s...\n'
        ))
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            metrics = LoggingMetricsCollector.get_buffer_health()
            
            # Clear screen and print
            self.stdout.write('\033[2J\033[H')  # Clear screen
            self.stdout.write(self.style.SUCCESS(
                f'=== Logging Metrics (Updated every {interval}s) ===\n'
            ))
            self.stdout.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.stdout.write(f"Total Records: {metrics['total_records']}")
            self.stdout.write(f"Total Dropped: {metrics['total_dropped']}")
            self.stdout.write(f"Avg Buffer Utilization: {metrics['avg_buffer_utilization']}%")
            
            self.stdout.write(self.style.SUCCESS('\n--- Per-Buffer Metrics ---'))
            for name, buffer_metrics in metrics['buffers'].items():
                self.stdout.write(
                    f"{name}: {buffer_metrics['total_records']} records, "
                    f"{buffer_metrics['dropped_records']} dropped, "
                    f"{buffer_metrics['buffer_utilization']}% utilization"
                )
            
            time.sleep(interval)
