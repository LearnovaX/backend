"""
REST API views for logging metrics and management.

Provides endpoints to:
- Get buffer health metrics
- Drain buffers
- Query buffered logs
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from src.apps.logs.utils import (
    LoggingMetricsCollector,
    LoggingShutdownManager,
    get_buffered_logs_as_dicts,
)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def logging_metrics(request):
    """
    Get in-memory logging metrics.
    
    Returns:
        - total_records: Total number of logs processed
        - total_dropped: Number of logs dropped due to buffer overflow
        - avg_buffer_utilization: Average buffer utilization percentage
        - buffers: Per-buffer detailed metrics
    """
    try:
        metrics = LoggingMetricsCollector.get_buffer_health()
        return Response(
            {
                'status': 'success',
                'data': metrics,
            },
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {
                'status': 'error',
                'message': str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def buffered_logs(request):
    """
    Get buffered log records and optionally clear them.
    
    Query Parameters:
    - limit: Limit number of records returned (default: 100)
    - clear: Set to 'true' to clear buffers after retrieval
    
    Returns:
        Array of log record objects with timestamp, level, logger, message, etc.
    """
    try:
        limit = int(request.query_params.get('limit', 100))
        clear_buffer = request.query_params.get('clear', 'false').lower() == 'true'
        
        logs = get_buffered_logs_as_dicts()
        
        # Limit results
        logs = logs[-limit:] if limit > 0 else logs
        
        result = {
            'status': 'success',
            'count': len(logs),
            'data': logs,
        }
        
        if clear_buffer:
            # Drain buffers
            drain_result = LoggingShutdownManager.shutdown(timeout=5.0)
            result['drain_info'] = drain_result
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {
                'status': 'error',
                'message': str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def drain_logs(request):
    """
    Drain all log buffers and prepare for shutdown.
    
    Query Parameters:
    - timeout: Time to wait for drain (default: 10)
    
    Returns:
        Summary of drained buffers and final metrics
    """
    try:
        timeout = float(request.query_params.get('timeout', 10.0))
        
        result = LoggingShutdownManager.shutdown(timeout=timeout)
        
        return Response(
            {
                'status': 'success',
                'data': result,
            },
            status=status.HTTP_200_OK,
        )
        
    except Exception as e:
        return Response(
            {
                'status': 'error',
                'message': str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def health_check(request):
    """
    Quick health check for logging system.
    
    Returns:
        - status: 'healthy' or 'degraded'
        - buffer_health: Metrics for all buffers
        - warnings: Any issues detected
    """
    try:
        metrics = LoggingMetricsCollector.get_buffer_health()
        
        health_status = 'healthy'
        warnings = []
        
        # Check for warning conditions
        if metrics['total_dropped'] > 0:
            warnings.append(f"Dropped {metrics['total_dropped']} log records")
            health_status = 'degraded'
        
        if metrics['avg_buffer_utilization'] > 80:
            warnings.append(
                f"Buffer utilization high: {metrics['avg_buffer_utilization']}%"
            )
            health_status = 'degraded'
        
        return Response(
            {
                'status': health_status,
                'buffer_health': metrics,
                'warnings': warnings,
            },
            status=status.HTTP_200_OK,
        )
        
    except Exception as e:
        return Response(
            {
                'status': 'error',
                'message': str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
