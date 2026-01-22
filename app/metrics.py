"""
Prometheus metrics for observability.

This module provides Prometheus metrics for monitoring scan operations,
queue depth, request latency, and system health.
"""

import os
import time
import logging
from functools import wraps
from typing import Callable, Optional

logger = logging.getLogger("METRICS")

# Check if Prometheus is enabled
PROMETHEUS_ENABLED = os.getenv('PROMETHEUS_ENABLED', 'true').lower() == 'true'

if PROMETHEUS_ENABLED:
    try:
        from prometheus_client import (
            Counter, Histogram, Gauge, Info,
            generate_latest, CONTENT_TYPE_LATEST,
            CollectorRegistry, multiprocess, REGISTRY
        )
        PROMETHEUS_AVAILABLE = True
    except ImportError:
        PROMETHEUS_AVAILABLE = False
        logger.warning("prometheus-client not installed, metrics disabled")
else:
    PROMETHEUS_AVAILABLE = False

# Default registry
_registry: Optional['CollectorRegistry'] = None


def get_registry() -> Optional['CollectorRegistry']:
    """Get the Prometheus registry."""
    global _registry
    if not PROMETHEUS_AVAILABLE:
        return None
    if _registry is None:
        # Check for multiprocess mode (Gunicorn with multiple workers)
        prometheus_multiproc_dir = os.getenv('PROMETHEUS_MULTIPROC_DIR')
        if prometheus_multiproc_dir:
            _registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(_registry)
        else:
            _registry = REGISTRY
    return _registry


# Metrics definitions (only created if Prometheus is available)
if PROMETHEUS_AVAILABLE:
    # Request metrics
    SCAN_REQUESTS_TOTAL = Counter(
        'autoscan_requests_total',
        'Total number of scan requests received',
        ['source', 'event_type', 'status']
    )

    SCAN_DURATION_SECONDS = Histogram(
        'autoscan_scan_duration_seconds',
        'Duration of scan operations in seconds',
        ['source', 'event_type'],
        buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0)
    )

    # Queue metrics
    QUEUE_SIZE = Gauge(
        'autoscan_queue_size',
        'Current number of items in the scan queue'
    )

    QUEUE_PROCESSING_TIME = Histogram(
        'autoscan_queue_processing_seconds',
        'Time spent processing items from queue',
        buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0)
    )

    # Thread pool metrics
    THREAD_POOL_ACTIVE = Gauge(
        'autoscan_thread_pool_active_threads',
        'Number of active threads in the scan pool'
    )

    THREAD_POOL_QUEUED = Gauge(
        'autoscan_thread_pool_queued_tasks',
        'Number of tasks queued for thread pool'
    )

    THREAD_POOL_COMPLETED = Counter(
        'autoscan_thread_pool_completed_total',
        'Total number of completed thread pool tasks',
        ['status']  # success, error, timeout
    )

    # External service metrics
    PLEX_REQUESTS_TOTAL = Counter(
        'autoscan_plex_requests_total',
        'Total Plex API requests',
        ['endpoint', 'status']
    )

    PLEX_REQUEST_DURATION = Histogram(
        'autoscan_plex_request_duration_seconds',
        'Plex API request duration',
        ['endpoint'],
        buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    )

    JELLYFIN_REQUESTS_TOTAL = Counter(
        'autoscan_jellyfin_requests_total',
        'Total Jellyfin/Emby API requests',
        ['endpoint', 'status']
    )

    # Health metrics
    HEALTH_CHECK_STATUS = Gauge(
        'autoscan_health_status',
        'Health check status (1=healthy, 0=unhealthy)',
        ['component']
    )

    # Application info
    APP_INFO = Info(
        'autoscan',
        'Application information'
    )

    # Error metrics
    ERROR_TOTAL = Counter(
        'autoscan_errors_total',
        'Total number of errors',
        ['error_type', 'component']
    )

    # Webhook metrics
    WEBHOOK_RECEIVED = Counter(
        'autoscan_webhook_received_total',
        'Total webhooks received',
        ['source']
    )

    WEBHOOK_PROCESSING_TIME = Histogram(
        'autoscan_webhook_processing_seconds',
        'Webhook processing time',
        ['source'],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
    )


def init_metrics(app_version: str = "unknown") -> None:
    """
    Initialize application metrics.

    Args:
        app_version: Application version string
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        APP_INFO.info({
            'version': app_version,
            'python_version': os.popen('python3 --version 2>/dev/null').read().strip() or 'unknown'
        })
        logger.info("Prometheus metrics initialized")
    except Exception as e:
        logger.error("Failed to initialize metrics: %s", str(e))


def track_request(source: str, event_type: str) -> Callable:
    """
    Decorator to track request metrics.

    Args:
        source: Source of the request (Sonarr, Radarr, etc.)
        event_type: Type of event (Download, Rename, etc.)

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not PROMETHEUS_AVAILABLE:
                return func(*args, **kwargs)

            start_time = time.time()
            status = 'success'
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                raise
            finally:
                duration = time.time() - start_time
                SCAN_REQUESTS_TOTAL.labels(
                    source=source,
                    event_type=event_type,
                    status=status
                ).inc()
                SCAN_DURATION_SECONDS.labels(
                    source=source,
                    event_type=event_type
                ).observe(duration)

        return wrapper
    return decorator


def track_scan_duration(source: str, event_type: str):
    """
    Context manager to track scan duration.

    Usage:
        with track_scan_duration('Sonarr', 'Download'):
            # perform scan
    """
    class ScanDurationTracker:
        def __init__(self):
            self.start_time = None

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if PROMETHEUS_AVAILABLE and self.start_time:
                duration = time.time() - self.start_time
                status = 'error' if exc_type else 'success'
                SCAN_REQUESTS_TOTAL.labels(
                    source=source,
                    event_type=event_type,
                    status=status
                ).inc()
                SCAN_DURATION_SECONDS.labels(
                    source=source,
                    event_type=event_type
                ).observe(duration)
            return False  # Don't suppress exceptions

    return ScanDurationTracker()


def update_queue_size(size: int) -> None:
    """Update the queue size gauge."""
    if PROMETHEUS_AVAILABLE:
        QUEUE_SIZE.set(size)


def update_thread_pool_metrics(active: int, queued: int) -> None:
    """Update thread pool metrics."""
    if PROMETHEUS_AVAILABLE:
        THREAD_POOL_ACTIVE.set(active)
        THREAD_POOL_QUEUED.set(queued)


def record_thread_completion(status: str = 'success') -> None:
    """Record a thread pool task completion."""
    if PROMETHEUS_AVAILABLE:
        THREAD_POOL_COMPLETED.labels(status=status).inc()


def record_plex_request(endpoint: str, status: str, duration: float) -> None:
    """Record a Plex API request."""
    if PROMETHEUS_AVAILABLE:
        PLEX_REQUESTS_TOTAL.labels(endpoint=endpoint, status=status).inc()
        PLEX_REQUEST_DURATION.labels(endpoint=endpoint).observe(duration)


def record_jellyfin_request(endpoint: str, status: str) -> None:
    """Record a Jellyfin/Emby API request."""
    if PROMETHEUS_AVAILABLE:
        JELLYFIN_REQUESTS_TOTAL.labels(endpoint=endpoint, status=status).inc()


def record_error(error_type: str, component: str) -> None:
    """Record an error occurrence."""
    if PROMETHEUS_AVAILABLE:
        ERROR_TOTAL.labels(error_type=error_type, component=component).inc()


def record_webhook(source: str, processing_time: float) -> None:
    """Record webhook receipt and processing time."""
    if PROMETHEUS_AVAILABLE:
        WEBHOOK_RECEIVED.labels(source=source).inc()
        WEBHOOK_PROCESSING_TIME.labels(source=source).observe(processing_time)


def update_health_status(component: str, healthy: bool) -> None:
    """Update health status for a component."""
    if PROMETHEUS_AVAILABLE:
        HEALTH_CHECK_STATUS.labels(component=component).set(1 if healthy else 0)


def get_metrics() -> bytes:
    """
    Generate Prometheus metrics output.

    Returns:
        Metrics in Prometheus text format
    """
    if not PROMETHEUS_AVAILABLE:
        return b"# Prometheus metrics disabled\n"

    registry = get_registry()
    return generate_latest(registry)


def get_metrics_content_type() -> str:
    """Get the content type for metrics endpoint."""
    if PROMETHEUS_AVAILABLE:
        return CONTENT_TYPE_LATEST
    return "text/plain"
