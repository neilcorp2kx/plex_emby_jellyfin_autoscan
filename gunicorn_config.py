import multiprocessing
import os

# Bind to configured host/port or defaults
bind = f"{os.getenv('SERVER_IP', '0.0.0.0')}:{os.getenv('SERVER_PORT', '3468')}"

# Workers: 2-4 x CPU cores (capped for home server use)
workers = int(os.getenv('GUNICORN_WORKERS', min(multiprocessing.cpu_count() * 2 + 1, 4)))
worker_class = 'sync'
threads = 2

# Timeouts
timeout = 120
graceful_timeout = 30
keepalive = 5

# Restart workers periodically to prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
