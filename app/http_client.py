"""
Resilient HTTP client with connection pooling and retry logic.

This module provides a pre-configured requests Session with:
- Connection pooling for better performance
- Automatic retries with exponential backoff
- Configurable timeouts
- Circuit breaker integration
"""

import logging
import os
from typing import Optional, Dict, Any, Tuple
from contextlib import contextmanager

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("HTTP_CLIENT")

# Default configuration from environment or sensible defaults
DEFAULT_TIMEOUT = float(os.getenv('HTTP_DEFAULT_TIMEOUT', '30'))
DEFAULT_POOL_CONNECTIONS = int(os.getenv('HTTP_POOL_CONNECTIONS', '10'))
DEFAULT_POOL_MAXSIZE = int(os.getenv('HTTP_POOL_MAXSIZE', '10'))
DEFAULT_MAX_RETRIES = int(os.getenv('HTTP_MAX_RETRIES', '3'))
DEFAULT_BACKOFF_FACTOR = float(os.getenv('HTTP_BACKOFF_FACTOR', '0.3'))

# Status codes that should trigger a retry
RETRY_STATUS_CODES = frozenset([408, 429, 500, 502, 503, 504])

# Methods that are safe to retry
RETRY_METHODS = frozenset(['HEAD', 'GET', 'PUT', 'DELETE', 'OPTIONS', 'TRACE'])


class ResilientHTTPAdapter(HTTPAdapter):
    """
    HTTP adapter with configurable timeouts and connection pooling.

    This adapter ensures all requests have a default timeout and
    uses connection pooling for better performance.
    """

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        pool_connections: int = DEFAULT_POOL_CONNECTIONS,
        pool_maxsize: int = DEFAULT_POOL_MAXSIZE,
        max_retries: Optional[Retry] = None,
        **kwargs
    ):
        self.timeout = timeout
        super().__init__(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=max_retries or Retry(0),
            **kwargs
        )

    def send(self, request, **kwargs):
        """Send request with default timeout if not specified."""
        if kwargs.get('timeout') is None:
            kwargs['timeout'] = self.timeout
        return super().send(request, **kwargs)


def create_retry_strategy(
    total: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: Optional[Tuple[int, ...]] = None,
    allowed_methods: Optional[Tuple[str, ...]] = None
) -> Retry:
    """
    Create a retry strategy for HTTP requests.

    Args:
        total: Total number of retries
        backoff_factor: Factor for exponential backoff (delay = factor * (2 ** retry))
        status_forcelist: HTTP status codes that trigger retry
        allowed_methods: HTTP methods that can be retried

    Returns:
        Configured Retry instance
    """
    return Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist or tuple(RETRY_STATUS_CODES),
        allowed_methods=allowed_methods or tuple(RETRY_METHODS),
        raise_on_status=False  # Don't raise on retry exhaustion, return response
    )


def create_resilient_session(
    timeout: float = DEFAULT_TIMEOUT,
    pool_connections: int = DEFAULT_POOL_CONNECTIONS,
    pool_maxsize: int = DEFAULT_POOL_MAXSIZE,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    retry_on_post: bool = False
) -> requests.Session:
    """
    Create a resilient HTTP session with connection pooling and retries.

    Args:
        timeout: Default request timeout in seconds
        pool_connections: Number of connection pools to cache
        pool_maxsize: Maximum connections per pool
        max_retries: Maximum number of retries per request
        backoff_factor: Exponential backoff factor
        retry_on_post: Whether to retry POST requests (default False for safety)

    Returns:
        Configured requests.Session

    Usage:
        session = create_resilient_session()
        response = session.get('https://api.example.com/data')
    """
    session = requests.Session()

    # Create retry strategy
    allowed_methods = list(RETRY_METHODS)
    if retry_on_post:
        allowed_methods.append('POST')

    retry_strategy = create_retry_strategy(
        total=max_retries,
        backoff_factor=backoff_factor,
        allowed_methods=tuple(allowed_methods)
    )

    # Create adapter with retry strategy
    adapter = ResilientHTTPAdapter(
        timeout=timeout,
        pool_connections=pool_connections,
        pool_maxsize=pool_maxsize,
        max_retries=retry_strategy
    )

    # Mount adapter for both HTTP and HTTPS
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    logger.debug("Created resilient session (timeout=%.1fs, pool=%d/%d, retries=%d)",
                timeout, pool_connections, pool_maxsize, max_retries)

    return session


# Global session instances for different use cases
_plex_session: Optional[requests.Session] = None
_jellyfin_session: Optional[requests.Session] = None
_general_session: Optional[requests.Session] = None


def get_plex_session() -> requests.Session:
    """
    Get a session configured for Plex API calls.

    Uses longer timeouts and more retries suitable for Plex operations.
    """
    global _plex_session
    if _plex_session is None:
        _plex_session = create_resilient_session(
            timeout=float(os.getenv('PLEX_HTTP_TIMEOUT', '60')),
            max_retries=int(os.getenv('PLEX_HTTP_RETRIES', '3')),
            pool_maxsize=int(os.getenv('PLEX_POOL_SIZE', '5'))
        )
        logger.info("Plex HTTP session initialized")
    return _plex_session


def get_jellyfin_session() -> requests.Session:
    """
    Get a session configured for Jellyfin/Emby API calls.
    """
    global _jellyfin_session
    if _jellyfin_session is None:
        _jellyfin_session = create_resilient_session(
            timeout=float(os.getenv('JELLYFIN_HTTP_TIMEOUT', '30')),
            max_retries=int(os.getenv('JELLYFIN_HTTP_RETRIES', '3')),
            pool_maxsize=int(os.getenv('JELLYFIN_POOL_SIZE', '5'))
        )
        logger.info("Jellyfin HTTP session initialized")
    return _jellyfin_session


def get_general_session() -> requests.Session:
    """
    Get a general-purpose resilient session.
    """
    global _general_session
    if _general_session is None:
        _general_session = create_resilient_session()
        logger.info("General HTTP session initialized")
    return _general_session


@contextmanager
def timeout_session(timeout: float):
    """
    Context manager for temporary session with specific timeout.

    Args:
        timeout: Timeout in seconds

    Usage:
        with timeout_session(5.0) as session:
            response = session.get('https://api.example.com')
    """
    session = create_resilient_session(timeout=timeout, max_retries=1)
    try:
        yield session
    finally:
        session.close()


class CircuitBreakerSession:
    """
    HTTP session wrapper with circuit breaker integration.

    Combines resilient HTTP session with circuit breaker pattern
    for comprehensive fault tolerance.
    """

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        circuit_breaker_name: str = "http",
        fail_max: int = 5,
        reset_timeout: float = 60.0
    ):
        """
        Initialize circuit breaker session.

        Args:
            session: Base requests session (created if None)
            circuit_breaker_name: Name for the circuit breaker
            fail_max: Failures before opening circuit
            reset_timeout: Seconds before retry attempt
        """
        self.session = session or create_resilient_session()
        self.circuit_breaker_name = circuit_breaker_name

        # Import here to avoid circular imports
        from app.circuit_breaker import get_circuit_breaker, CircuitBreakerError
        self.circuit_breaker = get_circuit_breaker(
            name=circuit_breaker_name,
            fail_max=fail_max,
            reset_timeout=reset_timeout
        )
        self.CircuitBreakerError = CircuitBreakerError

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request through circuit breaker."""
        from app.circuit_breaker import with_circuit_breaker

        def do_request():
            response = getattr(self.session, method)(url, **kwargs)
            # Consider 5xx errors as failures for circuit breaker
            if response.status_code >= 500:
                raise requests.exceptions.HTTPError(
                    f"Server error: {response.status_code}",
                    response=response
                )
            return response

        return with_circuit_breaker(self.circuit_breaker, do_request)

    def get(self, url: str, **kwargs) -> requests.Response:
        """GET request with circuit breaker."""
        return self._make_request('get', url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """POST request with circuit breaker."""
        return self._make_request('post', url, **kwargs)

    def put(self, url: str, **kwargs) -> requests.Response:
        """PUT request with circuit breaker."""
        return self._make_request('put', url, **kwargs)

    def delete(self, url: str, **kwargs) -> requests.Response:
        """DELETE request with circuit breaker."""
        return self._make_request('delete', url, **kwargs)

    def head(self, url: str, **kwargs) -> requests.Response:
        """HEAD request with circuit breaker."""
        return self._make_request('head', url, **kwargs)

    @property
    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        from app.circuit_breaker import PYBREAKER_AVAILABLE
        if PYBREAKER_AVAILABLE:
            return self.circuit_breaker.current_state == 'open'
        return self.circuit_breaker.state.value == 'open'

    def close(self):
        """Close the underlying session."""
        self.session.close()


def create_circuit_breaker_session(
    name: str,
    timeout: float = DEFAULT_TIMEOUT,
    fail_max: int = 5,
    reset_timeout: float = 60.0
) -> CircuitBreakerSession:
    """
    Create a session with both connection pooling and circuit breaker.

    Args:
        name: Circuit breaker name
        timeout: Request timeout
        fail_max: Circuit breaker failure threshold
        reset_timeout: Circuit breaker reset timeout

    Returns:
        CircuitBreakerSession instance
    """
    session = create_resilient_session(timeout=timeout)
    return CircuitBreakerSession(
        session=session,
        circuit_breaker_name=name,
        fail_max=fail_max,
        reset_timeout=reset_timeout
    )


def close_all_sessions():
    """Close all global session instances."""
    global _plex_session, _jellyfin_session, _general_session

    if _plex_session:
        _plex_session.close()
        _plex_session = None
        logger.debug("Plex session closed")

    if _jellyfin_session:
        _jellyfin_session.close()
        _jellyfin_session = None
        logger.debug("Jellyfin session closed")

    if _general_session:
        _general_session.close()
        _general_session = None
        logger.debug("General session closed")

    logger.info("All HTTP sessions closed")
