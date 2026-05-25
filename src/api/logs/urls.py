"""
URL configuration for logs API endpoints.
"""

from django.urls import path

from . import views

app_name = 'logs'

urlpatterns = [
    # Logging metrics and monitoring
    path('metrics/', views.logging_metrics, name='metrics'),
    path('buffered-logs/', views.buffered_logs, name='buffered_logs'),
    path('drain/', views.drain_logs, name='drain'),
    path('health/', views.health_check, name='health'),
]
