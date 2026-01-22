"""
Plex/Emby/Jellyfin Autoscan Application Factory.

This module provides the create_app() factory function for creating
Flask application instances following the application factory pattern.
"""

import logging
import os
import uuid
from typing import Optional, Dict, Any

from flask import Flask, g, request, jsonify

from app.config import get_config
from app.extensions import init_extensions, csrf, limiter

logger = logging.getLogger("APP")


def create_app(
    config_name: Optional[str] = None,
    config_override: Optional[Dict[str, Any]] = None,
    server_pass: Optional[str] = None
) -> Flask:
    """
    Application factory for creating Flask instances.

    This factory enables:
    - Multiple app instances with different configurations
    - Testing with isolated configurations
    - Flexible deployment options

    Args:
        config_name: Configuration name ('development', 'production', 'testing')
        config_override: Optional dictionary to override config values
        server_pass: Server password for URL routes. If None, loaded from config.

    Returns:
        Configured Flask application instance
    """
    # Create Flask app
    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static'
    )

    # Load configuration
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # Apply secret key fallbacks
    fallbacks = config_class.get_secret_key_fallbacks()
    if fallbacks:
        app.config['SECRET_KEY_FALLBACKS'] = fallbacks

    # Apply overrides
    if config_override:
        app.config.update(config_override)

    # Initialize extensions
    init_extensions(app)

    # Register error handlers
    register_error_handlers(app)

    # Register request hooks
    register_request_hooks(app)

    # Get server pass for blueprints
    if server_pass is None:
        import config
        conf = config.Config()
        server_pass = conf.configs['SERVER_PASS']
        allow_manual_scan = conf.configs.get('SERVER_ALLOW_MANUAL_SCAN', False)
    else:
        allow_manual_scan = False

    # Register blueprints
    register_blueprints(app, server_pass, allow_manual_scan)

    logger.info("Application created with config: %s", config_name or 'default')

    return app


def register_error_handlers(app: Flask) -> None:
    """Register error handlers for the application."""
    from app.errors import APIError

    @app.errorhandler(APIError)
    def handle_api_error(error):
        """Handle custom API errors."""
        response = jsonify({
            'status': 'error',
            'error': error.message,
            'error_code': error.error_code
        })
        response.status_code = error.status_code
        return response

    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle 400 Bad Request errors."""
        return jsonify({
            'status': 'error',
            'error': 'Bad request',
            'error_code': 'BAD_REQUEST'
        }), 400

    @app.errorhandler(401)
    def handle_unauthorized(error):
        """Handle 401 Unauthorized errors."""
        return jsonify({
            'status': 'error',
            'error': 'Unauthorized',
            'error_code': 'UNAUTHORIZED'
        }), 401

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found errors."""
        return jsonify({
            'status': 'error',
            'error': 'Not found',
            'error_code': 'NOT_FOUND'
        }), 404

    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 Internal Server errors."""
        logger.exception("Internal server error: %s", error)
        return jsonify({
            'status': 'error',
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500


def register_request_hooks(app: Flask) -> None:
    """Register request lifecycle hooks."""

    @app.before_request
    def add_correlation_id():
        """Add correlation ID to each request for tracing."""
        g.correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4())[:8])

    @app.after_request
    def add_correlation_header(response):
        """Add correlation ID to response headers."""
        if hasattr(g, 'correlation_id'):
            response.headers['X-Correlation-ID'] = g.correlation_id
        return response


def register_blueprints(app: Flask, server_pass: str, allow_manual_scan: bool) -> None:
    """
    Register all blueprints with the application.

    Args:
        app: Flask application instance
        server_pass: Server password for URL routes
        allow_manual_scan: Whether to allow manual scan requests
    """
    from app.blueprints.health import health_bp
    from app.blueprints.api import create_api_blueprint
    from app.blueprints.webhooks import create_webhooks_blueprint

    # Register health blueprint (always available)
    app.register_blueprint(health_bp)

    # Register API blueprint with server pass
    api_bp = create_api_blueprint(server_pass)
    app.register_blueprint(api_bp)

    # Register webhooks blueprint
    webhooks_bp = create_webhooks_blueprint(server_pass, allow_manual_scan)
    app.register_blueprint(webhooks_bp)

    logger.debug("Registered blueprints: health, api, webhooks")
