"""
Essential integration tests for health endpoints.
"""

import pytest
import json
from unittest.mock import patch


class TestHealthEndpoint:
    """Core health endpoint tests."""

    def test_health_returns_json(self, client):
        """Test that /health returns valid JSON."""
        with patch('app.blueprints.health.get_db_status', return_value='ok'), \
             patch('app.blueprints.health.get_thread_pool_stats', return_value=('ok', {})), \
             patch('app.blueprints.health.get_orphaned_thread_count', return_value=0), \
             patch('app.blueprints.health.get_queue_depth', return_value=0), \
             patch('app.blueprints.health.update_health_status'), \
             patch('app.blueprints.health.update_queue_size'), \
             patch('scan._shutdown_in_progress', False):

            response = client.get('/health')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'status' in data
            assert 'checks' in data

    def test_health_unhealthy_on_db_error(self, client):
        """Test that /health returns 503 when DB is down."""
        with patch('app.blueprints.health.get_db_status', return_value='error'), \
             patch('app.blueprints.health.get_thread_pool_stats', return_value=('ok', {})), \
             patch('app.blueprints.health.get_orphaned_thread_count', return_value=0), \
             patch('app.blueprints.health.get_queue_depth', return_value=0), \
             patch('app.blueprints.health.update_health_status'), \
             patch('app.blueprints.health.update_queue_size'), \
             patch('scan._shutdown_in_progress', False):

            response = client.get('/health')
            assert response.status_code == 503
