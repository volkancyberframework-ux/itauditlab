import os


bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
worker_class = "sync"

# Keep deploy shutdowns graceful while preventing a stuck request from
# wedging a worker indefinitely.
timeout = 60
graceful_timeout = 30
keepalive = 5

# Periodically recycle workers to contain slow memory growth. Jitter avoids
# replacing every worker at once.
max_requests = 1000
max_requests_jitter = 100

# Avoid worker heartbeat stalls on disk-backed filesystems.
worker_tmp_dir = "/dev/shm"

accesslog = "-"
errorlog = "-"
capture_output = True
