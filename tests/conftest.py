"""
Pytest configuration and shared fixtures.

This module provides fixtures for testing the plex_emby_jellyfin_autoscan application.
"""

import os
import sys
import tempfile
import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_config():
    """Provide a mock configuration dictionary."""
    return {
        'SERVER_IP': '127.0.0.1',
        'SERVER_PORT': 3468,
        'SERVER_PASS': 'test_password',
        'SERVER_USE_SQLITE': True,
        'SERVER_ALLOW_MANUAL_SCAN': True,
        'SERVER_IGNORE_LIST': [],
        'PLEX_LOCAL_URL': 'http://localhost:32400',
        'PLEX_TOKEN': 'test_token',
        'PLEX_SCANNER': '/usr/lib/plexmediaserver/Plex Media Scanner',
        'PLEX_SUPPORT_DIR': '/var/lib/plexmediaserver/Library/Application Support',
        'PLEX_DATABASE_PATH': '/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db',
        'PLEX_EMPTY_TRASH': False,
        'PLEX_EMPTY_TRASH_MAX_FILES': 100,
        'PLEX_EMPTY_TRASH_ZERO_DELETED': False,
        'PLEX_SECTION_PATH_MAPPINGS': {},
        'JELLYFIN_API_KEY': 'test_jellyfin_key',
        'JELLYFIN_LOCAL_URL': 'http://localhost:8096',
        'EMBY_OR_JELLYFIN': 'jellyfin',
        'GOOGLE': {
            'ENABLED': False,
            'CLIENT_ID': '',
            'CLIENT_SECRET': '',
            'ALLOWED': {},
            'TEAMDRIVE': False,
            'TEAMDRIVES': [],
            'POLL_INTERVAL': 60,
            'SHOW_CACHE_LOGS': False
        },
        'RCLONE': {
            'BINARY': '/usr/bin/rclone',
            'CONFIG': '',
            'CRYPT_MAPPINGS': {}
        }
    }


@pytest.fixture
def app(mock_config):
    """Create a Flask test application."""
    from app import create_app

    test_app = create_app(
        config_name='testing',
        config_override={
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'RATELIMIT_ENABLED': False
        },
        server_pass='test_password'
    )

    yield test_app


@pytest.fixture
def client(app):
    """Create a Flask test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a Flask CLI test runner."""
    return app.test_cli_runner()


@pytest.fixture
def mock_thread_pool():
    """Create a mock thread pool for testing."""
    from threads import BoundedThreadPool

    pool = BoundedThreadPool(max_workers=2, thread_name_prefix="test")
    yield pool
    pool.shutdown(wait=True, timeout=5.0)


@pytest.fixture
def mock_circuit_breaker():
    """Create a test circuit breaker."""
    from app.circuit_breaker import FallbackCircuitBreaker

    cb = FallbackCircuitBreaker(
        fail_max=3,
        reset_timeout=1.0,  # Short timeout for tests
        name="test_breaker"
    )
    yield cb


@pytest.fixture
def sample_sonarr_webhook():
    """Sample Sonarr webhook payload."""
    return {
        'eventType': 'Download',
        'series': {
            'id': 1,
            'title': 'Test Series',
            'path': '/media/tv/Test Series',
            'tvdbId': 12345
        },
        'episodeFile': {
            'id': 100,
            'relativePath': 'Season 01/Test Series - S01E01.mkv',
            'path': '/media/tv/Test Series/Season 01/Test Series - S01E01.mkv',
            'quality': 'HDTV-720p'
        },
        'isUpgrade': False
    }


@pytest.fixture
def sample_radarr_webhook():
    """Sample Radarr webhook payload."""
    return {
        'eventType': 'Download',
        'movie': {
            'id': 1,
            'title': 'Test Movie',
            'folderPath': '/media/movies/Test Movie (2024)',
            'tmdbId': 54321,
            'imdbId': 'tt1234567'
        },
        'movieFile': {
            'id': 100,
            'relativePath': 'Test Movie (2024).mkv',
            'path': '/media/movies/Test Movie (2024)/Test Movie (2024).mkv',
            'quality': 'Bluray-1080p'
        },
        'remoteMovie': {
            'title': 'Test Movie',
            'year': 2024,
            'imdbId': 'tt1234567',
            'tmdbId': 54321
        },
        'isUpgrade': False
    }


@pytest.fixture
def sample_lidarr_webhook():
    """Sample Lidarr webhook payload."""
    return {
        'eventType': 'Download',
        'artist': {
            'id': 1,
            'name': 'Test Artist',
            'path': '/media/music/Test Artist'
        },
        'trackFiles': [
            {
                'id': 100,
                'path': '/media/music/Test Artist/Test Album/01 - Test Track.flac',
                'relativePath': 'Test Album/01 - Test Track.flac',
                'quality': 'FLAC'
            }
        ],
        'isUpgrade': False
    }


@pytest.fixture
def sample_manual_scan_webhook():
    """Sample manual scan webhook payload."""
    return {
        'eventType': 'Manual',
        'filepath': '/media/movies/Test Movie (2024)/Test Movie (2024).mkv'
    }


@pytest.fixture
def sample_test_webhook():
    """Sample test webhook payload."""
    return {
        'eventType': 'Test'
    }


# Environment setup for tests
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv('TESTING', 'true')
    monkeypatch.setenv('PROMETHEUS_ENABLED', 'false')
    monkeypatch.setenv('OTEL_ENABLED', 'false')
    monkeypatch.setenv('LOG_FORMAT', 'text')
