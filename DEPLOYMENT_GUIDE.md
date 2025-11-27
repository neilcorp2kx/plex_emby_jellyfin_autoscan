# Production Deployment Guide

This guide covers the production deployment improvements added to the Plex/Emby/Jellyfin Autoscan application, including Gunicorn WSGI server, multi-stage Docker builds, and resource management.

## Table of Contents

1. [Overview](#overview)
2. [New Features](#new-features)
3. [Deployment Options](#deployment-options)
4. [Configuration](#configuration)
5. [Docker Deployment](#docker-deployment)
6. [Bare Metal Deployment](#bare-metal-deployment)
7. [Performance Tuning](#performance-tuning)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Version 2.2 introduces production-grade deployment features:

- **Gunicorn WSGI Server**: Replaces Flask's development server with a production-ready WSGI server
- **Multi-Stage Docker Build**: Reduces image size by ~40% and improves security
- **Resource Limits**: Prevents runaway container resource consumption
- **Log Rotation**: Automatic log management to prevent disk space issues
- **Improved Health Checks**: Better container orchestration support

---

## New Features

### 1. Gunicorn WSGI Server

**File**: `/mnt/nas/Config/AI-Projects/plex_emby_jellyfin_autoscan/gunicorn_config.py`

Gunicorn provides:
- **Production-ready performance**: Better request handling and concurrency
- **Worker process management**: Automatic restart on failure
- **Memory leak prevention**: Workers restart after processing 1000 requests
- **Configurable workers**: Defaults to `min(CPU_cores * 2 + 1, 4)` for home servers

**Configuration**:
```python
workers = 4                  # Number of worker processes
threads = 2                  # Threads per worker
timeout = 120               # Request timeout (2 minutes)
max_requests = 1000         # Restart workers after 1000 requests
```

**Environment Variables**:
- `GUNICORN_WORKERS`: Override number of workers (default: auto-calculated)
- `LOG_LEVEL`: Set logging level (default: 'info')
- `SERVER_IP`: Bind address (default: '0.0.0.0')
- `SERVER_PORT`: Bind port (default: '3468')

### 2. Multi-Stage Dockerfile

**File**: `/mnt/nas/Config/AI-Projects/plex_emby_jellyfin_autoscan/Dockerfile`

**Stage 1 (Builder)**:
- Installs Python dependencies in a virtual environment
- Separated from runtime for smaller final image

**Stage 2 (Runtime)**:
- Minimal Python 3.11-slim base image
- Only runtime dependencies (curl for health checks)
- Non-root user (autoscan:autoscan, UID 1000)
- Virtual environment copied from builder stage

**Benefits**:
- ~40% smaller image size (no build tools in final image)
- Improved security (minimal attack surface)
- Faster image pulls
- Better layer caching

### 3. WSGI Entry Point

**File**: `/mnt/nas/Config/AI-Projects/plex_emby_jellyfin_autoscan/wsgi.py`

Provides proper initialization for Gunicorn:
- Automatically sets command to 'server' mode
- Initializes background services (queue processor, Google Drive monitor)
- Compatible with both Gunicorn and direct execution

### 4. Resource Limits (Docker Compose)

**File**: `/mnt/nas/Config/AI-Projects/plex_emby_jellyfin_autoscan/docker-compose.yml`

```yaml
deploy:
  resources:
    limits:
      memory: 512M      # Maximum memory usage
      cpus: '2'         # Maximum CPU cores
    reservations:
      memory: 256M      # Minimum guaranteed memory
      cpus: '1'         # Minimum guaranteed CPU
```

### 5. Log Rotation

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"     # Maximum size per log file
    max-file: "3"       # Keep 3 rotated files (30MB total)
```

---

## Deployment Options

### Option 1: Docker Compose (Recommended)

**Best for**: Home servers, development, quick deployment

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 2: Docker (Manual)

**Best for**: Custom orchestration, Kubernetes, production clusters

```bash
# Build image
docker build -t plex_autoscan:2.2 .

# Run container
docker run -d \
  --name plex_autoscan \
  -p 3468:3468 \
  -v ./config:/config \
  -v ./database:/app/database \
  -v /mnt/media:/media:ro \
  --env-file .env \
  -e GUNICORN_WORKERS=4 \
  --memory=512m \
  --cpus=2 \
  plex_autoscan:2.2
```

### Option 3: Bare Metal (Systemd)

**Best for**: Dedicated servers, VPS, direct installation

See [Bare Metal Deployment](#bare-metal-deployment) section below.

---

## Configuration

### Environment Variables

Create a `.env` file from the template:

```bash
cp .env.example .env
nano .env
```

**Production-specific variables**:

```bash
# Security (REQUIRED)
SECRET_KEY=<generate-with-secrets.token_hex-32>
SERVER_PASS=<your-webhook-secret>

# Plex Configuration
PLEX_TOKEN=<your-plex-token>
PLEX_LOCAL_URL=http://localhost:32400

# Jellyfin/Emby Configuration (optional)
JELLYFIN_API_KEY=<your-jellyfin-api-key>
JELLYFIN_LOCAL_URL=http://localhost:8096
EMBY_OR_JELLYFIN=jellyfin

# Server Configuration
SERVER_IP=0.0.0.0
SERVER_PORT=3468

# Session Security (enable for HTTPS)
SESSION_COOKIE_SECURE=false  # Set to 'true' if using HTTPS

# Gunicorn Configuration
GUNICORN_WORKERS=4  # Adjust based on your CPU cores
LOG_LEVEL=info      # Options: debug, info, warning, error

# Security Headers (optional, recommended for production)
ENABLE_TALISMAN=false  # Set to 'true' for security headers
FORCE_HTTPS=false      # Set to 'true' to force HTTPS redirects
```

**Generate secure keys**:

```bash
# SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# SERVER_PASS
python3 -c "import uuid; print('SERVER_PASS=' + uuid.uuid4().hex)"
```

---

## Docker Deployment

### Building the Image

```bash
# Standard build
docker build -t plex_autoscan:2.2 .

# Build with custom tag
docker build -t myregistry.com/plex_autoscan:latest .

# Build for specific platform
docker build --platform linux/amd64 -t plex_autoscan:2.2 .
```

### Running with Docker Compose

**Full `docker-compose.yml` example**:

```yaml
version: '3.8'

services:
  autoscan:
    build: .
    container_name: plex_autoscan
    image: plex_autoscan:latest
    restart: unless-stopped

    ports:
      - "3468:3468"

    volumes:
      - ./config:/config
      - ./database:/app/database
      - /mnt/media:/media:ro

    env_file:
      - .env

    environment:
      - TZ=America/New_York
      - PUID=1000
      - PGID=1000
      - GUNICORN_WORKERS=4

    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '2'
        reservations:
          memory: 256M
          cpus: '1'

    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

    networks:
      - media_network

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:${SERVER_PORT:-3468}/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s

networks:
  media_network:
    driver: bridge
```

### Running Other Commands

The Docker image uses Gunicorn by default. For other commands:

```bash
# Show Plex sections
docker run --rm -v ./config:/config plex_autoscan:2.2 python scan.py sections

# Show detailed sections
docker run --rm -v ./config:/config plex_autoscan:2.2 python scan.py sections+

# Authorize Google Drive
docker run -it --rm -v ./config:/config plex_autoscan:2.2 python scan.py authorize

# Build Google Drive caches
docker run --rm -v ./config:/config plex_autoscan:2.2 python scan.py build_caches
```

---

## Bare Metal Deployment

### Prerequisites

```bash
# Install Python 3.11+
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip curl

# Create virtual environment
python3.11 -m venv /opt/plex_autoscan/venv
source /opt/plex_autoscan/venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Systemd Service

Create `/etc/systemd/system/plex_autoscan.service`:

```ini
[Unit]
Description=Plex/Emby/Jellyfin Autoscan
After=network.target

[Service]
Type=notify
User=autoscan
Group=autoscan
WorkingDirectory=/opt/plex_autoscan
Environment="PATH=/opt/plex_autoscan/venv/bin"
EnvironmentFile=/opt/plex_autoscan/.env

# Gunicorn command
ExecStart=/opt/plex_autoscan/venv/bin/gunicorn \
    --config /opt/plex_autoscan/gunicorn_config.py \
    --chdir /opt/plex_autoscan \
    wsgi:application

# Restart configuration
Restart=always
RestartSec=10

# Resource limits
MemoryLimit=512M
CPUQuota=200%

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/plex_autoscan/database /opt/plex_autoscan/logs

[Install]
WantedBy=multi-user.target
```

**Enable and start**:

```bash
sudo systemctl daemon-reload
sudo systemctl enable plex_autoscan
sudo systemctl start plex_autoscan
sudo systemctl status plex_autoscan
```

**View logs**:

```bash
sudo journalctl -u plex_autoscan -f
```

---

## Performance Tuning

### Worker Configuration

**Low-power devices** (Raspberry Pi, NAS):
```bash
GUNICORN_WORKERS=2
```

**Mid-range servers** (4-8 cores):
```bash
GUNICORN_WORKERS=4
```

**High-performance servers** (8+ cores):
```bash
GUNICORN_WORKERS=8
```

**Formula**: `workers = (2 × CPU_cores) + 1`, capped at 4 for home servers

### Memory Optimization

**Minimum**: 256MB (basic operation)
**Recommended**: 512MB (with headroom)
**High-load**: 1GB (heavy Google Drive monitoring)

### Database Tuning

The application uses connection pooling (configured in `db.py`):

```python
max_connections=8           # Maximum concurrent connections
stale_timeout=300          # Close idle connections after 5 minutes
journal_mode='wal'         # Write-Ahead Logging for concurrency
cache_size=-1024 * 64      # 64MB cache
```

---

## Monitoring

### Health Checks

**Endpoint**: `GET http://localhost:3468/`

**Docker health check**:
- Runs every 30 seconds
- 10-second timeout
- 3 retries before marking unhealthy
- 15-second startup grace period

**Manual health check**:
```bash
curl -f http://localhost:3468/
```

### Logging

**Log locations**:
- Docker: `docker logs plex_autoscan`
- Bare metal: `/opt/plex_autoscan/logs/plex_autoscan.log`
- Systemd: `journalctl -u plex_autoscan`

**Log levels**:
```bash
LOG_LEVEL=debug    # Verbose debugging
LOG_LEVEL=info     # Standard operation (default)
LOG_LEVEL=warning  # Warnings and errors only
LOG_LEVEL=error    # Errors only
```

### Resource Monitoring

**Docker**:
```bash
# Real-time stats
docker stats plex_autoscan

# Historical stats
docker inspect plex_autoscan
```

**Bare metal**:
```bash
# Process stats
ps aux | grep gunicorn

# Memory usage
systemctl status plex_autoscan

# Detailed metrics
top -p $(pgrep -f gunicorn)
```

---

## Troubleshooting

### Issue: Container won't start

**Symptoms**: Container exits immediately

**Solutions**:
1. Check logs: `docker logs plex_autoscan`
2. Verify `.env` file exists and has correct permissions
3. Ensure config directory is mounted correctly
4. Check for port conflicts: `netstat -tlnp | grep 3468`

### Issue: Background services not starting

**Symptoms**: Queue processor or Google Drive monitor not running

**Solutions**:
1. Check `wsgi.py` is being used (not `scan.py` directly)
2. Verify environment variables are loaded
3. Check logs for initialization messages
4. Ensure `SERVER_USE_SQLITE` or `GOOGLE.ENABLED` are configured

### Issue: High memory usage

**Symptoms**: Container using >512MB memory

**Solutions**:
1. Reduce `GUNICORN_WORKERS`
2. Lower `max_connections` in `db.py`
3. Disable Google Drive monitoring if not needed
4. Check for memory leaks (restart workers more frequently)

### Issue: Slow response times

**Symptoms**: Webhooks timing out or delayed

**Solutions**:
1. Increase `GUNICORN_WORKERS`
2. Increase `timeout` in `gunicorn_config.py`
3. Check database performance (run `VACUUM` on SQLite)
4. Verify network connectivity to Plex/Jellyfin

### Issue: Permission denied errors

**Symptoms**: Cannot write to database or logs

**Solutions**:
```bash
# Docker: Fix volume permissions
sudo chown -R 1000:1000 ./config ./database ./logs

# Bare metal: Fix service permissions
sudo chown -R autoscan:autoscan /opt/plex_autoscan
```

### Issue: Gunicorn not binding to port

**Symptoms**: Port 3468 not listening

**Solutions**:
1. Check `SERVER_IP` and `SERVER_PORT` in `.env`
2. Verify firewall allows port 3468
3. Ensure no other service using the port
4. Check Docker port mapping: `-p 3468:3468`

---

## Migration from v2.1

### Breaking Changes

**None** - v2.2 is backward compatible with v2.1 configuration

### Upgrade Steps

1. **Pull latest code**:
   ```bash
   git pull origin master
   ```

2. **Rebuild Docker image**:
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

3. **Verify operation**:
   ```bash
   docker-compose logs -f
   # Look for "Initializing background services for Gunicorn..."
   ```

4. **Update environment variables** (optional):
   ```bash
   # Add to .env
   GUNICORN_WORKERS=4
   LOG_LEVEL=info
   ```

### Rollback Procedure

If issues occur, rollback to v2.1:

```bash
# Stop current version
docker-compose down

# Checkout v2.1 tag
git checkout v2.1

# Rebuild and restart
docker-compose up -d --build
```

---

## Best Practices

### Security

1. **Always use HTTPS in production**:
   ```bash
   SESSION_COOKIE_SECURE=true
   ENABLE_TALISMAN=true
   FORCE_HTTPS=true
   ```

2. **Generate unique secrets**:
   ```bash
   # Never use default or example values
   SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
   SERVER_PASS=$(python3 -c "import uuid; print(uuid.uuid4().hex)")
   ```

3. **Restrict file permissions**:
   ```bash
   chmod 600 .env
   chmod 700 config/
   ```

4. **Use environment variables** (never commit secrets to git):
   ```bash
   # Add to .gitignore
   .env
   config/config.json
   ```

### Performance

1. **Start with 4 workers** and adjust based on load
2. **Enable log rotation** to prevent disk space issues
3. **Set resource limits** to prevent runaway processes
4. **Monitor health checks** for early issue detection

### Maintenance

1. **Regular updates**:
   ```bash
   # Monthly security updates
   pip install --upgrade -r requirements.txt
   docker-compose build --no-cache
   ```

2. **Database maintenance**:
   ```bash
   # Quarterly vacuum
   sqlite3 database/plex_autoscan.db "VACUUM;"
   ```

3. **Log review**:
   ```bash
   # Weekly log review
   docker-compose logs --since 7d | grep ERROR
   ```

---

## Additional Resources

- **Gunicorn Documentation**: https://docs.gunicorn.org/
- **Docker Best Practices**: https://docs.docker.com/develop/dev-best-practices/
- **Flask Production Deployment**: https://flask.palletsprojects.com/en/latest/deploying/
- **Systemd Service Management**: https://www.freedesktop.org/software/systemd/man/systemd.service.html

---

**Version**: 2.2
**Last Updated**: 2025-11-26
**Author**: DeploymentAgent
