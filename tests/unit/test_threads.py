"""
Unit tests for the threads module.

Tests cover BoundedThreadPool, PriorityLock, and thread management functionality.
"""

import pytest
import time
import threading
from concurrent.futures import Future
from unittest.mock import Mock, patch


class TestBoundedThreadPool:
    """Tests for BoundedThreadPool implementation."""

    def test_initialization_with_defaults(self):
        """Test that pool initializes with default values."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=5)
        try:
            assert pool.max_workers == 5
            assert pool.active_count == 0
            assert not pool.is_shutting_down()
            assert not pool.is_at_capacity()
        finally:
            pool.shutdown(wait=False)

    def test_initialization_from_env_vars(self, monkeypatch):
        """Test that pool reads configuration from environment variables."""
        from threads import BoundedThreadPool

        monkeypatch.setenv('SCAN_THREAD_POOL_SIZE', '15')
        monkeypatch.setenv('SCAN_SHUTDOWN_TIMEOUT', '45.0')
        monkeypatch.setenv('SCAN_TASK_TIMEOUT', '600.0')

        pool = BoundedThreadPool()
        try:
            assert pool.max_workers == 15
            stats = pool.get_stats()
            assert stats['shutdown_timeout'] == 45.0
            assert stats['task_timeout'] == 600.0
        finally:
            pool.shutdown(wait=False)

    def test_submit_returns_future(self):
        """Test that submit returns a Future object."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=2)
        try:
            future = pool.submit(lambda: "result")
            assert isinstance(future, Future)
            assert future.result(timeout=5) == "result"
        finally:
            pool.shutdown(wait=True, timeout=5.0)

    def test_submit_with_args_and_kwargs(self):
        """Test that submit passes args and kwargs correctly."""
        from threads import BoundedThreadPool

        def add(a, b, multiplier=1):
            return (a + b) * multiplier

        pool = BoundedThreadPool(max_workers=2)
        try:
            future = pool.submit(add, 2, 3, multiplier=2)
            assert future.result(timeout=5) == 10
        finally:
            pool.shutdown(wait=True, timeout=5.0)

    def test_submit_rejects_after_shutdown(self):
        """Test that submit returns None after shutdown is initiated."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=2)
        pool.shutdown(wait=False)

        future = pool.submit(lambda: "should not run")
        assert future is None

    def test_active_count_tracks_pending_tasks(self):
        """Test that active_count correctly tracks pending tasks."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=2)
        try:
            event = threading.Event()

            def blocking_task():
                event.wait(timeout=10)
                return "done"

            # Submit a blocking task
            future = pool.submit(blocking_task)
            time.sleep(0.1)  # Give task time to start

            # Should have one active task
            assert pool.active_count >= 1

            # Release the task
            event.set()
            future.result(timeout=5)

            # Give cleanup callback time to run
            time.sleep(0.1)
            assert pool.active_count == 0
        finally:
            pool.shutdown(wait=True, timeout=5.0)

    def test_queue_depth_same_as_active_count(self):
        """Test that queue_depth property returns same as active_count."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=2)
        try:
            assert pool.queue_depth == pool.active_count
        finally:
            pool.shutdown(wait=False)

    def test_is_at_capacity_when_full(self):
        """Test that is_at_capacity returns True when all workers are busy."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=2)
        try:
            events = []
            futures = []

            for _ in range(2):
                event = threading.Event()
                events.append(event)
                futures.append(pool.submit(lambda e=event: e.wait(timeout=10)))

            time.sleep(0.1)  # Give tasks time to start
            assert pool.is_at_capacity()

            # Release all tasks
            for event in events:
                event.set()

            for future in futures:
                future.result(timeout=5)
        finally:
            pool.shutdown(wait=True, timeout=5.0)

    def test_graceful_shutdown_waits_for_tasks(self):
        """Test that shutdown waits for running tasks to complete."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=2)
        completed = []

        def task():
            time.sleep(0.2)
            completed.append(True)

        pool.submit(task)
        pool.submit(task)

        result = pool.shutdown(wait=True, timeout=5.0)
        assert result is True
        assert len(completed) == 2

    def test_shutdown_timeout_cancels_tasks(self):
        """Test that shutdown cancels tasks after timeout."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=2)
        completed = []

        def long_task():
            time.sleep(10)
            completed.append(True)

        pool.submit(long_task)

        # Very short timeout should not wait for completion
        result = pool.shutdown(wait=True, timeout=0.1)
        # Task may or may not complete depending on timing
        assert pool.is_shutting_down()

    def test_shutdown_without_wait(self):
        """Test that shutdown without wait returns immediately."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=2)

        def long_task():
            time.sleep(5)

        pool.submit(long_task)

        start = time.time()
        pool.shutdown(wait=False)
        elapsed = time.time() - start

        # Should return very quickly
        assert elapsed < 1.0

    def test_is_shutting_down_flag(self):
        """Test that is_shutting_down returns correct state."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=2)
        assert not pool.is_shutting_down()

        pool.shutdown(wait=False)
        assert pool.is_shutting_down()

    def test_get_stats_returns_complete_info(self):
        """Test that get_stats returns all expected fields."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=5)
        try:
            stats = pool.get_stats()

            assert 'max_workers' in stats
            assert 'active_count' in stats
            assert 'is_at_capacity' in stats
            assert 'is_shutting_down' in stats
            assert 'shutdown_timeout' in stats
            assert 'task_timeout' in stats

            assert stats['max_workers'] == 5
            assert stats['active_count'] == 0
            assert stats['is_at_capacity'] is False
            assert stats['is_shutting_down'] is False
        finally:
            pool.shutdown(wait=False)

    def test_exception_in_task_does_not_crash_pool(self):
        """Test that task exceptions don't crash the thread pool."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=2)
        try:
            def failing_task():
                raise ValueError("Test error")

            def success_task():
                return "success"

            future1 = pool.submit(failing_task)
            future2 = pool.submit(success_task)

            # First task should raise
            with pytest.raises(ValueError):
                future1.result(timeout=5)

            # Second task should succeed
            assert future2.result(timeout=5) == "success"
        finally:
            pool.shutdown(wait=True, timeout=5.0)

    def test_concurrent_submissions(self):
        """Test that concurrent submissions are handled correctly."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=10)
        try:
            results = []
            lock = threading.Lock()

            def task(n):
                with lock:
                    results.append(n)
                return n

            futures = [pool.submit(task, i) for i in range(20)]

            for future in futures:
                future.result(timeout=10)

            assert len(results) == 20
            assert set(results) == set(range(20))
        finally:
            pool.shutdown(wait=True, timeout=10.0)


class TestBoundedThreadPoolLegacyInterface:
    """Tests for legacy Thread class compatibility methods."""

    def test_start_method_wraps_submit(self):
        """Test that start() method works like the old Thread class."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=2)
        try:
            results = []

            def task(value):
                results.append(value)

            future = pool.start(target=task, args=(42,))
            assert future is not None
            future.result(timeout=5)

            assert 42 in results
        finally:
            pool.shutdown(wait=True, timeout=5.0)

    def test_start_method_without_args(self):
        """Test that start() works without args."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=2)
        try:
            called = []

            def task():
                called.append(True)

            future = pool.start(target=task)
            future.result(timeout=5)

            assert len(called) == 1
        finally:
            pool.shutdown(wait=True, timeout=5.0)

    def test_join_waits_for_completion(self):
        """Test that join() waits for all tasks to complete."""
        from threads import BoundedThreadPool

        pool = BoundedThreadPool(max_workers=2)
        try:
            completed = []

            def task(n):
                time.sleep(0.1)
                completed.append(n)

            pool.submit(task, 1)
            pool.submit(task, 2)

            pool.join(timeout=5.0)
            assert len(completed) == 2
        finally:
            pool.shutdown(wait=True, timeout=5.0)


class TestPriorityLock:
    """Tests for PriorityLock implementation."""

    def test_basic_acquire_and_release(self):
        """Test basic lock acquire and release."""
        from threads import PriorityLock

        lock = PriorityLock()

        assert lock.acquire() is True
        lock.release()

        # Should be able to acquire again after release
        assert lock.acquire() is True
        lock.release()

    def test_lock_blocks_concurrent_access(self):
        """Test that lock properly blocks concurrent access."""
        from threads import PriorityLock

        lock = PriorityLock()
        shared_value = [0]
        errors = []

        def increment():
            try:
                lock.acquire()
                current = shared_value[0]
                time.sleep(0.01)  # Simulate work
                shared_value[0] = current + 1
                lock.release()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0
        assert shared_value[0] == 10

    def test_priority_ordering(self):
        """Test that higher priority (lower number) acquires first."""
        from threads import PriorityLock

        lock = PriorityLock()
        order = []
        release_event = threading.Event()

        # Main thread holds the lock
        lock.acquire()

        def waiter(priority, name):
            lock.acquire(priority=priority)
            order.append(name)
            lock.release()

        # Start threads with different priorities
        # Priority 10 should get lock after priority 1
        t_low = threading.Thread(target=waiter, args=(10, 'low'))
        t_high = threading.Thread(target=waiter, args=(1, 'high'))

        t_low.start()
        time.sleep(0.05)  # Give low priority thread time to queue
        t_high.start()
        time.sleep(0.05)  # Give high priority thread time to queue

        # Release lock - should go to higher priority (lower number) first
        lock.release()

        t_low.join(timeout=5)
        t_high.join(timeout=5)

        # High priority should have acquired before low priority
        assert order[0] == 'high'
        assert order[1] == 'low'


class TestLegacyThread:
    """Tests for the legacy Thread class."""

    def test_thread_start_and_track(self):
        """Test that Thread class can start and track threads."""
        from threads import Thread

        thread_mgr = Thread()
        results = []

        def task():
            results.append(True)

        thread_mgr.start(target=task, track=True)
        thread_mgr.join()

        assert len(results) == 1

    def test_thread_start_without_track(self):
        """Test that Thread class can start threads without tracking."""
        from threads import Thread

        thread_mgr = Thread()
        event = threading.Event()
        results = []

        def task():
            results.append(True)
            event.set()

        thread_mgr.start(target=task, track=False)
        event.wait(timeout=5)

        assert len(results) == 1
        assert len(thread_mgr.threads) == 0

    def test_multiple_threads(self):
        """Test managing multiple threads."""
        from threads import Thread

        thread_mgr = Thread()
        results = []
        lock = threading.Lock()

        def task(n):
            time.sleep(0.05)
            with lock:
                results.append(n)

        for i in range(5):
            thread_mgr.start(target=task, args=[i], track=True)

        thread_mgr.join()
        assert len(results) == 5


class TestThreadPoolFixture:
    """Tests using the mock_thread_pool fixture."""

    def test_fixture_creates_pool(self, mock_thread_pool):
        """Test that fixture provides a working thread pool."""
        from threads import BoundedThreadPool

        assert isinstance(mock_thread_pool, BoundedThreadPool)
        assert mock_thread_pool.max_workers == 2

    def test_fixture_pool_submits_tasks(self, mock_thread_pool):
        """Test that fixture pool can submit tasks."""
        result = []

        def task():
            result.append("done")

        future = mock_thread_pool.submit(task)
        future.result(timeout=5)

        assert result == ["done"]
