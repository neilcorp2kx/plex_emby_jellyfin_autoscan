"""
Pytest configuration and shared fixtures.
"""

import os
import sys
import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv('TESTING', 'true')
    monkeypatch.setenv('PROMETHEUS_ENABLED', 'false')
    monkeypatch.setenv('OTEL_ENABLED', 'false')
