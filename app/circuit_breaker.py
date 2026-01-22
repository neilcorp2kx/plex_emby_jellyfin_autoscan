"""
Circuit breaker implementation for external service resilience.

This module provides circuit breakers for external services (Plex, Jellyfin, Google)
to prevent cascading failures when services become unavailable.

Circuit breaker states:
- CLOSED: Normal operation, requests pass through
- OPEN: Service unavailable, requests fail fast
- HALF-OPEN: Testing if service recovered
"""

import logging
import os
import time
from functools import wraps
from typing import Callable, Optional, Any, Dict, List
from enum import Enum
from threading import Lock
from dataclasses import dataclass, field

logger = logging.getLogger("CIRCUIT_BREAKER")

# Check if pybreaker is available
PYBREAKER_AVAILABLE = False
try:
    import pybreaker
    PYBREAKER_AVAILABLE = True
except ImportError:
    logger.info("pybreaker not installed, using fallback circuit breaker implementation")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    fail_max: int = 5  # Number of failures before opening
    reset_timeout: float = 60.0  # Seconds before attempting reset
    exclude_exceptions: tuple = ()  # Exceptions that don't count as failures
    name: str = "default"


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring."""
    name: str
    state: str
    failure_count: int
    success_count: int
    last_failure_time: Optional[float]
    last_success_time: Optional[float]
    total_calls: int
    total_failures: int


class FallbackCircuitBreaker:
    """
    Fallback circuit breaker implementation when pybreaker is not available.

    Implements the circuit breaker pattern with three states:
    - CLOSED: Normal operation
    - OPEN: Failing fast (service unavailable)
    - HALF-OPEN: Testing recovery
    """

    def __init__(
        self,
        fail_max: int = 5,
        reset_timeout: float = 60.0,
        exclude: tuple = (),
        name: str = "default"
    ):
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self.exclude = exclude
        self.name = name

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._total_calls = 0
        self._total_failures = 0
        self._lock = Lock()

        logger.info("Circuit breaker '%s' initialized (fail_max=%d, reset_timeout=%.1fs)",
                   name, fail_max, reset_timeout)

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for timeout transition."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._last_failure_time and \
                   (time.time() - self._last_failure_time) >= self.reset_timeout:
                    self._state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker '%s' transitioning to HALF-OPEN", self.name)
            return self._state

    @property
    def current_state(self) -> str:
        """Get current state as string."""
        return self.state.value

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception from the function
        """
        current_state = self.state

        if current_state == CircuitState.OPEN:
            logger.warning("Circuit breaker '%s' is OPEN, failing fast", self.name)
            raise CircuitBreakerError(f"Circuit breaker '{self.name}' is open")

        with self._lock:
            self._total_calls += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.exclude:
            # Excluded exceptions don't count as failures
            raise
        except Exception as e:
            self._on_failure(e)
            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        with self._lock:
            self._success_count += 1
            self._last_success_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Recovery successful, close the circuit
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info("Circuit breaker '%s' recovered, now CLOSED", self.name)
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    def _on_failure(self, error: Exception) -> None:
        """Handle failed call."""
        with self._lock:
            self._failure_count += 1
            self._total_failures += 1
            self._last_failure_time = time.time()

            logger.warning("Circuit breaker '%s' recorded failure (%d/%d): %s",
                          self.name, self._failure_count, self.fail_max, str(error))

            if self._state == CircuitState.HALF_OPEN:
                # Recovery failed, reopen the circuit
                self._state = CircuitState.OPEN
                logger.warning("Circuit breaker '%s' recovery failed, now OPEN", self.name)
            elif self._failure_count >= self.fail_max:
                # Too many failures, open the circuit
                self._state = CircuitState.OPEN
                logger.warning("Circuit breaker '%s' threshold reached, now OPEN", self.name)

    def get_stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics."""
        with self._lock:
            return CircuitBreakerStats(
                name=self.name,
                state=self._state.value,
                failure_count=self._failure_count,
                success_count=self._success_count,
                last_failure_time=self._last_failure_time,
                last_success_time=self._last_success_time,
                total_calls=self._total_calls,
                total_failures=self._total_failures
            )

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            logger.info("Circuit breaker '%s' manually reset to CLOSED", self.name)


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Circuit breaker registry
_circuit_breakers: Dict[str, Any] = {}
_registry_lock = Lock()


def get_circuit_breaker(
    name: str,
    fail_max: int = 5,
    reset_timeout: float = 60.0,
    exclude: tuple = ()
) -> Any:
    """
    Get or create a circuit breaker by name.

    Args:
        name: Unique name for the circuit breaker
        fail_max: Number of failures before opening circuit
        reset_timeout: Seconds before attempting to close circuit
        exclude: Exception types to exclude from failure counting

    Returns:
        Circuit breaker instance
    """
    with _registry_lock:
        if name not in _circuit_breakers:
            if PYBREAKER_AVAILABLE:
                _circuit_breakers[name] = pybreaker.CircuitBreaker(
                    fail_max=fail_max,
                    reset_timeout=reset_timeout,
                    exclude=[exc for exc in exclude],
                    name=name
                )
            else:
                _circuit_breakers[name] = FallbackCircuitBreaker(
                    fail_max=fail_max,
                    reset_timeout=reset_timeout,
                    exclude=exclude,
                    name=name
                )
        return _circuit_breakers[name]


def get_all_circuit_breakers() -> Dict[str, Any]:
    """Get all registered circuit breakers."""
    with _registry_lock:
        return dict(_circuit_breakers)


def get_circuit_breaker_stats() -> List[Dict[str, Any]]:
    """Get statistics for all circuit breakers."""
    stats = []
    with _registry_lock:
        for name, cb in _circuit_breakers.items():
            if PYBREAKER_AVAILABLE:
                stats.append({
                    'name': name,
                    'state': cb.current_state,
                    'failure_count': cb.fail_counter,
                    'success_count': getattr(cb, 'success_counter', 0),
                })
            else:
                cb_stats = cb.get_stats()
                stats.append({
                    'name': cb_stats.name,
                    'state': cb_stats.state,
                    'failure_count': cb_stats.failure_count,
                    'success_count': cb_stats.success_count,
                    'total_calls': cb_stats.total_calls,
                    'total_failures': cb_stats.total_failures,
                })
    return stats


# Pre-configured circuit breakers for common services
def get_plex_circuit_breaker():
    """Get circuit breaker for Plex API calls."""
    return get_circuit_breaker(
        name="plex",
        fail_max=int(os.getenv('PLEX_CB_FAIL_MAX', '5')),
        reset_timeout=float(os.getenv('PLEX_CB_RESET_TIMEOUT', '60'))
    )


def get_jellyfin_circuit_breaker():
    """Get circuit breaker for Jellyfin/Emby API calls."""
    return get_circuit_breaker(
        name="jellyfin",
        fail_max=int(os.getenv('JELLYFIN_CB_FAIL_MAX', '5')),
        reset_timeout=float(os.getenv('JELLYFIN_CB_RESET_TIMEOUT', '60'))
    )


def get_google_circuit_breaker():
    """Get circuit breaker for Google Drive API calls."""
    return get_circuit_breaker(
        name="google",
        fail_max=int(os.getenv('GOOGLE_CB_FAIL_MAX', '3')),
        reset_timeout=float(os.getenv('GOOGLE_CB_RESET_TIMEOUT', '120'))
    )


def circuit_breaker(name: str, fail_max: int = 5, reset_timeout: float = 60.0):
    """
    Decorator to wrap a function with a circuit breaker.

    Args:
        name: Circuit breaker name
        fail_max: Failure threshold
        reset_timeout: Reset timeout in seconds

    Returns:
        Decorated function

    Usage:
        @circuit_breaker("plex", fail_max=5, reset_timeout=60)
        def call_plex_api():
            # API call
    """
    def decorator(func: Callable) -> Callable:
        cb = get_circuit_breaker(name, fail_max, reset_timeout)

        @wraps(func)
        def wrapper(*args, **kwargs):
            if PYBREAKER_AVAILABLE:
                return cb.call(func, *args, **kwargs)
            else:
                return cb.call(func, *args, **kwargs)

        # Attach circuit breaker for inspection
        wrapper.circuit_breaker = cb
        return wrapper

    return decorator


def with_circuit_breaker(cb, func: Callable, *args, **kwargs) -> Any:
    """
    Execute a function with circuit breaker protection.

    Args:
        cb: Circuit breaker instance
        func: Function to execute
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Function result
    """
    if PYBREAKER_AVAILABLE:
        return cb.call(func, *args, **kwargs)
    else:
        return cb.call(func, *args, **kwargs)
