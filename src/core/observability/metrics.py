"""Prometheus metrics helpers for Django."""

from __future__ import annotations

import logging
import time
from typing import Optional

from django.conf import settings
from django.http import HttpRequest, HttpResponse

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

    PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)

REQUEST_COUNT: Optional[Counter] = None
REQUEST_LATENCY: Optional[Histogram] = None


if PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter(
        "backend_http_requests_total",
        "Total HTTP requests",
        ["method", "route", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "backend_http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "route", "status"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
    )


def _resolve_route(request: HttpRequest) -> str:
    match = getattr(request, "resolver_match", None)
    if match is not None:
        return match.route or match.view_name or request.path
    return request.path


class PrometheusRequestMiddleware:
    """Collect basic request counts and latency for Prometheus."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = (
            PROMETHEUS_AVAILABLE and getattr(settings, "PROMETHEUS_ENABLED", True)
        )
        if not self.enabled:
            logger.debug("Prometheus middleware disabled")

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not self.enabled:
            return self.get_response(request)

        start_time = time.monotonic()
        response: Optional[HttpResponse] = None
        try:
            response = self.get_response(request)
            return response
        finally:
            duration = time.monotonic() - start_time
            status = response.status_code if response is not None else 500
            route = _resolve_route(request)
            method = request.method
            status_label = str(status)
            if REQUEST_COUNT is not None and REQUEST_LATENCY is not None:
                REQUEST_COUNT.labels(
                    method=method, route=route, status=status_label
                ).inc()
                REQUEST_LATENCY.labels(
                    method=method, route=route, status=status_label
                ).observe(duration)


def metrics_view(request: HttpRequest) -> HttpResponse:
    """Expose Prometheus metrics for scraping."""
    if not PROMETHEUS_AVAILABLE:
        return HttpResponse("prometheus_client not installed", status=501)
    if not getattr(settings, "PROMETHEUS_ENABLED", True):
        return HttpResponse("Prometheus disabled", status=403)
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)

