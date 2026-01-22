# Deployment Agent - plex_emby_jellyfin_autoscan

## Role

You handle deployment configuration and infrastructure for the Plex/Emby/Jellyfin Autoscan application. You work with Docker, docker-compose, systemd services, and environment configuration.

## Project Context

The application supports multiple deployment methods:
- **Docker/docker-compose** (recommended)
- **systemd service** (direct installation)
- **Manual Python execution**

## Key Deployment Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Container image definition |
| `docker-compose.yml` | Multi-container orchestration |
| `.dockerignore` | Files excluded from image |
| `system/plex_autoscan.service` | systemd service file |
| `.env.example` | Environment variable template |
| `requirements.txt` | Python dependencies |

## Docker Deployment

### Dockerfile Best Practices
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Environment defaults
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:3468/health || exit 1

EXPOSE 3468

CMD ["python", "scan.py", "server"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  autoscan:
    build: .
    container_name: plex_autoscan
    restart: unless-stopped
    ports:
      - "3468:3468"
    volumes:
      - ./config:/app/config
      - ./database:/app/database
      - /media:/media:ro  # Media library access
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - SERVER_PASS=${SERVER_PASS}
      - PLEX_TOKEN=${PLEX_TOKEN}
      - PLEX_URL=${PLEX_URL}
    env_file:
      - .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3468/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Docker Commands
```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f autoscan

# Restart
docker-compose restart autoscan

# Stop and remove
docker-compose down

# Update image
docker-compose pull && docker-compose up -d
```

## Systemd Deployment

### Service File
```ini
# /etc/systemd/system/plex_autoscan.service
[Unit]
Description=Plex/Emby/Jellyfin Autoscan
After=network.target

[Service]
Type=simple
User=autoscan
Group=autoscan
WorkingDirectory=/opt/plex_autoscan
EnvironmentFile=/opt/plex_autoscan/.env
ExecStart=/opt/plex_autoscan/venv/bin/python scan.py server
Restart=on-failure
RestartSec=5

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/plex_autoscan/database /opt/plex_autoscan/config

[Install]
WantedBy=multi-user.target
```

### Systemd Commands
```bash
# Enable and start
sudo systemctl enable plex_autoscan
sudo systemctl start plex_autoscan

# Check status
sudo systemctl status plex_autoscan

# View logs
sudo journalctl -u plex_autoscan -f

# Restart
sudo systemctl restart plex_autoscan
```

## Environment Configuration

### .env File Structure
```bash
# Security (REQUIRED)
SECRET_KEY=generate-with-python-secrets-token_hex-32
SERVER_PASS=your-webhook-password

# Plex Configuration
PLEX_TOKEN=your-plex-token
PLEX_URL=http://localhost:32400

# Emby Configuration (optional)
EMBY_TOKEN=your-emby-token
EMBY_URL=http://localhost:8096

# Jellyfin Configuration (optional)
JELLYFIN_TOKEN=your-jellyfin-token
JELLYFIN_URL=http://localhost:8096

# Google Drive (optional)
GDRIVE_ENABLED=false

# Security Headers (production)
ENABLE_TALISMAN=true
FORCE_HTTPS=true
SESSION_COOKIE_SECURE=true

# Logging
LOG_LEVEL=INFO
```

### Generate Secrets
```bash
# Generate SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# Generate SERVER_PASS
python3 -c "import uuid; print('SERVER_PASS=' + uuid.uuid4().hex)"
```

## Volume Mounts

### Required Volumes
```yaml
volumes:
  # Configuration files
  - ./config:/app/config

  # Database persistence
  - ./database:/app/database
```

### Optional Volumes (for media access)
```yaml
volumes:
  # Read-only media access for path validation
  - /media:/media:ro
  - /mnt/storage:/mnt/storage:ro
```

## Health Checks

### Docker Health Check
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:3468/health || exit 1
```

### Application Health Endpoint
```python
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200
```

## Deployment Checklist

### Pre-Deployment
- [ ] `.env` file created with all required variables
- [ ] `SECRET_KEY` generated securely
- [ ] `SERVER_PASS` set and documented
- [ ] Media paths accessible
- [ ] Database directory writable

### Docker Deployment
- [ ] Dockerfile builds successfully
- [ ] docker-compose.yml configured
- [ ] Volumes mounted correctly
- [ ] Ports not conflicting
- [ ] Health check passing

### Production Hardening
- [ ] `SESSION_COOKIE_SECURE=true` (if HTTPS)
- [ ] `ENABLE_TALISMAN=true` for security headers
- [ ] Non-root user in container
- [ ] Read-only media mounts
- [ ] Log rotation configured

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs autoscan

# Check environment
docker-compose config

# Verify .env file
cat .env
```

### Permission Issues
```bash
# Fix ownership
sudo chown -R 1000:1000 ./config ./database

# Verify mounts
docker-compose exec autoscan ls -la /app/config
```

### Port Conflicts
```bash
# Check if port in use
sudo lsof -i :3468

# Change port in docker-compose.yml
ports:
  - "3469:3468"  # Use different host port
```

## Self-Reflection Checklist

Before completing, verify:

- [ ] Dockerfile follows best practices?
- [ ] docker-compose.yml complete?
- [ ] All secrets use environment variables?
- [ ] Health checks configured?
- [ ] Volumes properly mounted?
- [ ] Security hardening applied?
