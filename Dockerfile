# Plex/Emby/Jellyfin Autoscan - Multi-Stage Production Dockerfile
# Stage 1: Builder - Install dependencies
FROM python:3.11-slim AS builder

LABEL maintainer="neilcorp2kx"
LABEL description="Modernized Plex/Jellyfin/Emby Autoscan with 2024/2025 dependencies and production-grade deployment"
LABEL version="2.2"

# Set environment variables for build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install dependencies into a virtual environment
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime - Slim production image
FROM python:3.11-slim AS runtime

# Install only runtime dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application directory, user, and required directories
# Using UID/GID 1002 for compatibility with existing setups
RUN groupadd -r -g 1002 autoscan && \
    useradd -r -g autoscan -u 1002 -d /app -s /bin/bash autoscan && \
    mkdir -p /app /config /app/database /app/logs && \
    chown -R autoscan:autoscan /app /config

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application files with proper ownership
COPY --chown=autoscan:autoscan . .

# Create volume mount points for persistent data
VOLUME ["/config", "/app/database"]

# Switch to non-root user for security
USER autoscan

# Add virtual environment to PATH
ENV PATH="/opt/venv/bin:$PATH"

# Expose webhook port (default: 3468)
EXPOSE 3468

# Health check - tests if the server is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${SERVER_PORT:-3468}/ || exit 1

# Run the application using Gunicorn for production
# Note: For non-server commands (sections, authorize, etc.), override with:
# docker run --rm <image> python scan.py <command>
CMD ["gunicorn", "--config", "gunicorn_config.py", "wsgi:application"]
