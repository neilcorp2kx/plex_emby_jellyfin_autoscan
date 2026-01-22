"""
API blueprint for programmatic access.

Provides JSON API endpoints for queue management and status.
"""

import logging
from typing import Tuple

from flask import Blueprint, jsonify, request, current_app

from app.extensions import limiter

logger = logging.getLogger("API")

# Create blueprint with dynamic URL prefix (set during registration)
api_bp = Blueprint('api', __name__)


def create_api_blueprint(server_pass: str) -> Blueprint:
    """
    Create API blueprint with the server password as URL prefix.

    Args:
        server_pass: Server password for URL

    Returns:
        Configured API blueprint
    """
    bp = Blueprint('api', __name__, url_prefix=f'/api/{server_pass}')

    @bp.route('', methods=['GET', 'POST'])
    @limiter.limit("30 per minute")
    def api_call():
        """
        Handle API calls.

        Supported commands:
        - queue_count: Get number of items in scan queue
        """
        import config
        import db

        conf = config.Config()
        data = {}

        try:
            if request.content_type == 'application/json':
                data = request.get_json(silent=True) or {}
            elif request.method == 'POST':
                data = request.form.to_dict()
            else:
                data = request.args.to_dict()

            # Verify cmd was supplied
            if 'cmd' not in data:
                logger.error("Unknown %s API call from %r", request.method, request.remote_addr)
                return jsonify({'error': 'No cmd parameter was supplied'})

            logger.info("Client %s API call from %r, type: %s", request.method, request.remote_addr, data['cmd'])

            # Process commands
            cmd = data['cmd'].lower()

            if cmd == 'queue_count':
                if not conf.configs['SERVER_USE_SQLITE']:
                    return jsonify({'error': 'SERVER_USE_SQLITE must be enabled'})
                return jsonify({'queue_count': db.get_queue_count()})

            elif cmd == 'health':
                # Lightweight health check via API
                try:
                    import scan
                    return jsonify({
                        'status': 'ok',
                        'thread_pool': scan.thread.get_stats(),
                        'shutdown_in_progress': scan._shutdown_in_progress
                    })
                except Exception as e:
                    return jsonify({'status': 'error', 'error': str(e)})

            else:
                return jsonify({'error': f'Unknown cmd: {cmd}'})

        except Exception:
            logger.exception("Exception parsing %s API call from %r: ", request.method, request.remote_addr)
            return jsonify({'error': 'Unexpected error occurred, check logs...'})

    return bp
