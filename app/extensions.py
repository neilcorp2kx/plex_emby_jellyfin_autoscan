"""
Flask extensions initialization.

This module initializes Flask extensions without binding them to a specific app,
following the application factory pattern. Extensions are initialized later
when create_app() is called.
"""

import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize extensions without app binding
csrf = CSRFProtect()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)


def init_extensions(app: Flask) -> None:
    """
    Initialize all Flask extensions with the app instance.

    Args:
        app: Flask application instance
    """
    # Initialize CSRF protection
    csrf.init_app(app)

    # Initialize rate limiter
    limiter.init_app(app)

    # Conditionally enable Flask-Talisman for security headers
    if os.getenv('ENABLE_TALISMAN', 'False').lower() == 'true':
        from flask_talisman import Talisman
        Talisman(
            app,
            force_https=os.getenv('FORCE_HTTPS', 'False').lower() == 'true',
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,  # 1 year
            content_security_policy=None,  # Disable CSP to avoid breaking existing functionality
            referrer_policy='strict-origin-when-cross-origin'
        )
