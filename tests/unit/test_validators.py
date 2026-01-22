"""
Essential unit tests for the validators module.
"""

import pytest


class TestValidatePath:
    """Core path validation tests."""

    def test_valid_path_passes(self):
        """Test that valid paths pass validation."""
        from validators import validate_path
        is_valid, sanitized, error = validate_path('/media/movies/Test.mkv')
        assert is_valid is True

    def test_empty_path_rejected(self):
        """Test that empty paths are rejected."""
        from validators import validate_path
        is_valid, _, error = validate_path('')
        assert is_valid is False

    def test_null_byte_blocked(self):
        """Test that null byte injection is blocked."""
        from validators import validate_path
        is_valid, _, error = validate_path('/media/movies\x00/evil.mkv')
        assert is_valid is False

    def test_directory_traversal_blocked(self):
        """Test that directory traversal is blocked."""
        from validators import validate_path
        is_valid, _, _ = validate_path('/media/../etc/passwd')
        assert is_valid is False


class TestValidateApiKey:
    """Core API key validation tests."""

    def test_valid_api_key_passes(self):
        """Test that valid API keys pass."""
        from validators import validate_api_key
        is_valid, error = validate_api_key('abcdef1234567890abcdef')
        assert is_valid is True

    def test_empty_api_key_rejected(self):
        """Test that empty API keys are rejected."""
        from validators import validate_api_key
        is_valid, error = validate_api_key('')
        assert is_valid is False


class TestValidateWebhookData:
    """Core webhook validation tests."""

    def test_valid_webhook_passes(self):
        """Test that valid webhook data passes."""
        from validators import validate_webhook_data
        data = {'eventType': 'Download', 'series': {'title': 'Test'}}
        is_valid, error = validate_webhook_data(data)
        assert is_valid is True

    def test_non_dict_rejected(self):
        """Test that non-dict data is rejected."""
        from validators import validate_webhook_data
        is_valid, error = validate_webhook_data('string')
        assert is_valid is False
