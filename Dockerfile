# Plex/Emby/Jellyfin Autoscan - Modern Docker Image
# Based on Python 3.11 slim for security and performance

FROM python:3.11-slim

LABEL maintainer="neilcorp2kx"
LABEL description="Modernized Plex/Jellyfin/Emby Autoscan with 2024/2025 dependencies and API-based scanning"
LABEL version="2.1"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create application directory, user, and required directories
RUN groupadd -r autoscan && \
    useradd -r -g autoscan -u 1000 -d /app -s /bin/bash autoscan && \
    mkdir -p /app /config /app/database /app/logs && \
    chown -R autoscan:autoscan /app /config

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY --chown=autoscan:autoscan requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=autoscan:autoscan . .

# Create volume mount points for persistent data
VOLUME ["/config", "/app/database"]

# Switch to non-root user for security (run as autoscan, not root)
USER autoscan

# Expose webhook port (default: 3468)
EXPOSE 3468

# Health check - tests the webhook endpoint with a GET request
# Note: In production, SERVER_PASS should be set via environment variable
# This checks the root endpoint which returns 200 if the server is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3468/ || exit 1

# Run the application
CMD ["python3", "scan.py", "server"]
