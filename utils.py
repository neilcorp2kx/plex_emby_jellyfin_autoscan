"""
Utility functions for Plex/Emby/Jellyfin Autoscan.

This module provides:
- retry_with_backoff: Decorator for retrying failed operations with exponential backoff
- OperationTimeout: Context manager for operations with timeout
- Path mapping functions
- Process management utilities
- JSON and database utilities
"""

import json
import logging
import os
import random
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import closing, contextmanager
from copy import copy
from functools import wraps
from typing import Callable, Tuple, Type, Optional, Any, Generator
from urllib.parse import urljoin

import psutil
import requests

logger = logging.getLogger("UTILS")


# =============================================================================
# Retry and Timeout Utilities
# =============================================================================

class RetryExhausted(Exception):
    """Raised when all retry attempts have been exhausted."""
    pass


class OperationTimeoutError(Exception):
    """Raised when an operation times out."""
    pass


def retry_with_backoff(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
) -> Callable:
    """
    Decorator for retrying failed operations with exponential backoff and jitter.

    This implements the "exponential backoff with full jitter" pattern recommended
    by AWS and other cloud providers to prevent thundering herd problems.

    Args:
        max_retries: Maximum number of retry attempts (default: 5)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 60.0)
        exponential_base: Base for exponential calculation (default: 2.0)
        jitter: If True, adds randomization to delays (default: True)
        exceptions: Tuple of exception types to catch and retry (default: all)
        on_retry: Optional callback function(exception, attempt, delay) called before each retry

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
        def fetch_data(url):
            return requests.get(url, timeout=30)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):  # +1 because first attempt is not a retry
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    # If this was the last attempt, don't calculate delay
                    if attempt >= max_retries:
                        break

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)

                    # Add jitter (randomize between 0.5x and 1.5x the delay)
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        "Retry %d/%d for %s after %.2fs delay: %s",
                        attempt + 1, max_retries, func.__name__, delay, str(e)
                    )

                    # Call optional retry callback
                    if on_retry:
                        try:
                            on_retry(e, attempt + 1, delay)
                        except Exception as callback_error:
                            logger.warning("Retry callback error: %s", callback_error)

                    time.sleep(delay)

            # All retries exhausted
            logger.error(
                "All %d retries exhausted for %s: %s",
                max_retries, func.__name__, str(last_exception)
            )
            raise RetryExhausted(
                f"Failed after {max_retries} retries: {last_exception}"
            ) from last_exception

        return wrapper
    return decorator


@contextmanager
def operation_timeout(
    seconds: float,
    operation_name: str = "operation"
) -> Generator[None, None, None]:
    """
    Context manager for operations with a timeout warning.

    Note: This is a cooperative timeout - it doesn't forcibly kill the operation.
    It sets a flag that can be checked periodically within long-running operations.

    Args:
        seconds: Timeout in seconds
        operation_name: Name for logging purposes

    Yields:
        None

    Example:
        with operation_timeout(30.0, "database_query"):
            result = execute_query()
    """
    timeout_occurred = threading.Event()

    def timeout_handler():
        timeout_occurred.set()
        logger.warning(
            "Operation '%s' exceeded %.1fs timeout threshold",
            operation_name, seconds
        )

    timer = threading.Timer(seconds, timeout_handler)
    timer.daemon = True
    timer.start()

    try:
        yield
    finally:
        timer.cancel()
        if timeout_occurred.is_set():
            logger.info("Operation '%s' completed (was flagged as slow)", operation_name)


def with_timeout(
    timeout_seconds: float,
    default: Any = None,
    raise_on_timeout: bool = False
) -> Callable:
    """
    Decorator to add timeout behavior to functions.

    Note: This uses threading and will log a warning if the function takes too long,
    but cannot forcibly terminate the function (Python limitation).

    Args:
        timeout_seconds: Timeout in seconds
        default: Default value to return on timeout (if raise_on_timeout is False)
        raise_on_timeout: If True, raise OperationTimeoutError instead of returning default

    Returns:
        Decorated function

    Example:
        @with_timeout(30.0, default=None, raise_on_timeout=True)
        def slow_operation():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = [default]
            exception = [None]
            completed = threading.Event()

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
                finally:
                    completed.set()

            thread = threading.Thread(target=target, daemon=True)
            thread.start()

            if completed.wait(timeout=timeout_seconds):
                # Completed within timeout
                if exception[0]:
                    raise exception[0]
                return result[0]
            else:
                # Timeout occurred
                logger.warning(
                    "Function '%s' timed out after %.1fs",
                    func.__name__, timeout_seconds
                )
                if raise_on_timeout:
                    raise OperationTimeoutError(
                        f"Function '{func.__name__}' timed out after {timeout_seconds}s"
                    )
                return default

        return wrapper
    return decorator


# =============================================================================
# Original utility functions
# =============================================================================



def get_plex_section(config, path):
    """
    Get Plex library section ID by matching path using Plex API instead of database.
    """
    from xml.etree import ElementTree
    try:
        # Get all library sections from Plex API
        api_url = '%s/library/sections/all?X-Plex-Token=%s' % (
            config['PLEX_LOCAL_URL'],
            config['PLEX_TOKEN']
        )
        
        logger.debug("Requesting library sections from Plex API to map path '%s'", path)
        resp = requests.get(api_url, timeout=30)
        
        if resp.status_code != 200:
            logger.error("Failed to get library sections from Plex API. Status: %d", resp.status_code)
            return -1
            
        # Parse XML response
        root = ElementTree.fromstring(resp.text)
        
        # Iterate through sections and their locations
        for section in root.findall("Directory"):
            section_id = section.get('key')
            section_title = section.get('title')
            
            # Check all location paths for this section
            for location in section.findall("Location"):
                root_path = location.get('path')
                
                # Check if the provided path starts with this library's root path
                if path.startswith(root_path + os.sep) or path.startswith(root_path):
                    logger.debug(
                        "Plex Library Section ID '%s' ('%s') matching root folder '%s' was found via API.",
                        section_id, section_title, root_path
                    )
                    return int(section_id)
        
        logger.error("Unable to map '%s' to a Section ID.", path)
        
    except requests.exceptions.RequestException as e:
        logger.exception("Request exception while trying to map '%s' to a Section ID via Plex API: %s", path, str(e))
    except ElementTree.ParseError as e:
        logger.exception("XML parse error while processing Plex API response: %s", str(e))
    except Exception as e:
        logger.exception("Exception while trying to map '%s' to a Section ID via Plex API: %s", path, str(e))
    
    return -1

def map_pushed_path(config, path):
    for mapped_path, mappings in config['SERVER_PATH_MAPPINGS'].items():
        for mapping in mappings:
            if path.startswith(mapping):
                logger.debug("Mapping server path '%s' to '%s'.", mapping, mapped_path)
                return path.replace(mapping, mapped_path)
    return path


def map_pushed_path_file_exists(config, path):
    for mapped_path, mappings in config['SERVER_FILE_EXIST_PATH_MAPPINGS'].items():
        for mapping in mappings:
            if path.startswith(mapping):
                logger.debug("Mapping file check path '%s' to '%s'.", mapping, mapped_path)
                return path.replace(mapping, mapped_path)
    return path


# For Rclone dir cache clear request
def map_file_exists_path_for_rclone(config, path):
    for mapped_path, mappings in config['RCLONE']['RC_CACHE_REFRESH']['FILE_EXISTS_TO_REMOTE_MAPPINGS'].items():
        for mapping in mappings:
            if path.startswith(mapping):
                logger.debug("Mapping Rclone file check path '%s' to '%s'.", mapping, mapped_path)
                return path.replace(mapping, mapped_path)
    return path


def is_process_running(process_name, plex_container=None):
    try:
        for process in psutil.process_iter():
            if process.name().lower() == process_name.lower():
                if not plex_container:
                    return True, process, plex_container
                # plex_container was not None
                # we need to check if this processes is from the container we are interested in
                get_pid_container = r"docker inspect --format '{{.Name}}' \"$(cat /proc/%s/cgroup |head -n 1 " \
                                    r"|cut -d / -f 3)\" | sed 's/^\///'" % process.pid
                process_container = run_command(get_pid_container, True)
                logger.debug("Using: %s", get_pid_container)
                logger.debug("Docker Container For PID %s: %r", process.pid,
                             process_container.strip() if process_container is not None else 'Unknown???')
                if process_container is not None and isinstance(process_container, str) and \
                        process_container.strip().lower() == plex_container.lower():
                    return True, process, process_container.strip()

        return False, None, plex_container
    except psutil.ZombieProcess:
        return False, None, plex_container
    except Exception:
        logger.exception("Exception checking for process: '%s': ", process_name)
        return False, None, plex_container


def wait_running_process(process_name, use_docker=False, plex_container=None):
    try:
        running, process, container = is_process_running(process_name,
                                                         None if not use_docker or not plex_container else
                                                         plex_container)
        while running and process:
            logger.info("'%s' is running, pid: %d,%s cmdline: %r. Checking again in 60 seconds...", process.name(),
                        process.pid,
                        ' container: %s,' % container.strip() if use_docker and isinstance(container, str) else '',
                        process.cmdline())
            time.sleep(60)
            running, process, container = is_process_running(process_name,
                                                             None if not use_docker or not plex_container else
                                                             plex_container)

        return True

    except Exception:
        logger.exception("Exception waiting for process: '%s'", process_name())

        return False


def run_command(command, get_output=False):
    total_output = ''
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while True:
        output = str(process.stdout.readline()).lstrip('b').replace('\\n', '').strip()
        if output and len(output) >= 3:
            if not get_output:
                if len(output) >= 8:
                    logger.info(output)
            else:
                total_output += output

        if process.poll() is not None:
            break

    rc = process.poll()
    return rc if not get_output else total_output


def should_ignore(file_path, config):
    for item in config['SERVER_IGNORE_LIST']:
        if item.lower() in file_path.lower():
            return True, item

    return False, None


def remove_item_from_list(item, from_list):
    while item in from_list:
        from_list.pop(from_list.index(item))
    return


def get_priority(config, scan_path):
    try:
        for priority, paths in config['SERVER_SCAN_PRIORITIES'].items():
            for path in paths:
                if path.lower() in scan_path.lower():
                    logger.debug("Using priority '%d' for path '%s'", int(priority), scan_path)
                    return int(priority)
        logger.debug("Using default priority '0' for path '%s'", scan_path)
    except Exception:
        logger.exception("Exception determining priority to use for '%s': ", scan_path)
    return 0


def rclone_rc_clear_cache(config, scan_path):
    try:
        rclone_rc_expire_url = urljoin(config['RCLONE']['RC_CACHE_REFRESH']['RC_URL'], 'cache/expire')
        rclone_rc_refresh_url = urljoin(config['RCLONE']['RC_CACHE_REFRESH']['RC_URL'], 'vfs/refresh')

        cache_clear_path = map_file_exists_path_for_rclone(config, scan_path).lstrip(os.path.sep)
        logger.debug("Top level cache_clear_path: '%s'", cache_clear_path)

        while True:
            last_clear_path = cache_clear_path
            cache_clear_path = os.path.dirname(cache_clear_path)
            if cache_clear_path == last_clear_path or not len(cache_clear_path):
                # is the last path we tried to clear, the same as this path, if so, abort
                logger.error("Aborting Rclone dir cache clear request for '%s' due to directory level exhaustion, last level: '%s'",
                             scan_path, last_clear_path)
                return False
            else:
                last_clear_path = cache_clear_path

            # send Rclone mount dir cache clear request
            logger.info("Sending Rclone mount dir cache clear request for: '%s'", cache_clear_path)
            try:
                # try cache clear
                resp = requests.post(rclone_rc_expire_url, json={'remote': cache_clear_path}, timeout=120)
                if '{' in resp.text and '}' in resp.text:
                    data = resp.json()
                    if 'error' in data:
                        # try to vfs/refresh as fallback
                        resp = requests.post(rclone_rc_refresh_url, json={'dir': cache_clear_path}, timeout=120)
                        if '{' in resp.text and '}' in resp.text:
                            data = resp.json()
                            if 'result' in data and cache_clear_path in data['result'] \
                                    and data['result'][cache_clear_path] == 'OK':
                                # successfully vfs refreshed
                                logger.info("Successfully refreshed Rclone VFS mount's dir cache for '%s'", cache_clear_path)
                                return True

                        logger.info("Failed to clear Rclone mount's dir cache for '%s': %s", cache_clear_path,
                                    data['error'] if 'error' in data else data)
                        continue
                    elif ('status' in data and 'message' in data) and data['status'] == 'ok':
                        logger.info("Successfully cleared Rclone Cache mount's dir cache for '%s'", cache_clear_path)
                        return True

                # abort on unexpected response (no json response, no error/status & message in returned json
                logger.error("Unexpected Rclone mount dir cache clear response from %s while trying to clear '%s': %s",
                             rclone_rc_expire_url, cache_clear_path, resp.text)
                break

            except Exception:
                logger.exception("Exception sending Rclone mount dir cache clear request to %s for '%s': ", rclone_rc_expire_url,
                                 cache_clear_path)
                break

    except Exception:
        logger.exception("Exception clearing Rclone mount dir cache for '%s': ", scan_path)
    return False


def load_json(file_path):
    if os.path.sep not in file_path:
        file_path = os.path.join(os.path.dirname(sys.argv[0]), file_path)

    with open(file_path, 'r') as fp:
        return json.load(fp)


def dump_json(file_path, obj, processing=True):
    if os.path.sep not in file_path:
        file_path = os.path.join(os.path.dirname(sys.argv[0]), file_path)

    with open(file_path, 'w') as fp:
        if processing:
            json.dump(obj, fp, indent=2, sort_keys=True)
        else:
            json.dump(obj, fp)
    return


def remove_files_exist_in_plex_database(config, file_paths):
    removed_items = 0
    plex_db_path = config['PLEX_DATABASE_PATH']
    try:
        if plex_db_path and os.path.exists(plex_db_path):
            with sqlite3.connect(plex_db_path) as conn:
                conn.row_factory = sqlite3.Row
                with closing(conn.cursor()) as c:
                    for file_path in copy(file_paths):
                        # check if file exists in plex
                        file_name = os.path.basename(file_path)
                        file_path_plex = map_pushed_path(config, file_path)
                        logger.debug("Checking to see if '%s' exists in the Plex DB located at '%s'", file_path_plex,
                                     plex_db_path)
                        found_item = c.execute("SELECT size FROM media_parts WHERE file LIKE ?",
                                               ('%' + file_path_plex,)) \
                            .fetchone()
                        file_path_actual = map_pushed_path_file_exists(config, file_path_plex)
                        if found_item and os.path.isfile(file_path_actual):
                            # check if file sizes match in plex
                            file_size = os.path.getsize(file_path_actual)
                            logger.debug("'%s' was found in the Plex DB media_parts table.", file_name)
                            logger.debug(
                                "Checking to see if the file size of '%s' matches the existing file size of '%s' in the Plex DB.",
                                file_size, found_item[0])
                            if file_size == found_item[0]:
                                logger.debug("'%s' size matches size found in the Plex DB.", file_size)
                                logger.debug("Removing path from scan queue: '%s'", file_path)
                                file_paths.remove(file_path)
                                removed_items += 1

    except Exception:
        logger.exception("Exception checking if %s exists in the Plex DB: ", file_paths)
    return removed_items


def allowed_scan_extension(file_path, extensions):
    check_path = file_path.lower()
    for ext in extensions:
        if check_path.endswith(ext.lower()):
            logger.debug("'%s' had allowed extension: %s", file_path, ext)
            return True
    logger.debug("'%s' did not have an allowed extension.", file_path)
    return False
