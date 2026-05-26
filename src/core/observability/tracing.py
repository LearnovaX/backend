"""OpenTelemetry tracing setup."""

from __future__ import annotations

import logging
from typing import Optional

from django.conf import settings

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    OTEL_AVAILABLE = False

logger = logging.getLogger(__name__)
_initialized = False


def setup_tracing() -> None:
    """Configure OpenTelemetry tracing if enabled."""
    global _initialized
    if _initialized:
        return
    if not (OTEL_AVAILABLE and getattr(settings, "OTEL_ENABLED", False)):
        logger.debug("OpenTelemetry tracing disabled")
        return

    resource = Resource.create({SERVICE_NAME: settings.OTEL_SERVICE_NAME})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    DjangoInstrumentor().instrument()
    _initialized = True

