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
from concurrent.futures import ThreadPoolExecutor, Future
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

    Usage:
        pool = BoundedThreadPool(max_workers=10)
        pool.submit(some_function, arg1, arg2)
        # On shutdown:
        pool.shutdown(wait=True, timeout=30.0)
    """

    def __init__(self, max_workers: Optional[int] = None, thread_name_prefix: str = "scan"):
        """
        Initialize the thread pool.

        Args:
            max_workers: Maximum number of worker threads. Defaults to SCAN_THREAD_POOL_SIZE
                        env var or 10 if not set.
            thread_name_prefix: Prefix for worker thread names.
        """
        if max_workers is None:
            max_workers = int(os.getenv('SCAN_THREAD_POOL_SIZE', '10'))

        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix
        )
        self._futures: List[Future] = []
        self._shutdown_event = threading.Event()
        self._lock = threading.Lock()
        self._max_workers = max_workers
        logger.info("BoundedThreadPool initialized with max_workers=%d", max_workers)

    def submit(self, fn: Callable, *args, **kwargs) -> Optional[Future]:
        """
        Submit a task to the thread pool.

        Args:
            fn: The function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Future object if submitted, None if shutdown is in progress
        """
        if self._shutdown_event.is_set():
            logger.warning("Rejecting task '%s', shutdown in progress", fn.__name__)
            return None

        try:
            future = self._executor.submit(fn, *args, **kwargs)
            with self._lock:
                self._futures.append(future)
            future.add_done_callback(self._cleanup_future)
            logger.debug("Task '%s' submitted to thread pool", fn.__name__)
            return future
        except RuntimeError as e:
            logger.error("Failed to submit task '%s': %s", fn.__name__, e)
            return None

    def _cleanup_future(self, future: Future) -> None:
        """Remove completed future from tracking list."""
        with self._lock:
            if future in self._futures:
                self._futures.remove(future)

    def shutdown(self, wait: bool = True, timeout: float = 30.0) -> None:
        """
        Gracefully shutdown the thread pool.

        Args:
            wait: If True, wait for pending tasks to complete
            timeout: Maximum seconds to wait for completion (used for logging only,
                    ThreadPoolExecutor.shutdown doesn't support timeout directly)
        """
        self._shutdown_event.set()
        logger.info("Initiating graceful shutdown (wait=%s, timeout=%.1fs)...", wait, timeout)

        pending_count = len(self._futures)
        if pending_count > 0:
            logger.info("Waiting for %d pending task(s) to complete...", pending_count)

        try:
            self._executor.shutdown(wait=wait, cancel_futures=not wait)
            logger.info("Thread pool shutdown complete")
        except Exception as e:
            logger.error("Error during thread pool shutdown: %s", e)

    def is_shutting_down(self) -> bool:
        """Check if shutdown has been initiated."""
        return self._shutdown_event.is_set()

    @property
    def active_count(self) -> int:
        """Return the number of active (pending) tasks."""
        with self._lock:
            return len(self._futures)

    @property
    def max_workers(self) -> int:
        """Return the maximum number of workers."""
        return self._max_workers

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

    def join(self) -> None:
        """
        Legacy compatibility method - waits for all tasks to complete.

        This method provides backward compatibility with the Thread class interface.
        New code should use shutdown() instead.
        """
        logger.debug("join() called - waiting for all tasks to complete")
        # Wait for all current futures to complete
        with self._lock:
            futures_copy = list(self._futures)

        for future in futures_copy:
            try:
                future.result(timeout=300)  # 5 minute timeout per task
            except Exception as e:
                logger.warning("Task raised exception during join: %s", e)
