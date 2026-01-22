"""
Health check blueprint.

Provides endpoints for monitoring application health and status.
"""

from datetime import datetime
from typing import Tuple, Dict, Any

from flask import Blueprint, jsonify, current_app

from app.extensions import limiter

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

    health = {
        'status': 'healthy' if db_status == 'ok' and thread_pool_status == 'ok' else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'checks': {
            'database': db_status,
            'thread_pool': thread_pool_status
        },
        'metrics': {
            'thread_pool': pool_stats,
            'orphaned_threads': orphaned_threads,
            'shutdown_in_progress': shutdown_in_progress
        }
    }

    status_code = 200 if health['status'] == 'healthy' else 503
    return jsonify(health), status_code


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
            'queue_depth': get_queue_depth()
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
