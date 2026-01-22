"""
Unit tests for the circuit breaker module.

Tests cover circuit breaker states, transitions, and failure handling.
"""

import pytest
import time
from unittest.mock import Mock, patch


class TestFallbackCircuitBreaker:
    """Tests for the FallbackCircuitBreaker implementation."""

    def test_initial_state_is_closed(self):
        """Test that circuit breaker starts in CLOSED state."""
        from app.circuit_breaker import FallbackCircuitBreaker, CircuitState

        cb = FallbackCircuitBreaker(name="test", fail_max=3, reset_timeout=60)
        assert cb.state == CircuitState.CLOSED

    def test_successful_calls_keep_circuit_closed(self):
        """Test that successful calls keep the circuit closed."""
        from app.circuit_breaker import FallbackCircuitBreaker, CircuitState

        cb = FallbackCircuitBreaker(name="test", fail_max=3, reset_timeout=60)

        for _ in range(10):
            result = cb.call(lambda: "success")
            assert result == "success"

        assert cb.state == CircuitState.CLOSED

    def test_failures_increment_counter(self):
        """Test that failures increment the failure counter."""
        from app.circuit_breaker import FallbackCircuitBreaker

        cb = FallbackCircuitBreaker(name="test", fail_max=5, reset_timeout=60)

        def failing_func():
            raise ValueError("Test error")

        # Fail twice
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(failing_func)

        stats = cb.get_stats()
        assert stats.failure_count == 2
        assert stats.total_failures == 2

    def test_circuit_opens_after_fail_max(self):
        """Test that circuit opens after fail_max failures."""
        from app.circuit_breaker import FallbackCircuitBreaker, CircuitState

        cb = FallbackCircuitBreaker(name="test", fail_max=3, reset_timeout=60)

        def failing_func():
            raise ValueError("Test error")

        # Fail 3 times to open circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

    def test_open_circuit_fails_fast(self):
        """Test that open circuit rejects calls immediately."""
        from app.circuit_breaker import FallbackCircuitBreaker, CircuitBreakerError, CircuitState

        cb = FallbackCircuitBreaker(name="test", fail_max=2, reset_timeout=60)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

        assert cb.state == CircuitState.OPEN

        # New calls should fail fast with CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            cb.call(lambda: "should not execute")

    def test_circuit_transitions_to_half_open_after_timeout(self):
        """Test that circuit transitions to HALF-OPEN after reset_timeout."""
        from app.circuit_breaker import FallbackCircuitBreaker, CircuitState

        cb = FallbackCircuitBreaker(name="test", fail_max=2, reset_timeout=0.1)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

        assert cb.state == CircuitState.OPEN

        # Wait for reset timeout
        time.sleep(0.15)

        # Should transition to HALF-OPEN
        assert cb.state == CircuitState.HALF_OPEN

    def test_successful_call_in_half_open_closes_circuit(self):
        """Test that successful call in HALF-OPEN state closes the circuit."""
        from app.circuit_breaker import FallbackCircuitBreaker, CircuitState

        cb = FallbackCircuitBreaker(name="test", fail_max=2, reset_timeout=0.1)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

        # Wait for HALF-OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        # Successful call should close circuit
        result = cb.call(lambda: "success")
        assert result == "success"
        assert cb.state == CircuitState.CLOSED

    def test_failure_in_half_open_reopens_circuit(self):
        """Test that failure in HALF-OPEN state reopens the circuit."""
        from app.circuit_breaker import FallbackCircuitBreaker, CircuitState

        cb = FallbackCircuitBreaker(name="test", fail_max=2, reset_timeout=0.1)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

        # Wait for HALF-OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        # Failure should reopen circuit
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail again")))

        assert cb.state == CircuitState.OPEN

    def test_excluded_exceptions_dont_count_as_failures(self):
        """Test that excluded exceptions don't count toward failure threshold."""
        from app.circuit_breaker import FallbackCircuitBreaker, CircuitState

        cb = FallbackCircuitBreaker(
            name="test",
            fail_max=2,
            reset_timeout=60,
            exclude=(KeyError,)
        )

        # KeyError should not count as failure
        for _ in range(5):
            with pytest.raises(KeyError):
                cb.call(lambda: (_ for _ in ()).throw(KeyError("excluded")))

        # Circuit should still be closed
        assert cb.state == CircuitState.CLOSED

        # But ValueError should count
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("not excluded")))

        assert cb.state == CircuitState.OPEN

    def test_manual_reset(self):
        """Test that manual reset closes the circuit."""
        from app.circuit_breaker import FallbackCircuitBreaker, CircuitState

        cb = FallbackCircuitBreaker(name="test", fail_max=2, reset_timeout=60)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

        assert cb.state == CircuitState.OPEN

        # Manual reset
        cb.reset()
        assert cb.state == CircuitState.CLOSED

    def test_get_stats_returns_correct_values(self):
        """Test that get_stats returns accurate statistics."""
        from app.circuit_breaker import FallbackCircuitBreaker

        cb = FallbackCircuitBreaker(name="test_stats", fail_max=5, reset_timeout=60)

        # Some successful calls
        for _ in range(3):
            cb.call(lambda: "success")

        # Some failures
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

        stats = cb.get_stats()
        assert stats.name == "test_stats"
        assert stats.success_count == 3
        assert stats.failure_count == 2
        assert stats.total_calls == 5
        assert stats.total_failures == 2


class TestCircuitBreakerRegistry:
    """Tests for circuit breaker registry functions."""

    def test_get_circuit_breaker_creates_new(self):
        """Test that get_circuit_breaker creates new breakers."""
        from app.circuit_breaker import get_circuit_breaker, _circuit_breakers

        # Clear registry first
        _circuit_breakers.clear()

        cb = get_circuit_breaker("new_test_cb", fail_max=5)
        assert cb is not None
        assert "new_test_cb" in _circuit_breakers

    def test_get_circuit_breaker_returns_existing(self):
        """Test that get_circuit_breaker returns existing breaker."""
        from app.circuit_breaker import get_circuit_breaker

        cb1 = get_circuit_breaker("shared_cb")
        cb2 = get_circuit_breaker("shared_cb")

        assert cb1 is cb2

    def test_get_all_circuit_breakers(self):
        """Test that get_all_circuit_breakers returns all breakers."""
        from app.circuit_breaker import get_circuit_breaker, get_all_circuit_breakers, _circuit_breakers

        _circuit_breakers.clear()

        get_circuit_breaker("cb1")
        get_circuit_breaker("cb2")
        get_circuit_breaker("cb3")

        all_cbs = get_all_circuit_breakers()
        assert len(all_cbs) == 3
        assert "cb1" in all_cbs
        assert "cb2" in all_cbs
        assert "cb3" in all_cbs

    def test_get_circuit_breaker_stats(self):
        """Test that get_circuit_breaker_stats returns stats for all breakers."""
        from app.circuit_breaker import (
            get_circuit_breaker, get_circuit_breaker_stats, _circuit_breakers
        )

        _circuit_breakers.clear()

        cb1 = get_circuit_breaker("stats_cb1")
        cb2 = get_circuit_breaker("stats_cb2")

        # Make some calls
        cb1.call(lambda: "success")

        stats = get_circuit_breaker_stats()
        assert len(stats) == 2

        names = [s['name'] for s in stats]
        assert "stats_cb1" in names
        assert "stats_cb2" in names


class TestCircuitBreakerDecorator:
    """Tests for the circuit_breaker decorator."""

    def test_decorator_wraps_function(self):
        """Test that decorator wraps function with circuit breaker."""
        from app.circuit_breaker import circuit_breaker, _circuit_breakers

        _circuit_breakers.clear()

        @circuit_breaker("decorator_test", fail_max=3)
        def my_function():
            return "result"

        result = my_function()
        assert result == "result"
        assert hasattr(my_function, 'circuit_breaker')

    def test_decorator_handles_failures(self):
        """Test that decorated function failures affect circuit."""
        from app.circuit_breaker import circuit_breaker, CircuitBreakerError, _circuit_breakers

        _circuit_breakers.clear()

        call_count = 0

        @circuit_breaker("fail_decorator_test", fail_max=2, reset_timeout=60)
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        # Fail twice to open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                failing_function()

        # Circuit should be open, fail fast
        with pytest.raises(CircuitBreakerError):
            failing_function()

        # Function should have been called only twice
        assert call_count == 2


class TestWithCircuitBreaker:
    """Tests for the with_circuit_breaker function."""

    def test_with_circuit_breaker_executes_function(self):
        """Test that with_circuit_breaker executes the function."""
        from app.circuit_breaker import FallbackCircuitBreaker, with_circuit_breaker

        cb = FallbackCircuitBreaker(name="with_cb_test", fail_max=3)

        result = with_circuit_breaker(cb, lambda: "executed")
        assert result == "executed"

    def test_with_circuit_breaker_passes_args(self):
        """Test that with_circuit_breaker passes args and kwargs."""
        from app.circuit_breaker import FallbackCircuitBreaker, with_circuit_breaker

        cb = FallbackCircuitBreaker(name="args_test", fail_max=3)

        def add(a, b):
            return a + b

        result = with_circuit_breaker(cb, add, 2, 3)
        assert result == 5


class TestServiceCircuitBreakers:
    """Tests for pre-configured service circuit breakers."""

    def test_get_plex_circuit_breaker(self):
        """Test that Plex circuit breaker is configured correctly."""
        from app.circuit_breaker import get_plex_circuit_breaker, _circuit_breakers

        _circuit_breakers.clear()

        cb = get_plex_circuit_breaker()
        assert cb is not None
        assert "plex" in _circuit_breakers

    def test_get_jellyfin_circuit_breaker(self):
        """Test that Jellyfin circuit breaker is configured correctly."""
        from app.circuit_breaker import get_jellyfin_circuit_breaker, _circuit_breakers

        _circuit_breakers.clear()

        cb = get_jellyfin_circuit_breaker()
        assert cb is not None
        assert "jellyfin" in _circuit_breakers

    def test_get_google_circuit_breaker(self):
        """Test that Google circuit breaker is configured correctly."""
        from app.circuit_breaker import get_google_circuit_breaker, _circuit_breakers

        _circuit_breakers.clear()

        cb = get_google_circuit_breaker()
        assert cb is not None
        assert "google" in _circuit_breakers
