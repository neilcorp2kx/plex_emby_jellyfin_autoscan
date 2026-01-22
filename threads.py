"""
Thread management module with bounded thread pool and graceful shutdown support.

This module provides:
- BoundedThreadPool: Enterprise-grade thread pool with backpressure and graceful shutdown
- PriorityLock: Priority-based mutex for fair thread scheduling
- Thread: Legacy thread wrapper (deprecated, use BoundedThreadPool instead)
"""

import queue
import datetime
import copy
import threading
import logging
import os
from concurrent.futures import ThreadPoolExecutor, Future, wait, FIRST_COMPLETED
from typing import Callable, Optional, List, Any

logger = logging.getLogger("THREADS")


class PriorityLock:
    def __init__(self):
        self._is_available = True
        self._mutex = threading.Lock()
        self._waiter_queue = queue.PriorityQueue()

    def acquire(self, priority=0):
        self._mutex.acquire()
        # First, just check the lock.
        if self._is_available:
            self._is_available = False
            self._mutex.release()
            return True
        event = threading.Event()
        self._waiter_queue.put((priority, datetime.datetime.now(), event))
        self._mutex.release()
        event.wait()
        # When the event is triggered, we have the lock.
        return True

    def release(self):
        self._mutex.acquire()
        # Notify the next thread in line, if any.
        try:
            _, timeAdded, event = self._waiter_queue.get_nowait()
        except queue.Empty:
            self._is_available = True
        else:
            event.set()
        self._mutex.release()


class Thread:
    def __init__(self):
        self.threads = []

    def start(self, target, name=None, args=None, track=False):
        thread = threading.Thread(target=target, name=name, args=args if args else [])
        thread.daemon = True
        thread.start()
        if track:
            self.threads.append(thread)
        return thread

    def join(self):
        for thread in copy.copy(self.threads):
            thread.join()
            self.threads.remove(thread)
        return

    def kill(self):
        for thread in copy.copy(self.threads):
            thread.kill()
            self.threads.remove(thread)
        return


class BoundedThreadPool:
    """
    Enterprise-grade thread pool with bounded workers and graceful shutdown.

    Features:
    - Bounded worker count to prevent resource exhaustion
    - Graceful shutdown with configurable timeout
    - Backpressure when shutdown is in progress
    - Task tracking and cleanup
    - Queue depth monitoring for backpressure visibility

    Usage:
        pool = BoundedThreadPool(max_workers=10)
        pool.submit(some_function, arg1, arg2)
        # On shutdown:
        pool.shutdown(wait=True, timeout=30.0)
    """

    def __init__(self, max_workers: Optional[int] = None, thread_name_prefix: str = "scan",
                 shutdown_timeout: Optional[float] = None, task_timeout: Optional[float] = None):
        """
        Initialize the thread pool.

        Args:
            max_workers: Maximum number of worker threads. Defaults to SCAN_THREAD_POOL_SIZE
                        env var or 10 if not set.
            thread_name_prefix: Prefix for worker thread names.
            shutdown_timeout: Default timeout for shutdown operations. Defaults to
                             SCAN_SHUTDOWN_TIMEOUT env var or 30.0 seconds.
            task_timeout: Default timeout for individual tasks in join(). Defaults to
                         SCAN_TASK_TIMEOUT env var or 300.0 seconds.
        """
        if max_workers is None:
            max_workers = int(os.getenv('SCAN_THREAD_POOL_SIZE', '10'))
        if shutdown_timeout is None:
            shutdown_timeout = float(os.getenv('SCAN_SHUTDOWN_TIMEOUT', '30.0'))
        if task_timeout is None:
            task_timeout = float(os.getenv('SCAN_TASK_TIMEOUT', '300.0'))

        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix
        )
        self._futures: List[Future] = []
        self._shutdown_event = threading.Event()
        self._lock = threading.Lock()
        self._max_workers = max_workers
        self._shutdown_timeout = shutdown_timeout
        self._task_timeout = task_timeout
        logger.info("BoundedThreadPool initialized with max_workers=%d, shutdown_timeout=%.1fs, task_timeout=%.1fs",
                    max_workers, shutdown_timeout, task_timeout)

    def submit(self, fn: Callable, *args, **kwargs) -> Optional[Future]:
        """
        Submit a task to the thread pool.

        Args:
            fn: The function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Future object if submitted, None if shutdown is in progress or pool is closed
        """
        # Use lock to prevent race condition between shutdown check and submit
        with self._lock:
            if self._shutdown_event.is_set():
                logger.warning("Rejecting task '%s', shutdown in progress", fn.__name__)
                return None

            try:
                future = self._executor.submit(fn, *args, **kwargs)
                self._futures.append(future)
                future.add_done_callback(self._cleanup_future)
                logger.debug("Task '%s' submitted to thread pool (queue depth: %d)",
                            fn.__name__, len(self._futures))
                return future
            except RuntimeError as e:
                logger.error("Failed to submit task '%s': %s", fn.__name__, e)
                return None

    def _cleanup_future(self, future: Future) -> None:
        """Remove completed future from tracking list."""
        try:
            with self._lock:
                if future in self._futures:
                    self._futures.remove(future)
        except Exception as e:
            # Log but don't raise - this is a callback and shouldn't break the caller
            logger.warning("Error cleaning up future: %s", e)

    def shutdown(self, wait: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Gracefully shutdown the thread pool.

        Args:
            wait: If True, wait for pending tasks to complete
            timeout: Maximum seconds to wait for completion. If None, uses default
                    from initialization. If tasks don't complete within timeout,
                    they will be cancelled.

        Returns:
            True if shutdown completed cleanly, False if timeout occurred
        """
        if timeout is None:
            timeout = self._shutdown_timeout

        self._shutdown_event.set()
        logger.info("Initiating graceful shutdown (wait=%s, timeout=%.1fs)...", wait, timeout)

        with self._lock:
            pending_futures = list(self._futures)
        pending_count = len(pending_futures)

        if pending_count > 0 and wait:
            logger.info("Waiting for %d pending task(s) to complete...", pending_count)

            # Wait for futures with actual timeout enforcement
            done, not_done = wait(pending_futures, timeout=timeout, return_when=FIRST_COMPLETED)

            # Keep waiting until all done or timeout
            remaining_timeout = timeout
            start_time = datetime.datetime.now()
            while not_done and remaining_timeout > 0:
                done, not_done = wait(not_done, timeout=remaining_timeout, return_when=FIRST_COMPLETED)
                elapsed = (datetime.datetime.now() - start_time).total_seconds()
                remaining_timeout = timeout - elapsed

            if not_done:
                logger.warning("Timeout reached with %d task(s) still running, cancelling...", len(not_done))
                for future in not_done:
                    future.cancel()
                clean_shutdown = False
            else:
                clean_shutdown = True
        else:
            clean_shutdown = True

        try:
            self._executor.shutdown(wait=wait, cancel_futures=not wait)
            logger.info("Thread pool shutdown complete")
        except Exception as e:
            logger.error("Error during thread pool shutdown: %s", e)
            clean_shutdown = False

        return clean_shutdown

    def is_shutting_down(self) -> bool:
        """Check if shutdown has been initiated."""
        return self._shutdown_event.is_set()

    @property
    def active_count(self) -> int:
        """Return the number of active (pending) tasks."""
        with self._lock:
            return len(self._futures)

    @property
    def queue_depth(self) -> int:
        """
        Return the current queue depth (same as active_count).

        Use this to monitor backpressure - if queue_depth approaches
        max_workers consistently, consider increasing pool size or
        reducing task submission rate.
        """
        return self.active_count

    @property
    def max_workers(self) -> int:
        """Return the maximum number of workers."""
        return self._max_workers

    def is_at_capacity(self) -> bool:
        """
        Check if the thread pool is at capacity.

        Returns:
            True if all workers are busy (queue_depth >= max_workers)
        """
        return self.active_count >= self._max_workers

    def get_stats(self) -> dict:
        """
        Get thread pool statistics for monitoring.

        Returns:
            Dictionary with pool statistics
        """
        with self._lock:
            return {
                'max_workers': self._max_workers,
                'active_count': len(self._futures),
                'is_at_capacity': len(self._futures) >= self._max_workers,
                'is_shutting_down': self._shutdown_event.is_set(),
                'shutdown_timeout': self._shutdown_timeout,
                'task_timeout': self._task_timeout
            }

    # Compatibility methods for legacy Thread class interface
    def start(self, target: Callable, name: Optional[str] = None,
              args: Optional[tuple] = None, track: bool = False) -> Optional[Future]:
        """
        Legacy compatibility method - wraps submit().

        This method provides backward compatibility with the Thread class interface.
        New code should use submit() directly.
        """
        if args is None:
            args = ()
        return self.submit(target, *args)

    def join(self, timeout: Optional[float] = None) -> None:
        """
        Legacy compatibility method - waits for all tasks to complete.

        This method provides backward compatibility with the Thread class interface.
        New code should use shutdown() instead.

        Args:
            timeout: Timeout per task in seconds. If None, uses default task_timeout.
        """
        if timeout is None:
            timeout = self._task_timeout

        logger.debug("join() called - waiting for all tasks to complete (timeout=%.1fs per task)", timeout)
        # Wait for all current futures to complete
        with self._lock:
            futures_copy = list(self._futures)

        for future in futures_copy:
            try:
                future.result(timeout=timeout)
            except Exception as e:
                logger.warning("Task raised exception during join: %s", e)
