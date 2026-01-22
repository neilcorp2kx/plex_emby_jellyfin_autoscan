"""
Scanner service for media library scanning.

This service encapsulates the scan orchestration logic, providing a clean
interface for triggering scans from webhooks, manual requests, and Google Drive.
"""

import logging
from typing import Optional

logger = logging.getLogger("SCANNER")

# Resilience imports (Phase 4)
try:
    from app.http_client import get_jellyfin_session
    from app.circuit_breaker import (
        get_jellyfin_circuit_breaker,
        with_circuit_breaker,
        CircuitBreakerError
    )
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False
    import requests

# Singleton instance
_scanner_service: Optional['ScannerService'] = None


class ScannerService:
    """
    Service for orchestrating media library scans.

    This class provides a high-level interface for:
    - Starting scans for Plex/Jellyfin/Emby
    - Managing the scan queue
    - Coordinating with external services
    """

    def __init__(self, config, thread_pool, scan_lock, resleep_paths: list):
        """
        Initialize the scanner service.

        Args:
            config: Application configuration object
            thread_pool: BoundedThreadPool for async scan execution
            scan_lock: PriorityLock for scan coordination
            resleep_paths: Shared list for tracking resleep paths
        """
        self.config = config
        self.thread_pool = thread_pool
        self.scan_lock = scan_lock
        self.resleep_paths = resleep_paths
        logger.info("ScannerService initialized")

    def start_scan(
        self,
        path: str,
        scan_for: str,
        scan_type: str,
        scan_title: Optional[str] = None,
        scan_lookup_type: Optional[str] = None,
        scan_lookup_id: Optional[str] = None
    ) -> bool:
        """
        Start a media library scan for the given path.

        Args:
            path: File path to scan
            scan_for: Source of scan request (Sonarr, Radarr, Lidarr, Manual, Google Drive)
            scan_type: Type of event (Download, Rename, Upgrade, Manual)
            scan_title: Optional title for logging
            scan_lookup_type: Optional lookup type
            scan_lookup_id: Optional lookup ID

        Returns:
            True if scan was started, False otherwise
        """
        import utils
        import db
        import plex

        # Get section ID for the path
        section = utils.get_plex_section(self.config.configs, path)
        if section <= 0:
            logger.warning("Could not find Plex section for path: %s", path)
            return False

        logger.info("Using Section ID '%d' for '%s'", section, path)

        # Add to database queue if enabled
        if self.config.configs['SERVER_USE_SQLITE']:
            db_exists, db_file = db.exists_file_root_path(path)
            if not db_exists and db.add_item(path, scan_for, section, scan_type):
                logger.info("Added '%s' to Plex Autoscan database.", path)
                logger.info("Proceeding with scan...")

                # Send Jellyfin/Emby notification
                self._notify_jellyfin(path)

            else:
                logger.info(
                    "Already processing '%s' from same folder. Skip adding extra scan request.",
                    db_file
                )
                self.resleep_paths.append(db_file)
                return False

        # Start async scan
        self.thread_pool.start(
            plex.scan,
            args=[
                self.config.configs,
                self.scan_lock,
                path,
                scan_for,
                section,
                scan_type,
                self.resleep_paths,
                scan_title,
                scan_lookup_type,
                scan_lookup_id
            ]
        )

        return True

    def _notify_jellyfin(self, path: str) -> None:
        """
        Send library update notification to Jellyfin/Emby.

        Uses circuit breaker pattern to prevent cascading failures
        when Jellyfin/Emby is unavailable.

        Args:
            path: Path that was updated
        """
        try:
            apikey = self.config.configs['JELLYFIN_API_KEY']
            jellyfin_url = self.config.configs['JELLYFIN_LOCAL_URL']
            emby_or_jellyfin = self.config.configs['EMBY_OR_JELLYFIN']

            endpoint_url = f"{jellyfin_url}/{emby_or_jellyfin}/Library/Media/Updated"

            payload = {
                "Updates": [{
                    "Path": path,
                    "UpdateType": "Created"
                }]
            }

            if RESILIENCE_AVAILABLE:
                # Use circuit breaker and resilient session
                cb = get_jellyfin_circuit_breaker()
                session = get_jellyfin_session()

                def do_notify():
                    return session.post(
                        endpoint_url,
                        params={'api_key': apikey},
                        headers={'accept': '*/*', 'Content-Type': 'application/json'},
                        json=payload,
                        timeout=30
                    )

                try:
                    response = with_circuit_breaker(cb, do_notify)
                    logger.info("Jellyfin/Emby notification sent for '%s' (status: %d)",
                               path, response.status_code)
                except CircuitBreakerError:
                    logger.warning("Jellyfin/Emby circuit breaker open, skipping notification for '%s'", path)
            else:
                # Fallback to direct requests
                import requests
                response = requests.post(
                    endpoint_url,
                    params={'api_key': apikey},
                    headers={'accept': '*/*', 'Content-Type': 'application/json'},
                    json=payload,
                    timeout=30
                )
                logger.info("Jellyfin/Emby notification sent for '%s' (status: %d)",
                           path, response.status_code)

        except Exception as e:
            logger.error("Failed to send Jellyfin/Emby notification for '%s': %s", path, str(e))

    def get_queue_count(self) -> int:
        """Get current queue count."""
        import db
        try:
            return db.get_queue_count() or 0
        except Exception:
            return 0

    def is_healthy(self) -> bool:
        """Check if scanner service is healthy."""
        return not self.thread_pool.is_shutting_down()


def init_scanner_service(config, thread_pool, scan_lock, resleep_paths: list) -> ScannerService:
    """
    Initialize the global scanner service.

    Args:
        config: Application configuration
        thread_pool: Thread pool for async operations
        scan_lock: Lock for scan coordination
        resleep_paths: Shared list for resleep tracking

    Returns:
        Initialized ScannerService instance
    """
    global _scanner_service
    _scanner_service = ScannerService(config, thread_pool, scan_lock, resleep_paths)
    return _scanner_service


def get_scanner_service() -> ScannerService:
    """
    Get the global scanner service instance.

    Returns:
        ScannerService instance

    Raises:
        RuntimeError: If service not initialized
    """
    global _scanner_service
    if _scanner_service is None:
        # Lazy initialization from scan module
        import scan
        _scanner_service = ScannerService(
            scan.conf,
            scan.thread,
            scan.scan_lock,
            scan.resleep_paths
        )
    return _scanner_service
