"""
Essential unit tests for the circuit breaker module.
"""

import pytest
import time


class TestCircuitBreaker:
    """Core circuit breaker tests."""

    def test_initial_state_closed(self):
        """Test that circuit starts closed."""
        from app.circuit_breaker import FallbackCircuitBreaker, CircuitState
        cb = FallbackCircuitBreaker(name="test", fail_max=3, reset_timeout=60)
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_failures(self):
        """Test that circuit opens after max failures."""
        from app.circuit_breaker import FallbackCircuitBreaker, CircuitState
        cb = FallbackCircuitBreaker(name="test", fail_max=2, reset_timeout=60)

        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

        assert cb.state == CircuitState.OPEN

    def test_open_circuit_fails_fast(self):
        """Test that open circuit rejects calls immediately."""
        from app.circuit_breaker import FallbackCircuitBreaker, CircuitBreakerError, CircuitState
        cb = FallbackCircuitBreaker(name="test", fail_max=2, reset_timeout=60)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

        # Should fail fast
        with pytest.raises(CircuitBreakerError):
            cb.call(lambda: "should not run")

    def test_manual_reset(self):
        """Test that manual reset closes circuit."""
        from app.circuit_breaker import FallbackCircuitBreaker, CircuitState
        cb = FallbackCircuitBreaker(name="test", fail_max=2, reset_timeout=60)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

        cb.reset()
        assert cb.state == CircuitState.CLOSED
