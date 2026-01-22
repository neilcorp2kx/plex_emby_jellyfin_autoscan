"""
Unit tests for the validators module.

Tests cover path validation, API key validation, filename sanitization,
webhook data validation, and signature verification.
"""

import pytest
import os


class TestValidatePath:
    """Tests for validate_path function."""

    def test_valid_path(self):
        """Test that valid paths pass validation."""
        from validators import validate_path

        is_valid, sanitized, error = validate_path('/media/movies/Test Movie.mkv')
        assert is_valid is True
        assert sanitized is not None
        assert error is None

    def test_empty_path_rejected(self):
        """Test that empty paths are rejected."""
        from validators import validate_path

        is_valid, sanitized, error = validate_path('')
        assert is_valid is False
        assert sanitized is None
        assert 'empty' in error.lower()

    def test_none_path_rejected(self):
        """Test that None paths are rejected."""
        from validators import validate_path

        is_valid, sanitized, error = validate_path(None)
        assert is_valid is False
        assert sanitized is None

    def test_null_byte_injection_blocked(self):
        """Test that null byte injection is blocked."""
        from validators import validate_path

        is_valid, sanitized, error = validate_path('/media/movies\x00/evil.mkv')
        assert is_valid is False
        assert 'null' in error.lower()

    def test_directory_traversal_blocked(self):
        """Test that directory traversal attempts are blocked."""
        from validators import validate_path

        # Test .. traversal
        is_valid, _, error = validate_path('/media/../etc/passwd')
        assert is_valid is False

        # Test ~ expansion
        is_valid, _, error = validate_path('~/sensitive/file')
        assert is_valid is False

    def test_allowed_base_paths_enforced(self):
        """Test that allowed base paths are enforced when specified."""
        from validators import validate_path

        allowed = ['/media/movies', '/media/tv']

        # Path within allowed base should pass
        is_valid, _, _ = validate_path('/media/movies/Test.mkv', allowed_base_paths=allowed)
        assert is_valid is True

        # Path outside allowed base should fail
        is_valid, _, error = validate_path('/etc/passwd', allowed_base_paths=allowed)
        assert is_valid is False
        assert 'allowed' in error.lower()

    def test_path_resolved_to_absolute(self):
        """Test that paths are resolved to absolute paths."""
        from validators import validate_path

        is_valid, sanitized, _ = validate_path('relative/path/file.mkv')
        assert is_valid is True
        assert os.path.isabs(sanitized)


class TestValidateApiKey:
    """Tests for validate_api_key function."""

    def test_valid_api_key(self):
        """Test that valid API keys pass validation."""
        from validators import validate_api_key

        is_valid, error = validate_api_key('abcdef1234567890abcdef')
        assert is_valid is True
        assert error is None

    def test_empty_api_key_rejected(self):
        """Test that empty API keys are rejected."""
        from validators import validate_api_key

        is_valid, error = validate_api_key('')
        assert is_valid is False
        assert 'empty' in error.lower()

    def test_short_api_key_rejected(self):
        """Test that short API keys are rejected."""
        from validators import validate_api_key

        is_valid, error = validate_api_key('short', min_length=16)
        assert is_valid is False
        assert 'short' in error.lower()

    def test_long_api_key_rejected(self):
        """Test that excessively long API keys are rejected."""
        from validators import validate_api_key

        long_key = 'a' * 300
        is_valid, error = validate_api_key(long_key, max_length=256)
        assert is_valid is False
        assert 'long' in error.lower()

    def test_invalid_characters_rejected(self):
        """Test that API keys with invalid characters are rejected."""
        from validators import validate_api_key

        is_valid, error = validate_api_key('api-key-with-$pecial!')
        assert is_valid is False
        assert 'invalid' in error.lower()

    def test_null_byte_in_api_key_rejected(self):
        """Test that null bytes in API keys are rejected."""
        from validators import validate_api_key

        is_valid, error = validate_api_key('valid_key\x00_hidden')
        assert is_valid is False

    def test_alphanumeric_with_hyphens_underscores_allowed(self):
        """Test that alphanumeric keys with hyphens and underscores are allowed."""
        from validators import validate_api_key

        is_valid, error = validate_api_key('my_api-key_123-test')
        assert is_valid is True


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_normal_filename_unchanged(self):
        """Test that normal filenames pass through unchanged."""
        from validators import sanitize_filename

        result = sanitize_filename('Movie Title 2024.mkv')
        assert result == 'Movie Title 2024.mkv'

    def test_empty_filename_returns_empty(self):
        """Test that empty filename returns empty string."""
        from validators import sanitize_filename

        result = sanitize_filename('')
        assert result == ''

    def test_null_bytes_removed(self):
        """Test that null bytes are removed."""
        from validators import sanitize_filename

        result = sanitize_filename('file\x00name.txt')
        assert '\x00' not in result
        assert result == 'filename.txt'

    def test_path_separators_replaced(self):
        """Test that path separators are replaced with underscores."""
        from validators import sanitize_filename

        result = sanitize_filename('path/to/file.txt')
        assert '/' not in result
        assert result == 'path_to_file.txt'

        result = sanitize_filename('path\\to\\file.txt')
        assert '\\' not in result

    def test_dangerous_characters_removed(self):
        """Test that dangerous characters are removed."""
        from validators import sanitize_filename

        result = sanitize_filename('file<>:"|?*name.txt')
        # Only alphanumeric, spaces, hyphens, underscores, and periods kept
        assert '<' not in result
        assert '>' not in result
        assert ':' not in result

    def test_leading_trailing_dots_spaces_stripped(self):
        """Test that leading/trailing dots and spaces are stripped."""
        from validators import sanitize_filename

        result = sanitize_filename('...filename...')
        assert not result.startswith('.')
        assert not result.endswith('.')

        result = sanitize_filename('  filename  ')
        assert not result.startswith(' ')
        assert not result.endswith(' ')

    def test_long_filename_truncated(self):
        """Test that long filenames are truncated."""
        from validators import sanitize_filename

        long_name = 'a' * 300 + '.mkv'
        result = sanitize_filename(long_name, max_length=255)
        assert len(result) <= 255
        assert result.endswith('.mkv')


class TestValidateServerPass:
    """Tests for validate_server_pass function."""

    def test_valid_hex_server_pass(self):
        """Test that valid hex server passwords pass."""
        from validators import validate_server_pass

        # 32-character hex string (UUID without hyphens)
        is_valid, error = validate_server_pass('a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4')
        assert is_valid is True
        assert error is None

    def test_valid_alphanumeric_server_pass(self):
        """Test that valid alphanumeric server passwords pass."""
        from validators import validate_server_pass

        is_valid, error = validate_server_pass('my_secure_password_123')
        assert is_valid is True

    def test_empty_server_pass_rejected(self):
        """Test that empty server passwords are rejected."""
        from validators import validate_server_pass

        is_valid, error = validate_server_pass('')
        assert is_valid is False
        assert 'empty' in error.lower()

    def test_short_server_pass_rejected(self):
        """Test that short server passwords are rejected."""
        from validators import validate_server_pass

        is_valid, error = validate_server_pass('short')
        assert is_valid is False
        assert 'short' in error.lower()


class TestValidateScanSection:
    """Tests for validate_scan_section function."""

    def test_valid_section_id(self):
        """Test that valid section IDs pass."""
        from validators import validate_scan_section

        is_valid, section, error = validate_scan_section(1)
        assert is_valid is True
        assert section == 1
        assert error is None

    def test_string_section_id_converted(self):
        """Test that string section IDs are converted to int."""
        from validators import validate_scan_section

        is_valid, section, error = validate_scan_section('42')
        assert is_valid is True
        assert section == 42
        assert isinstance(section, int)

    def test_negative_section_id_rejected(self):
        """Test that negative section IDs are rejected."""
        from validators import validate_scan_section

        is_valid, _, error = validate_scan_section(-1)
        assert is_valid is False
        assert 'negative' in error.lower() or 'non-negative' in error.lower()

    def test_large_section_id_rejected(self):
        """Test that excessively large section IDs are rejected."""
        from validators import validate_scan_section

        is_valid, _, error = validate_scan_section(9999999)
        assert is_valid is False
        assert 'large' in error.lower()

    def test_invalid_section_id_rejected(self):
        """Test that invalid section IDs are rejected."""
        from validators import validate_scan_section

        is_valid, _, error = validate_scan_section('not_a_number')
        assert is_valid is False
        assert 'integer' in error.lower()


class TestValidateWebhookData:
    """Tests for validate_webhook_data function."""

    def test_valid_webhook_data(self):
        """Test that valid webhook data passes."""
        from validators import validate_webhook_data

        data = {
            'eventType': 'Download',
            'series': {'title': 'Test Show', 'path': '/media/tv/Test'}
        }
        is_valid, error = validate_webhook_data(data)
        assert is_valid is True
        assert error is None

    def test_non_dict_rejected(self):
        """Test that non-dictionary data is rejected."""
        from validators import validate_webhook_data

        is_valid, error = validate_webhook_data(['list', 'data'])
        assert is_valid is False
        assert 'dictionary' in error.lower()

        is_valid, error = validate_webhook_data('string data')
        assert is_valid is False

    def test_deeply_nested_data_rejected(self):
        """Test that deeply nested data is rejected (DoS protection)."""
        from validators import validate_webhook_data

        # Create deeply nested structure
        nested = {'level': 0}
        current = nested
        for i in range(15):  # More than max_depth of 10
            current['child'] = {'level': i + 1}
            current = current['child']

        is_valid, error = validate_webhook_data(nested)
        assert is_valid is False
        assert 'nested' in error.lower()

    def test_empty_dict_passes(self):
        """Test that empty dictionary passes validation."""
        from validators import validate_webhook_data

        is_valid, error = validate_webhook_data({})
        assert is_valid is True


class TestValidateUrl:
    """Tests for validate_url function."""

    def test_valid_http_url(self):
        """Test that valid HTTP URLs pass."""
        from validators import validate_url

        is_valid, error = validate_url('http://localhost:8080/path')
        assert is_valid is True

    def test_valid_https_url(self):
        """Test that valid HTTPS URLs pass."""
        from validators import validate_url

        is_valid, error = validate_url('https://example.com/api/v1')
        assert is_valid is True

    def test_empty_url_rejected(self):
        """Test that empty URLs are rejected."""
        from validators import validate_url

        is_valid, error = validate_url('')
        assert is_valid is False
        assert 'empty' in error.lower()

    def test_invalid_scheme_rejected(self):
        """Test that invalid URL schemes are rejected."""
        from validators import validate_url

        is_valid, error = validate_url('ftp://example.com/file')
        assert is_valid is False
        assert 'scheme' in error.lower()

    def test_malformed_url_rejected(self):
        """Test that malformed URLs are rejected."""
        from validators import validate_url

        is_valid, error = validate_url('not-a-valid-url')
        assert is_valid is False
        assert 'format' in error.lower()

    def test_null_byte_in_url_rejected(self):
        """Test that null bytes in URLs are rejected."""
        from validators import validate_url

        is_valid, error = validate_url('http://example.com\x00/path')
        assert is_valid is False


class TestVerifyWebhookSignature:
    """Tests for verify_webhook_signature function."""

    def test_valid_signature_verified(self):
        """Test that valid signatures are verified."""
        from validators import verify_webhook_signature
        import hmac
        import hashlib

        payload = b'{"test": "data"}'
        secret = 'my_secret_key'
        expected_sig = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        is_valid, error = verify_webhook_signature(payload, f'sha256={expected_sig}', secret)
        assert is_valid is True
        assert error is None

    def test_invalid_signature_rejected(self):
        """Test that invalid signatures are rejected."""
        from validators import verify_webhook_signature

        payload = b'{"test": "data"}'
        is_valid, error = verify_webhook_signature(payload, 'sha256=invalid_signature', 'secret')
        assert is_valid is False
        assert 'invalid' in error.lower()

    def test_missing_secret_rejected(self):
        """Test that missing secret is rejected."""
        from validators import verify_webhook_signature

        is_valid, error = verify_webhook_signature(b'payload', 'signature', None)
        assert is_valid is False
        assert 'not configured' in error.lower()

    def test_missing_signature_rejected(self):
        """Test that missing signature is rejected."""
        from validators import verify_webhook_signature

        is_valid, error = verify_webhook_signature(b'payload', None, 'secret')
        assert is_valid is False
        assert 'no signature' in error.lower()

    def test_string_payload_handled(self):
        """Test that string payloads are handled correctly."""
        from validators import verify_webhook_signature
        import hmac
        import hashlib

        payload = '{"test": "data"}'
        secret = 'my_secret_key'
        expected_sig = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        is_valid, error = verify_webhook_signature(payload, f'sha256={expected_sig}', secret)
        assert is_valid is True

    def test_plain_signature_format(self):
        """Test that plain signature format (without prefix) works."""
        from validators import verify_webhook_signature
        import hmac
        import hashlib

        payload = b'test'
        secret = 'secret'
        expected_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        # Without sha256= prefix
        is_valid, error = verify_webhook_signature(payload, expected_sig, secret)
        assert is_valid is True
