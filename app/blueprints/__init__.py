"""
Flask blueprints for the application.

This package contains modular blueprints for:
- health: Health check endpoints
- api: Programmatic API access
- webhooks: Webhook handlers for scan triggers
"""

from app.blueprints.health import health_bp
from app.blueprints.api import create_api_blueprint
from app.blueprints.webhooks import create_webhooks_blueprint

__all__ = ['health_bp', 'create_api_blueprint', 'create_webhooks_blueprint']
