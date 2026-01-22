"""
Integration tests for health check endpoints.

Tests cover /health, /health/detailed, and /metrics endpoints.
"""

import pytest
import json
from unittest.mock import patch, Mock


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_endpoint_returns_200_when_healthy(self, client):
        """Test that /health returns 200 when all checks pass."""
        with patch('app.blueprints.health.get_db_status', return_value='ok'), \
             patch('app.blueprints.health.get_thread_pool_stats', return_value=('ok', {'max_workers': 10})), \
             patch('app.blueprints.health.get_orphaned_thread_count', return_value=0), \
             patch('app.blueprints.health.get_queue_depth', return_value=0), \
             patch('app.blueprints.health.update_health_status'), \
             patch('app.blueprints.health.update_queue_size'), \
             patch('scan._shutdown_in_progress', False):

            response = client.get('/health')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'healthy'
            assert 'timestamp' in data
            assert 'checks' in data
            assert data['checks']['database'] == 'ok'
            assert data['checks']['thread_pool'] == 'ok'

    def test_health_endpoint_returns_503_when_db_unhealthy(self, client):
        """Test that /health returns 503 when database is unhealthy."""
        with patch('app.blueprints.health.get_db_status', return_value='error'), \
             patch('app.blueprints.health.get_thread_pool_stats', return_value=('ok', {})), \
             patch('app.blueprints.health.get_orphaned_thread_count', return_value=0), \
             patch('app.blueprints.health.get_queue_depth', return_value=0), \
             patch('app.blueprints.health.update_health_status'), \
             patch('app.blueprints.health.update_queue_size'), \
             patch('scan._shutdown_in_progress', False):

            response = client.get('/health')

            assert response.status_code == 503
            data = json.loads(response.data)
            assert data['status'] == 'unhealthy'

    def test_health_endpoint_returns_503_when_thread_pool_unhealthy(self, client):
        """Test that /health returns 503 when thread pool is unhealthy."""
        with patch('app.blueprints.health.get_db_status', return_value='ok'), \
             patch('app.blueprints.health.get_thread_pool_stats', return_value=('error', {'error': 'Pool error'})), \
             patch('app.blueprints.health.get_orphaned_thread_count', return_value=0), \
             patch('app.blueprints.health.get_queue_depth', return_value=0), \
             patch('app.blueprints.health.update_health_status'), \
             patch('app.blueprints.health.update_queue_size'), \
             patch('scan._shutdown_in_progress', False):

            response = client.get('/health')

            assert response.status_code == 503
            data = json.loads(response.data)
            assert data['status'] == 'unhealthy'

    def test_health_endpoint_includes_metrics(self, client):
        """Test that /health includes metrics section."""
        pool_stats = {
            'max_workers': 10,
            'active_count': 2,
            'is_at_capacity': False
        }

        with patch('app.blueprints.health.get_db_status', return_value='ok'), \
             patch('app.blueprints.health.get_thread_pool_stats', return_value=('ok', pool_stats)), \
             patch('app.blueprints.health.get_orphaned_thread_count', return_value=1), \
             patch('app.blueprints.health.get_queue_depth', return_value=5), \
             patch('app.blueprints.health.update_health_status'), \
             patch('app.blueprints.health.update_queue_size'), \
             patch('scan._shutdown_in_progress', False):

            response = client.get('/health')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'metrics' in data
            assert data['metrics']['thread_pool'] == pool_stats
            assert data['metrics']['orphaned_threads'] == 1
            assert data['metrics']['queue_depth'] == 5
            assert data['metrics']['shutdown_in_progress'] is False

    def test_health_endpoint_shows_shutdown_in_progress(self, client):
        """Test that /health shows when shutdown is in progress."""
        with patch('app.blueprints.health.get_db_status', return_value='ok'), \
             patch('app.blueprints.health.get_thread_pool_stats', return_value=('ok', {})), \
             patch('app.blueprints.health.get_orphaned_thread_count', return_value=0), \
             patch('app.blueprints.health.get_queue_depth', return_value=0), \
             patch('app.blueprints.health.update_health_status'), \
             patch('app.blueprints.health.update_queue_size'), \
             patch('scan._shutdown_in_progress', True):

            response = client.get('/health')
            data = json.loads(response.data)
            assert data['metrics']['shutdown_in_progress'] is True


class TestDetailedHealthEndpoint:
    """Tests for the /health/detailed endpoint."""

    def test_detailed_health_returns_plex_status(self, client, mock_config):
        """Test that /health/detailed includes Plex connectivity check."""
        plex_status = {'status': 'ok', 'latency_ms': 25.5}

        with patch('app.blueprints.health.get_db_status', return_value='ok'), \
             patch('app.blueprints.health.get_thread_pool_stats', return_value=('ok', {})), \
             patch('app.blueprints.health.get_orphaned_thread_count', return_value=0), \
             patch('app.blueprints.health.get_queue_depth', return_value=0), \
             patch('app.blueprints.health.check_plex_connectivity', return_value=plex_status), \
             patch('app.blueprints.health.update_health_status'), \
             patch('app.blueprints.health.update_queue_size'), \
             patch('app.blueprints.health.get_circuit_breaker_stats', return_value=[]), \
             patch('scan._shutdown_in_progress', False), \
             patch('config.Config') as mock_conf:

            mock_conf.return_value.configs = mock_config
            response = client.get('/health/detailed')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['checks']['plex'] == plex_status

    def test_detailed_health_degraded_when_plex_down(self, client, mock_config):
        """Test that /health/detailed returns degraded when Plex is down."""
        plex_status = {'status': 'error', 'error': 'connection_refused'}

        with patch('app.blueprints.health.get_db_status', return_value='ok'), \
             patch('app.blueprints.health.get_thread_pool_stats', return_value=('ok', {})), \
             patch('app.blueprints.health.get_orphaned_thread_count', return_value=0), \
             patch('app.blueprints.health.get_queue_depth', return_value=0), \
             patch('app.blueprints.health.check_plex_connectivity', return_value=plex_status), \
             patch('app.blueprints.health.update_health_status'), \
             patch('app.blueprints.health.update_queue_size'), \
             patch('app.blueprints.health.get_circuit_breaker_stats', return_value=[]), \
             patch('scan._shutdown_in_progress', False), \
             patch('config.Config') as mock_conf:

            mock_conf.return_value.configs = mock_config
            response = client.get('/health/detailed')

            data = json.loads(response.data)
            assert data['status'] == 'degraded'

    def test_detailed_health_includes_circuit_breaker_stats(self, client, mock_config):
        """Test that /health/detailed includes circuit breaker statistics."""
        cb_stats = [
            {'name': 'plex', 'state': 'closed', 'failure_count': 0},
            {'name': 'jellyfin', 'state': 'closed', 'failure_count': 0}
        ]

        with patch('app.blueprints.health.get_db_status', return_value='ok'), \
             patch('app.blueprints.health.get_thread_pool_stats', return_value=('ok', {})), \
             patch('app.blueprints.health.get_orphaned_thread_count', return_value=0), \
             patch('app.blueprints.health.get_queue_depth', return_value=0), \
             patch('app.blueprints.health.check_plex_connectivity', return_value={'status': 'ok'}), \
             patch('app.blueprints.health.update_health_status'), \
             patch('app.blueprints.health.update_queue_size'), \
             patch('app.blueprints.health.get_circuit_breaker_stats', return_value=cb_stats), \
             patch('app.blueprints.health.CIRCUIT_BREAKER_AVAILABLE', True), \
             patch('scan._shutdown_in_progress', False), \
             patch('config.Config') as mock_conf:

            mock_conf.return_value.configs = mock_config
            response = client.get('/health/detailed')

            data = json.loads(response.data)
            assert 'circuit_breakers' in data['metrics']

    def test_detailed_health_shows_prometheus_status(self, client, mock_config):
        """Test that /health/detailed shows Prometheus availability."""
        with patch('app.blueprints.health.get_db_status', return_value='ok'), \
             patch('app.blueprints.health.get_thread_pool_stats', return_value=('ok', {})), \
             patch('app.blueprints.health.get_orphaned_thread_count', return_value=0), \
             patch('app.blueprints.health.get_queue_depth', return_value=0), \
             patch('app.blueprints.health.check_plex_connectivity', return_value={'status': 'ok'}), \
             patch('app.blueprints.health.update_health_status'), \
             patch('app.blueprints.health.update_queue_size'), \
             patch('app.blueprints.health.get_circuit_breaker_stats', return_value=[]), \
             patch('scan._shutdown_in_progress', False), \
             patch('config.Config') as mock_conf:

            mock_conf.return_value.configs = mock_config
            response = client.get('/health/detailed')

            data = json.loads(response.data)
            assert 'prometheus_enabled' in data['metrics']


class TestMetricsEndpoint:
    """Tests for the /metrics endpoint."""

    def test_metrics_endpoint_returns_prometheus_format(self, client):
        """Test that /metrics returns Prometheus-formatted metrics."""
        mock_metrics = """# HELP autoscan_requests_total Total scan requests
# TYPE autoscan_requests_total counter
autoscan_requests_total{source="sonarr",status="success"} 42
"""
        with patch('app.blueprints.health.get_metrics', return_value=mock_metrics), \
             patch('app.blueprints.health.get_metrics_content_type', return_value='text/plain; version=0.0.4'), \
             patch('app.blueprints.health.get_queue_depth', return_value=0), \
             patch('app.blueprints.health.get_db_status', return_value='ok'), \
             patch('app.blueprints.health.get_thread_pool_stats', return_value=('ok', {})), \
             patch('app.blueprints.health.update_health_status'), \
             patch('app.blueprints.health.update_queue_size'):

            response = client.get('/metrics')

            assert response.status_code == 200
            assert 'text/plain' in response.content_type
            assert b'autoscan_requests_total' in response.data

    def test_metrics_endpoint_updates_metrics_before_serving(self, client):
        """Test that /metrics updates health metrics before serving."""
        update_health_mock = Mock()
        update_queue_mock = Mock()

        with patch('app.blueprints.health.get_metrics', return_value=''), \
             patch('app.blueprints.health.get_metrics_content_type', return_value='text/plain'), \
             patch('app.blueprints.health.get_queue_depth', return_value=5), \
             patch('app.blueprints.health.get_db_status', return_value='ok'), \
             patch('app.blueprints.health.get_thread_pool_stats', return_value=('ok', {})), \
             patch('app.blueprints.health.update_health_status', update_health_mock), \
             patch('app.blueprints.health.update_queue_size', update_queue_mock):

            client.get('/metrics')

            # Verify update functions were called
            assert update_health_mock.called
            update_queue_mock.assert_called_with(5)


class TestPlexConnectivityCheck:
    """Tests for the Plex connectivity check function."""

    def test_check_plex_returns_ok_on_success(self):
        """Test Plex connectivity returns ok on successful response."""
        from app.blueprints.health import check_plex_connectivity
        import requests

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.025

        config = {
            'PLEX_LOCAL_URL': 'http://localhost:32400',
            'PLEX_TOKEN': 'test_token'
        }

        with patch('requests.get', return_value=mock_response):
            result = check_plex_connectivity(config)

            assert result['status'] == 'ok'
            assert result['latency_ms'] == 25.0

    def test_check_plex_returns_error_on_timeout(self):
        """Test Plex connectivity returns error on timeout."""
        from app.blueprints.health import check_plex_connectivity
        import requests

        config = {
            'PLEX_LOCAL_URL': 'http://localhost:32400',
            'PLEX_TOKEN': 'test_token'
        }

        with patch('requests.get', side_effect=requests.exceptions.Timeout()):
            result = check_plex_connectivity(config)

            assert result['status'] == 'error'
            assert result['error'] == 'timeout'

    def test_check_plex_returns_error_on_connection_refused(self):
        """Test Plex connectivity returns error on connection refused."""
        from app.blueprints.health import check_plex_connectivity
        import requests

        config = {
            'PLEX_LOCAL_URL': 'http://localhost:32400',
            'PLEX_TOKEN': 'test_token'
        }

        with patch('requests.get', side_effect=requests.exceptions.ConnectionError()):
            result = check_plex_connectivity(config)

            assert result['status'] == 'error'
            assert result['error'] == 'connection_refused'

    def test_check_plex_returns_degraded_on_non_200(self):
        """Test Plex connectivity returns degraded on non-200 response."""
        from app.blueprints.health import check_plex_connectivity

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.elapsed.total_seconds.return_value = 0.010

        config = {
            'PLEX_LOCAL_URL': 'http://localhost:32400',
            'PLEX_TOKEN': 'bad_token'
        }

        with patch('requests.get', return_value=mock_response):
            result = check_plex_connectivity(config)

            assert result['status'] == 'degraded'
