"""
OpenTelemetry tracing for distributed observability.

This module provides optional OpenTelemetry instrumentation for tracing
requests across the application and external services.
"""

import os
import logging
from typing import Optional, Any, Dict
from contextlib import contextmanager

logger = logging.getLogger("TRACING")

# Check if OpenTelemetry is enabled
OTEL_ENABLED = os.getenv('OTEL_ENABLED', 'false').lower() == 'true'

# OpenTelemetry components (lazily imported)
_tracer = None
_trace = None
_SpanKind = None
_StatusCode = None
OTEL_AVAILABLE = False

if OTEL_ENABLED:
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.trace import SpanKind, StatusCode
        from opentelemetry.propagate import set_global_textmap
        from opentelemetry.propagators.b3 import B3MultiFormat

        _trace = trace
        _SpanKind = SpanKind
        _StatusCode = StatusCode
        OTEL_AVAILABLE = True
        logger.info("OpenTelemetry modules loaded successfully")
    except ImportError as e:
        logger.warning("OpenTelemetry not installed: %s", str(e))
        OTEL_AVAILABLE = False


def init_tracing(
    service_name: str = "plex-autoscan",
    service_version: str = "unknown"
) -> None:
    """
    Initialize OpenTelemetry tracing.

    Args:
        service_name: Name of the service for tracing
        service_version: Version of the service
    """
    global _tracer

    if not OTEL_AVAILABLE:
        logger.info("OpenTelemetry tracing disabled (OTEL_ENABLED=false or not installed)")
        return

    try:
        # Create resource with service information
        resource = Resource.create({
            SERVICE_NAME: service_name,
            "service.version": service_version,
            "deployment.environment": os.getenv('ENVIRONMENT', 'production')
        })

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Configure exporter based on environment
        exporter_type = os.getenv('OTEL_EXPORTER_TYPE', 'console')

        if exporter_type == 'otlp':
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                otlp_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'localhost:4317')
                exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info("OTLP exporter configured: %s", otlp_endpoint)
            except ImportError:
                logger.warning("OTLP exporter not available, falling back to console")
                exporter_type = 'console'

        if exporter_type == 'jaeger':
            try:
                from opentelemetry.exporter.jaeger.thrift import JaegerExporter
                jaeger_host = os.getenv('JAEGER_AGENT_HOST', 'localhost')
                jaeger_port = int(os.getenv('JAEGER_AGENT_PORT', '6831'))
                exporter = JaegerExporter(
                    agent_host_name=jaeger_host,
                    agent_port=jaeger_port
                )
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info("Jaeger exporter configured: %s:%d", jaeger_host, jaeger_port)
            except ImportError:
                logger.warning("Jaeger exporter not available, falling back to console")
                exporter_type = 'console'

        if exporter_type == 'console':
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            logger.info("Console span exporter configured")

        # Set the global tracer provider
        _trace.set_tracer_provider(provider)

        # Set up B3 propagation for compatibility with other systems
        set_global_textmap(B3MultiFormat())

        # Create the tracer
        _tracer = _trace.get_tracer(service_name, service_version)

        logger.info("OpenTelemetry tracing initialized for %s v%s", service_name, service_version)

    except Exception as e:
        logger.error("Failed to initialize OpenTelemetry: %s", str(e))
        _tracer = None


def instrument_flask(app: Any) -> None:
    """
    Instrument Flask application with OpenTelemetry.

    Args:
        app: Flask application instance
    """
    if not OTEL_AVAILABLE or not OTEL_ENABLED:
        return

    try:
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        FlaskInstrumentor().instrument_app(app)
        logger.info("Flask instrumented with OpenTelemetry")
    except ImportError:
        logger.warning("Flask instrumentation not available")
    except Exception as e:
        logger.error("Failed to instrument Flask: %s", str(e))


def instrument_requests() -> None:
    """Instrument the requests library with OpenTelemetry."""
    if not OTEL_AVAILABLE or not OTEL_ENABLED:
        return

    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        RequestsInstrumentor().instrument()
        logger.info("Requests library instrumented with OpenTelemetry")
    except ImportError:
        logger.warning("Requests instrumentation not available")
    except Exception as e:
        logger.error("Failed to instrument requests: %s", str(e))


def get_tracer():
    """Get the global tracer instance."""
    return _tracer


@contextmanager
def create_span(
    name: str,
    kind: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
):
    """
    Create a new span for tracing.

    Args:
        name: Name of the span
        kind: Kind of span (client, server, internal, producer, consumer)
        attributes: Optional attributes to add to the span

    Yields:
        The span context (or None if tracing disabled)

    Usage:
        with create_span("process_webhook", kind="server", attributes={"source": "Sonarr"}):
            # do work
    """
    if not OTEL_AVAILABLE or _tracer is None:
        yield None
        return

    # Map kind string to SpanKind enum
    span_kind = _SpanKind.INTERNAL
    if kind:
        kind_map = {
            'client': _SpanKind.CLIENT,
            'server': _SpanKind.SERVER,
            'internal': _SpanKind.INTERNAL,
            'producer': _SpanKind.PRODUCER,
            'consumer': _SpanKind.CONSUMER
        }
        span_kind = kind_map.get(kind.lower(), _SpanKind.INTERNAL)

    with _tracer.start_as_current_span(name, kind=span_kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        try:
            yield span
        except Exception as e:
            if span:
                span.set_status(_StatusCode.ERROR, str(e))
                span.record_exception(e)
            raise


def add_span_attribute(key: str, value: Any) -> None:
    """
    Add an attribute to the current span.

    Args:
        key: Attribute key
        value: Attribute value
    """
    if not OTEL_AVAILABLE or _trace is None:
        return

    span = _trace.get_current_span()
    if span:
        span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Add an event to the current span.

    Args:
        name: Event name
        attributes: Optional event attributes
    """
    if not OTEL_AVAILABLE or _trace is None:
        return

    span = _trace.get_current_span()
    if span:
        span.add_event(name, attributes=attributes or {})


def set_span_error(error: Exception) -> None:
    """
    Mark the current span as errored.

    Args:
        error: The exception that occurred
    """
    if not OTEL_AVAILABLE or _trace is None:
        return

    span = _trace.get_current_span()
    if span:
        span.set_status(_StatusCode.ERROR, str(error))
        span.record_exception(error)


def get_trace_context() -> Optional[Dict[str, str]]:
    """
    Get the current trace context for propagation.

    Returns:
        Dictionary with trace context headers, or None if tracing disabled
    """
    if not OTEL_AVAILABLE or _trace is None:
        return None

    try:
        from opentelemetry.propagate import inject
        carrier = {}
        inject(carrier)
        return carrier
    except Exception:
        return None


def trace_function(name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator to trace a function.

    Args:
        name: Optional span name (defaults to function name)
        attributes: Optional attributes to add to the span

    Usage:
        @trace_function(attributes={"operation": "scan"})
        def process_scan(path):
            # do work
    """
    def decorator(func):
        if not OTEL_AVAILABLE:
            return func

        from functools import wraps

        @wraps(func)
        def wrapper(*args, **kwargs):
            span_name = name or func.__name__
            with create_span(span_name, kind="internal", attributes=attributes):
                return func(*args, **kwargs)

        return wrapper
    return decorator
