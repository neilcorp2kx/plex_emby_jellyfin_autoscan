#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Security validators module for Plex Autoscan
Provides input validation and sanitization functions
"""
import os
import re
import logging
import hmac
import hashlib
from pathlib import Path

logger = logging.getLogger("VALIDATORS")


def validate_path(path, allowed_base_paths=None):
    """
    Validate and sanitize file paths to prevent directory traversal attacks.

    Args:
        path: The path to validate
        allowed_base_paths: Optional list of allowed base paths

    Returns:
        tuple: (is_valid, sanitized_path, error_message)
    """
    if not path:
        return False, None, "Path cannot be empty"

    try:
        # Remove any null bytes
        if '\x00' in path:
            return False, None, "Path contains null bytes"

        # Resolve to absolute path and check for traversal attempts
        abs_path = os.path.abspath(path)

        # Check for common directory traversal patterns
        dangerous_patterns = ['..', '~/', '~\\']
        for pattern in dangerous_patterns:
            if pattern in path:
                logger.warning("Potential directory traversal attempt detected: %s", path)
                return False, None, "Path contains potentially dangerous patterns"

        # If allowed base paths are specified, verify the path starts with one of them
        if allowed_base_paths:
            is_allowed = False
            for base_path in allowed_base_paths:
                try:
                    # Resolve both paths and check if scan path is within allowed base
                    resolved_base = os.path.abspath(base_path)
                    if abs_path.startswith(resolved_base):
                        is_allowed = True
                        break
                except (ValueError, OSError) as e:
                    logger.error("Error validating base path %s: %s", base_path, e)
                    continue

            if not is_allowed:
                return False, None, f"Path is not within allowed base paths"

        return True, abs_path, None

    except (ValueError, OSError) as e:
        logger.error("Error validating path %s: %s", path, e)
        return False, None, f"Invalid path: {str(e)}"


def validate_api_key(api_key, min_length=16, max_length=256):
    """
    Validate API key format and length.

    Args:
        api_key: The API key to validate
        min_length: Minimum acceptable length
        max_length: Maximum acceptable length

    Returns:
        tuple: (is_valid, error_message)
    """
    if not api_key:
        return False, "API key cannot be empty"

    # Check for null bytes
    if '\x00' in api_key:
        return False, "API key contains invalid characters"

    # Check length
    if len(api_key) < min_length:
        return False, f"API key too short (minimum {min_length} characters)"

    if len(api_key) > max_length:
        return False, f"API key too long (maximum {max_length} characters)"

    # Check for valid characters (alphanumeric, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9_-]+$', api_key):
        return False, "API key contains invalid characters"

    return True, None


def sanitize_filename(filename, max_length=255):
    """
    Sanitize filename to prevent security issues.

    Args:
        filename: The filename to sanitize
        max_length: Maximum allowed filename length

    Returns:
        str: Sanitized filename
    """
    if not filename:
        return ""

    # Remove any null bytes
    filename = filename.replace('\x00', '')

    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')

    # Remove potentially dangerous characters
    # Keep alphanumeric, spaces, hyphens, underscores, and periods
    filename = re.sub(r'[^\w\s\-\.]', '', filename)

    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')

    # Truncate to max length
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        if ext:
            max_name_length = max_length - len(ext)
            filename = name[:max_name_length] + ext
        else:
            filename = filename[:max_length]

    return filename


def validate_server_pass(server_pass):
    """
    Validate server password/token format.

    Args:
        server_pass: The server password/token to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if not server_pass:
        return False, "Server password cannot be empty"

    # Check for null bytes
    if '\x00' in server_pass:
        return False, "Server password contains invalid characters"

    # Minimum length for security
    if len(server_pass) < 16:
        return False, "Server password too short (minimum 16 characters)"

    # Check for hex format (if it's a UUID-based token)
    if re.match(r'^[a-f0-9]{32}$', server_pass):
        return True, None

    # Otherwise check for reasonable characters
    if not re.match(r'^[a-zA-Z0-9_-]+$', server_pass):
        return False, "Server password contains invalid characters"

    return True, None


def validate_scan_section(section):
    """
    Validate Plex section ID.

    Args:
        section: The section ID to validate

    Returns:
        tuple: (is_valid, sanitized_section, error_message)
    """
    try:
        section_int = int(section)
        if section_int < 0:
            return False, None, "Section ID must be non-negative"
        if section_int > 999999:
            return False, None, "Section ID too large"
        return True, section_int, None
    except (ValueError, TypeError):
        return False, None, "Section ID must be a valid integer"


def validate_webhook_data(data):
    """
    Validate incoming webhook data structure.

    Args:
        data: Dictionary of webhook data

    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Webhook data must be a dictionary"

    # Check for excessive data size (potential DoS)
    import json
    try:
        data_size = len(json.dumps(data))
        if data_size > 1024 * 1024:  # 1MB limit
            return False, "Webhook data too large"
    except (TypeError, ValueError):
        return False, "Invalid webhook data format"

    # Check for suspicious nested depth (potential DoS)
    def check_depth(obj, current_depth=0, max_depth=10):
        if current_depth > max_depth:
            return False
        if isinstance(obj, dict):
            return all(check_depth(v, current_depth + 1, max_depth) for v in obj.values())
        elif isinstance(obj, list):
            return all(check_depth(item, current_depth + 1, max_depth) for item in obj)
        return True

    if not check_depth(data):
        return False, "Webhook data structure too deeply nested"

    return True, None


def validate_url(url, allowed_schemes=None):
    """
    Validate URL format and scheme.

    Args:
        url: The URL to validate
        allowed_schemes: List of allowed URL schemes (default: ['http', 'https'])

    Returns:
        tuple: (is_valid, error_message)
    """
    if not url:
        return False, "URL cannot be empty"

    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']

    # Check for null bytes
    if '\x00' in url:
        return False, "URL contains invalid characters"

    # Basic URL format validation
    url_pattern = re.compile(
        r'^(https?):\/\/'  # scheme
        r'([a-zA-Z0-9.-]+)'  # domain
        r'(:[0-9]+)?'  # optional port
        r'(\/.*)?$'  # optional path
    )

    if not url_pattern.match(url):
        return False, "Invalid URL format"

    # Check scheme
    scheme = url.split('://')[0].lower()
    if scheme not in allowed_schemes:
        return False, f"URL scheme must be one of: {', '.join(allowed_schemes)}"

    return True, None


def verify_webhook_signature(payload, signature, secret, algorithm='sha256'):
    """
    Verify HMAC signature for webhook requests (optional security enhancement).

    This function enables webhook signature verification to ensure requests are authentic.
    Common webhook providers (GitHub, Slack, etc.) sign their payloads with HMAC.

    Args:
        payload: The raw request body (bytes or str)
        signature: The signature header from the webhook request
        secret: The shared secret key used for signing
        algorithm: Hash algorithm to use (default: sha256)

    Returns:
        tuple: (is_valid, error_message)

    Example usage:
        # In Flask endpoint:
        signature = request.headers.get('X-Hub-Signature-256')  # GitHub style
        is_valid, error = verify_webhook_signature(
            request.get_data(),
            signature,
            os.getenv('WEBHOOK_SECRET')
        )

    Supported header formats:
        - GitHub: 'X-Hub-Signature-256: sha256=<signature>'
        - Slack: 'X-Slack-Signature: v0=<signature>'
        - Generic: '<algorithm>=<signature>' or just '<signature>'
    """
    if not secret:
        return False, "Webhook secret not configured"

    if not signature:
        return False, "No signature provided in request"

    # Convert payload to bytes if it's a string
    if isinstance(payload, str):
        payload = payload.encode('utf-8')

    # Convert secret to bytes if it's a string
    if isinstance(secret, str):
        secret = secret.encode('utf-8')

    # Parse signature format (handle 'sha256=...' or just the hex string)
    signature_value = signature
    if '=' in signature:
        # Format: "sha256=abc123..." or "v0=abc123..."
        _, signature_value = signature.split('=', 1)

    try:
        # Select hash algorithm
        if algorithm.lower() == 'sha256':
            hash_func = hashlib.sha256
        elif algorithm.lower() == 'sha1':
            hash_func = hashlib.sha1
        elif algorithm.lower() == 'sha512':
            hash_func = hashlib.sha512
        else:
            return False, f"Unsupported algorithm: {algorithm}"

        # Compute expected signature
        expected_signature = hmac.new(
            secret,
            payload,
            hash_func
        ).hexdigest()

        # Use constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(expected_signature, signature_value)

        if not is_valid:
            logger.warning("Webhook signature verification failed")
            return False, "Invalid webhook signature"

        return True, None

    except Exception as e:
        logger.error("Error verifying webhook signature: %s", str(e))
        return False, f"Signature verification error: {str(e)}"
