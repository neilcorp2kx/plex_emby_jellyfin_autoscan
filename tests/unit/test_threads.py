"""
Essential unit tests for the threads module.
"""

import pytest
import threading
from concurrent.futures import Future


class TestBoundedThreadPool:
    """Core thread pool tests."""

    def test_initialization(self):
        """Test that pool initializes correctly."""
        from threads import BoundedThreadPool
        pool = BoundedThreadPool(max_workers=5)
        try:
            assert pool.max_workers == 5
            assert not pool.is_shutting_down()
        finally:
            pool.shutdown(wait=False)

    def test_submit_returns_future(self):
        """Test that submit returns a Future."""
        from threads import BoundedThreadPool
        pool = BoundedThreadPool(max_workers=2)
        try:
            future = pool.submit(lambda: "result")
            assert isinstance(future, Future)
            assert future.result(timeout=5) == "result"
        finally:
            pool.shutdown(wait=True, timeout=5.0)

    def test_rejects_after_shutdown(self):
        """Test that submit returns None after shutdown."""
        from threads import BoundedThreadPool
        pool = BoundedThreadPool(max_workers=2)
        pool.shutdown(wait=False)
        future = pool.submit(lambda: "should not run")
        assert future is None

    def test_graceful_shutdown(self):
        """Test that shutdown waits for tasks."""
        from threads import BoundedThreadPool
        pool = BoundedThreadPool(max_workers=2)
        completed = []

        def task():
            completed.append(True)

        pool.submit(task)
        pool.submit(task)
        pool.shutdown(wait=True, timeout=5.0)

        assert len(completed) == 2
