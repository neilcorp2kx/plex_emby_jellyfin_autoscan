"""
Health check blueprint.

Provides endpoints for monitoring application health, status, and Prometheus metrics.
"""

from datetime import datetime
from typing import Tuple, Dict, Any

from flask import Blueprint, jsonify, current_app, Response

from app.extensions import limiter
from app.metrics import (
    get_metrics, get_metrics_content_type, update_health_status,
    update_queue_size, PROMETHEUS_AVAILABLE
)

# Circuit breaker imports (Phase 4)
try:
    from app.circuit_breaker import get_circuit_breaker_stats
    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    CIRCUIT_BREAKER_AVAILABLE = False

health_bp = Blueprint('health', __name__)


def get_db_status() -> str:
    """Check database connectivity."""
    try:
        import db
        return 'ok' if db.get_queue_count() is not None else 'error'
    except Exception:
        return 'error'


def get_thread_pool_stats() -> Tuple[str, Dict[str, Any]]:
    """Get thread pool statistics."""
    try:
        # Import from the module where thread pool is initialized
        import scan
        pool_stats = scan.thread.get_stats()
        return 'ok', pool_stats
    except Exception as e:
        return 'error', {'error': str(e)}


def get_orphaned_thread_count() -> int:
    """Get count of orphaned threads from timeout operations."""
    try:
        import utils
        return utils.get_orphaned_thread_count()
    except Exception:
        return -1


@health_bp.route('/health', methods=['GET'])
@limiter.limit("60 per minute")
def health_check():
    """
    Basic health check endpoint.

    Returns:
        JSON response with health status
    """
    db_status = get_db_status()
    thread_pool_status, pool_stats = get_thread_pool_stats()
    orphaned_threads = get_orphaned_thread_count()

    # Check shutdown status
    try:
        import scan
        shutdown_in_progress = scan._shutdown_in_progress
    except Exception:
        shutdown_in_progress = False

    is_healthy = db_status == 'ok' and thread_pool_status == 'ok'

    # Update Prometheus health metrics
    update_health_status('database', db_status == 'ok')
    update_health_status('thread_pool', thread_pool_status == 'ok')
    update_health_status('overall', is_healthy)

    # Update queue size metric
    queue_depth = get_queue_depth()
    update_queue_size(queue_depth)

    health = {
        'status': 'healthy' if is_healthy else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'checks': {
            'database': db_status,
            'thread_pool': thread_pool_status
        },
        'metrics': {
            'thread_pool': pool_stats,
            'orphaned_threads': orphaned_threads,
            'shutdown_in_progress': shutdown_in_progress,
            'queue_depth': queue_depth
        }
    }

    status_code = 200 if health['status'] == 'healthy' else 503
    return jsonify(health), status_code


@health_bp.route('/metrics', methods=['GET'])
@limiter.limit("60 per minute")
def prometheus_metrics():
    """
    Prometheus metrics endpoint.

    Returns:
        Prometheus-formatted metrics
    """
    # Update metrics before serving
    try:
        queue_depth = get_queue_depth()
        update_queue_size(queue_depth)

        db_status = get_db_status()
        thread_pool_status, pool_stats = get_thread_pool_stats()

        update_health_status('database', db_status == 'ok')
        update_health_status('thread_pool', thread_pool_status == 'ok')
        update_health_status('overall', db_status == 'ok' and thread_pool_status == 'ok')
    except Exception:
        pass

    return Response(
        get_metrics(),
        mimetype=get_metrics_content_type()
    )


@health_bp.route('/health/detailed', methods=['GET'])
@limiter.limit("30 per minute")
def detailed_health():
    """
    Detailed health check with dependency status.

    Returns:
        JSON response with detailed health information
    """
    import config as app_config
    conf = app_config.Config()

    db_status = get_db_status()
    thread_pool_status, pool_stats = get_thread_pool_stats()
    orphaned_threads = get_orphaned_thread_count()
    queue_depth = get_queue_depth()

    # Check Plex connectivity
    plex_status = check_plex_connectivity(conf.configs)

    # Check shutdown status
    try:
        import scan
        shutdown_in_progress = scan._shutdown_in_progress
    except Exception:
        shutdown_in_progress = False

    # Determine overall status
    overall = 'healthy'
    if db_status == 'error' or thread_pool_status == 'error':
        overall = 'unhealthy'
    elif plex_status.get('status') == 'error':
        overall = 'degraded'

    # Update Prometheus health metrics
    update_health_status('database', db_status == 'ok')
    update_health_status('thread_pool', thread_pool_status == 'ok')
    update_health_status('plex', plex_status.get('status') == 'ok')
    update_health_status('overall', overall == 'healthy')
    update_queue_size(queue_depth)

    # Get circuit breaker stats if available
    circuit_breakers = []
    if CIRCUIT_BREAKER_AVAILABLE:
        try:
            circuit_breakers = get_circuit_breaker_stats()
        except Exception:
            pass

    health = {
        'status': overall,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'checks': {
            'database': db_status,
            'thread_pool': thread_pool_status,
            'plex': plex_status
        },
        'metrics': {
            'thread_pool': pool_stats,
            'orphaned_threads': orphaned_threads,
            'shutdown_in_progress': shutdown_in_progress,
            'queue_depth': queue_depth,
            'prometheus_enabled': PROMETHEUS_AVAILABLE,
            'circuit_breakers': circuit_breakers
        }
    }

    status_code = 200 if overall == 'healthy' else (503 if overall == 'unhealthy' else 200)
    return jsonify(health), status_code


def check_plex_connectivity(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check Plex server connectivity.

    Args:
        config: Application configuration

    Returns:
        Dictionary with status and optional latency
    """
    import requests

    try:
        resp = requests.get(
            f"{config['PLEX_LOCAL_URL']}/identity",
            headers={'X-Plex-Token': config['PLEX_TOKEN']},
            timeout=5
        )
        return {
            'status': 'ok' if resp.status_code == 200 else 'degraded',
            'latency_ms': round(resp.elapsed.total_seconds() * 1000, 2)
        }
    except requests.exceptions.Timeout:
        return {'status': 'error', 'error': 'timeout'}
    except requests.exceptions.ConnectionError:
        return {'status': 'error', 'error': 'connection_refused'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def get_queue_depth() -> int:
    """Get current scan queue depth."""
    try:
        import db
        return db.get_queue_count() or 0
    except Exception:
        return -1
