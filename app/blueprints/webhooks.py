"""
Webhooks blueprint for scan triggers.

Handles incoming webhook requests from Sonarr, Radarr, Lidarr, and manual scans.
"""

import json
import logging
import os
from typing import Tuple

from flask import Blueprint, request, abort, render_template, jsonify

from app.extensions import csrf, limiter
import validators

logger = logging.getLogger("WEBHOOKS")


def create_webhooks_blueprint(server_pass: str, allow_manual_scan: bool = False) -> Blueprint:
    """
    Create webhooks blueprint with server password as URL.

    Args:
        server_pass: Server password for URL
        allow_manual_scan: Whether to allow manual scan requests

    Returns:
        Configured webhooks blueprint
    """
    bp = Blueprint('webhooks', __name__)

    @bp.route(f'/{server_pass}', methods=['GET'])
    @limiter.limit("10 per minute")
    def manual_scan():
        """Render manual scan form."""
        if not allow_manual_scan:
            return abort(401)
        return render_template('manual_scan.html')

    @bp.route(f'/{server_pass}', methods=['POST'])
    @csrf.exempt
    @limiter.limit("30 per minute")
    def client_pushed():
        """
        Handle incoming webhook requests.

        Supports:
        - Sonarr/Radarr/Lidarr webhooks
        - Manual scan requests
        - Test events
        """
        import config
        import utils

        conf = config.Config()

        # Optional webhook signature verification
        webhook_secret = os.getenv('WEBHOOK_SECRET')
        if webhook_secret:
            signature = (
                request.headers.get('X-Hub-Signature-256') or
                request.headers.get('X-Slack-Signature') or
                request.headers.get('X-Webhook-Signature')
            )
            if signature:
                is_valid, error_msg = validators.verify_webhook_signature(
                    request.get_data(),
                    signature,
                    webhook_secret
                )
                if not is_valid:
                    logger.error("Webhook signature verification failed from %r: %s",
                                request.remote_addr, error_msg)
                    abort(401)
                logger.debug("Webhook signature verified successfully from %r", request.remote_addr)
            else:
                logger.warning("WEBHOOK_SECRET is configured but no signature header found from %r",
                             request.remote_addr)

        # Parse request data
        if request.content_type == 'application/json':
            data = request.get_json(silent=True)
        else:
            data = request.form.to_dict()

        if not data:
            logger.error("Invalid scan request from: %r", request.remote_addr)
            abort(400)

        # Validate webhook data structure
        is_valid, error_msg = validators.validate_webhook_data(data)
        if not is_valid:
            logger.error("Invalid webhook data from %r: %s", request.remote_addr, error_msg)
            abort(400)

        logger.debug("Client %r request dump:\n%s", request.remote_addr,
                    json.dumps(data, indent=4, sort_keys=True))

        # Handle different event types
        event_type = data.get('eventType') or data.get('EventType', '')

        if event_type == 'Test':
            logger.info("Client %r made a test request, event: 'Test'", request.remote_addr)
            return 'OK'

        elif event_type == 'Manual':
            return handle_manual_scan(data, conf, request.remote_addr)

        else:
            return handle_automated_scan(data, conf, request.remote_addr)

    return bp


def handle_manual_scan(data: dict, conf, remote_addr: str) -> Tuple[str, int]:
    """
    Handle manual scan requests.

    Args:
        data: Request data
        conf: Configuration object
        remote_addr: Client IP address

    Returns:
        Response tuple (body, status_code)
    """
    import utils
    from app.services.scanner import get_scanner_service

    filepath = data.get('filepath', '')
    logger.info("Client %r made a manual scan request for: '%s'", remote_addr, filepath)

    # Validate and sanitize filepath
    is_valid, sanitized_path, error_msg = validators.validate_path(filepath)
    if not is_valid:
        logger.error("Invalid filepath from %r: %s", remote_addr, error_msg)
        return render_template('scan_error.html', path=filepath), 400

    # Check ignore list
    should_ignore, ignore_match = utils.should_ignore(sanitized_path, conf.configs)
    if should_ignore:
        logger.info("Ignoring scan request for '%s' - matches ignore pattern: %s",
                   sanitized_path, ignore_match)
        return render_template('scan_error.html', path=sanitized_path), 200

    # Map path and start scan
    final_path = utils.map_pushed_path(conf.configs, sanitized_path)
    scanner = get_scanner_service()

    if scanner.start_scan(final_path, 'Manual', 'Manual'):
        return render_template('scan_success.html', path=final_path)
    else:
        return render_template('scan_error.html', path=final_path)


def handle_automated_scan(data: dict, conf, remote_addr: str) -> str:
    """
    Handle automated scan requests from Sonarr/Radarr/Lidarr.

    Args:
        data: Request data
        conf: Configuration object
        remote_addr: Client IP address

    Returns:
        Response string
    """
    import utils
    from app.services.scanner import get_scanner_service

    event_type = data.get('eventType') or data.get('EventType', 'Unknown')
    scanner = get_scanner_service()

    # Determine scan source based on data structure
    if 'movie' in data:
        scan_for = 'Radarr'
        scan_type = event_type
        paths = extract_radarr_paths(data)
    elif 'series' in data:
        scan_for = 'Sonarr'
        scan_type = event_type
        paths = extract_sonarr_paths(data)
    elif 'artist' in data:
        scan_for = 'Lidarr'
        scan_type = event_type
        paths = extract_lidarr_paths(data)
    else:
        logger.error("Unknown scan request from: %r", remote_addr)
        return 'Unknown request type'

    logger.info("Client %r made a %s request for %d path(s), event: '%s'",
               remote_addr, scan_for, len(paths), event_type)

    # Process each path
    for path in paths:
        # Validate path
        is_valid, sanitized_path, error_msg = validators.validate_path(path)
        if not is_valid:
            logger.warning("Skipping invalid path from %r: %s", remote_addr, error_msg)
            continue

        # Check ignore list
        should_ignore, ignore_match = utils.should_ignore(sanitized_path, conf.configs)
        if should_ignore:
            logger.info("Ignoring scan request for '%s' - matches ignore pattern: %s",
                       sanitized_path, ignore_match)
            continue

        # Map path and start scan
        final_path = utils.map_pushed_path(conf.configs, sanitized_path)

        # Get title for logging
        scan_title = data.get('movie', {}).get('title') or \
                    data.get('series', {}).get('title') or \
                    data.get('artist', {}).get('name') or ''

        scanner.start_scan(final_path, scan_for, scan_type, scan_title)

    return 'OK'


def extract_radarr_paths(data: dict) -> list:
    """Extract file paths from Radarr webhook data."""
    paths = []
    movie = data.get('movie', {})
    movie_file = data.get('movieFile', {})

    if movie_file.get('relativePath'):
        folder_path = movie.get('folderPath', '')
        if folder_path:
            paths.append(f"{folder_path}/{movie_file['relativePath']}")
    elif movie.get('folderPath'):
        paths.append(movie['folderPath'])

    return paths


def extract_sonarr_paths(data: dict) -> list:
    """Extract file paths from Sonarr webhook data."""
    paths = []
    series = data.get('series', {})
    episode_file = data.get('episodeFile', {})

    if episode_file.get('relativePath'):
        folder_path = series.get('path', '')
        if folder_path:
            paths.append(f"{folder_path}/{episode_file['relativePath']}")
    elif series.get('path'):
        paths.append(series['path'])

    return paths


def extract_lidarr_paths(data: dict) -> list:
    """Extract file paths from Lidarr webhook data."""
    paths = []
    artist = data.get('artist', {})
    track_files = data.get('trackFiles', [])

    for track_file in track_files:
        if track_file.get('path'):
            paths.append(track_file['path'])

    if not paths and artist.get('path'):
        paths.append(artist['path'])

    return paths
