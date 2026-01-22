"""
Flask application configuration classes.

This module provides configuration classes for different environments
following the application factory pattern.
"""

import os
import secrets


class BaseConfig:
    """Base configuration with defaults."""

    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(32))
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    SESSION_REFRESH_EACH_REQUEST = True  # Extend session on each request

    # JSON
    JSON_AS_ASCII = False

    # Support for rotating secret keys
    @staticmethod
    def get_secret_key_fallbacks():
        fallback_keys = os.getenv('SECRET_KEY_FALLBACKS', '')
        if fallback_keys:
            return [key.strip() for key in fallback_keys.split(',') if key.strip()]
        return []


class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    TESTING = False


class TestingConfig(BaseConfig):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False  # Disable CSRF for testing


# Configuration mapping
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
}


def get_config(env_name: str = None):
    """
    Get configuration class by environment name.

    Args:
        env_name: Environment name ('development', 'production', 'testing')
                  If None, uses FLASK_ENV environment variable.

    Returns:
        Configuration class
    """
    if env_name is None:
        env_name = os.getenv('FLASK_ENV', 'production')
    return config_by_name.get(env_name, config_by_name['default'])
