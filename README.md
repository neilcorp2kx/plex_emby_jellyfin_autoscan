<img src="assets/logo.svg" width="600" alt="Plex & Jellyfin Autoscan">

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-blue.svg?style=flat-square)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPL%203-blue.svg?style=flat-square)](https://github.com/l3uddz/plex_autoscan/blob/master/LICENSE.md)
[![last commit (develop)](https://img.shields.io/github/last-commit/l3uddz/plex_autoscan/develop.svg?colorB=177DC1&label=Last%20Commit&style=flat-square)](https://github.com/l3uddz/plex_autoscan/commits/develop)
[![Discord](https://img.shields.io/discord/381077432285003776.svg?colorB=177DC1&label=Discord&style=flat-square)](https://discord.io/cloudbox)
[![Contributing](https://img.shields.io/badge/Contributing-gray.svg?style=flat-square)](CONTRIBUTING.md)
[![Donate](https://img.shields.io/badge/Donate-gray.svg?style=flat-square)](#donate)

---

## 🚀 2024/2025 Modernization Update

This fork has been **completely modernized** with the latest security features and dependencies:

**✅ Modern Dependencies (2024/2025)**
- Flask 3.0.3, Werkzeug 3.0.4, Jinja2 3.1.4
- Peewee 3.17.6 with connection pooling
- Python 3.7+ only (Python 2 removed)
- All dependencies updated to latest stable versions

**✅ Production-Ready Deployment (v2.2)** 🆕
- **Gunicorn WSGI Server** - Production-grade server replacing Flask development server
- **Rate Limiting** - Flask-Limiter protection against abuse (configurable limits)
- **Health Endpoint** - `/health` endpoint for container monitoring and load balancers
- **Multi-worker Support** - Configure `GUNICORN_WORKERS` for better performance
- **Optimized Database** - Connection pooling with N+1 query fixes

**✅ API-Based Plex Scanning (v2.1)**
- **Migrated from deprecated CLI scanner to modern Plex API**
- No more Docker CLI or sudo requirements
- No more Docker socket mounting needed
- Simplified configuration - just need `PLEX_LOCAL_URL` and `PLEX_TOKEN`
- Future-proof - uses officially supported Plex API
- Better error handling with HTTP status codes
- **See [Issue #33](https://github.com/neilcorp2kx/plex_emby_jellyfin_autoscan/issues/33) for details**

**✅ Security Enhancements**
- Environment variable support (`.env` file)
- Input validation and sanitization (`validators.py` module)
- Path traversal protection
- Session security (HttpOnly, SameSite cookies)
- Jinja2 templates with automatic XSS protection
- Request timeout protection (already implemented)

**✅ Performance Improvements**
- Database connection pooling with PooledSqliteDatabase
- WAL mode for better concurrency
- 64MB cache for reduced disk I/O
- Optimized database operations

**See [Security Best Practices](#security-best-practices) section below for setup instructions.**

---

## 📢 Important: v2.1 API Migration Notice

**Version 2.1 has migrated from the deprecated Plex CLI scanner to the modern Plex API.** This change brings significant simplifications:

### ✅ What's Better Now

- **Simpler Docker Setup**: No more Docker socket mounting (`/var/run/docker.sock`)
- **No Docker CLI Needed**: Removed Docker CLI installation from container
- **No Sudo Required**: Eliminated sudo-based scanner execution
- **Future-Proof**: Uses officially supported Plex API (CLI scanner is deprecated)
- **Better Error Handling**: Clear HTTP status codes instead of CLI errors

### 🗑️ Configuration No Longer Required

These config options are **no longer needed** for Plex scanning (still present for backward compatibility but not used):

- ~~`PLEX_SCANNER`~~ - Scanner binary path (not used with API)
- ~~`PLEX_LD_LIBRARY_PATH`~~ - Library path (not used with API)
- ~~`PLEX_SUPPORT_DIR`~~ - Support directory (not used with API)
- ~~`USE_DOCKER`~~ - Docker execution mode (not used with API)
- ~~`USE_SUDO`~~ - Sudo execution (not used with API)
- ~~`DOCKER_NAME`~~ - Docker container name (not used with API)
- ~~`PLEX_USER`~~ - Plex user account (not used with API)
- ~~`PLEX_WAIT_FOR_EXTERNAL_SCANNERS`~~ - Scanner process waiting (not applicable with API)

### ✅ Required Configuration (Unchanged)

These are the only Plex-related configs you need:

- **`PLEX_LOCAL_URL`** - Plex server URL (e.g., `http://plex:32400`)
- **`PLEX_TOKEN`** - Authentication token

### 🔄 Migration Path for Existing Users

**You don't need to change anything!** The migration is backward compatible:

1. **Docker Users**: Remove the Docker socket mount from your docker-compose.yml (optional cleanup)
   ```yaml
   # Can be removed:
   # - /var/run/docker.sock:/var/run/docker.sock:ro
   ```

2. **Config Cleanup** (optional): Old config options are harmless to leave in place, but you can remove them if desired

3. **Rebuild Docker Image**: `docker-compose build --no-cache` (recommended for Docker users)

**Everything else continues to work exactly as before!**

---

## 🚀 v2.2 Production Deployment Features

Version 2.2 introduces production-grade deployment capabilities for reliable, scalable operation.

### ✅ What's New in v2.2

**Gunicorn WSGI Server**
- Replaces Flask's development server with production-grade Gunicorn
- Multi-worker support for better concurrent request handling
- Automatic worker management and graceful restarts
- Proper signal handling for container orchestration

**Rate Limiting (Flask-Limiter)**
- Protects against webhook flooding and abuse
- Default: 200 requests/day, 50/hour per IP
- Webhook endpoints: Higher limits for automation tools
- Configurable via environment variables

**Health Monitoring**
- `/health` endpoint for container health checks
- Returns JSON status with queue count and uptime
- Compatible with Docker health checks, Kubernetes probes, and load balancers
- Example response: `{"status": "healthy", "queue_count": 5}`

**Database Optimizations**
- Fixed N+1 query issues in queue path checking
- Atomic operations prevent race conditions
- Connection pooling with WAL mode for better concurrency

### 🔧 Configuration

**Environment Variables (Docker):**

```yaml
environment:
  - GUNICORN_WORKERS=2          # Number of worker processes (default: 2)
  - GUNICORN_TIMEOUT=120        # Worker timeout in seconds (default: 120)
  - GUNICORN_MAX_REQUESTS=1000  # Requests before worker restart (default: 1000)
```

**Health Check Configuration:**

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:3468/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 15s
```

### 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check - returns status and queue count |
| `/{SERVER_PASS}` | POST | Webhook endpoint for Sonarr/Radarr/Lidarr |
| `/{SERVER_PASS}` | GET | Manual scan form (if `SERVER_ALLOW_MANUAL_SCAN=true`) |
| `/{SERVER_PASS}/queue_count` | GET | Returns current queue size |

### 🔄 Migration from v2.1

**No breaking changes!** v2.2 is fully backward compatible:

1. **Docker Users**: Rebuild your image to get Gunicorn
   ```bash
   docker-compose build --no-cache
   docker-compose up -d
   ```

2. **Native Users**: Install updated requirements and use Gunicorn
   ```bash
   pip install -r requirements.txt
   gunicorn -w 2 -b 0.0.0.0:3468 wsgi:application
   ```

3. **Optional**: Add health check to your docker-compose.yml (see above)

---

## 🏠 Home Server Quick Start

**Good news:** This application is already optimized for home servers! You only need minimal configuration.

### What's Already Perfect for Home Use

✅ **Webhook-Friendly**: Sonarr/Radarr/Lidarr webhooks work out of the box
✅ **Smart Defaults**: Heavy security features (Talisman, HTTPS enforcement) are **OFF by default**
✅ **Zero Performance Impact**: CSRF protection is active but doesn't slow anything down
✅ **No Configuration Needed**: Everything works with sensible defaults

### Minimal Setup (5 Minutes)

**1. Create your `.env` file:**
```bash
cp .env.example .env
nano .env
```

**2. Add just these two essential values:**
```bash
# Generate a secure secret key (run this command):
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# Generate a webhook password (run this command):
python3 -c "import uuid; print('SERVER_PASS=' + uuid.uuid4().hex)"

# Paste the generated values into your .env file:
SECRET_KEY=your_generated_key_here
SERVER_PASS=your_generated_password_here

# All other variables are OPTIONAL:
# - PLEX_TOKEN (can stay in config.json)
# - PLEX_LOCAL_URL (can stay in config.json)
# - JELLYFIN_API_KEY (can stay in config.json)
# - ENABLE_TALISMAN (already defaults to false)
# - FORCE_HTTPS (already defaults to false)
# - SESSION_COOKIE_SECURE (already defaults to false)
# - SECRET_KEY_FALLBACKS (only needed for key rotation)
```

**3. Secure the file:**
```bash
chmod 600 .env
```

**That's it!** You're done. 🎉

### What You Get

- ✅ Modern 2024/2025 dependencies (no security vulnerabilities)
- ✅ Input validation (prevents accidents and malformed data)
- ✅ Session security with HttpOnly cookies
- ✅ Webhooks work perfectly (CSRF exempted for Sonarr/Radarr/Lidarr)
- ✅ No HTTPS required for local network use
- ✅ No performance overhead

### Advanced Options (Optional)

**Only configure these if exposing to the internet:**

```bash
# Enable HTTPS enforcement (requires valid SSL certificate)
ENABLE_TALISMAN=true
FORCE_HTTPS=true
SESSION_COOKIE_SECURE=true
```

**Security Features Already OFF by Default:**
- ⭕ Security headers (Talisman) - **DISABLED** (not needed on LAN)
- ⭕ HTTPS enforcement - **DISABLED** (not needed on LAN)
- ⭕ Key rotation - **OPTIONAL** (only for paranoid users)

### FAQ

**Q: Is CSRF protection going to break my webhooks?**
A: No! Webhooks are automatically exempted from CSRF checks. Sonarr/Radarr/Lidarr work perfectly.

**Q: Do I need HTTPS for my home server?**
A: No! HTTPS enforcement is disabled by default. Only enable if exposing to the internet.

**Q: Should I remove security features to simplify?**
A: No need! Current defaults are already minimal. Security features have zero performance impact and don't interfere with normal operation.

**Q: What about all the other security enhancements from PR #21?**
A: They're designed to be invisible on home servers. Session refresh just means you don't get logged out unnecessarily. Everything works seamlessly.

For complete security documentation, see [Security Best Practices](#security-best-practices) below.

---
<!-- TOC depthFrom:1 depthTo:2 withLinks:1 updateOnSave:0 orderedList:0 -->

- [v2.2 Production Deployment Features](#-v22-production-deployment-features)
- [Home Server Quick Start](#-home-server-quick-start)
- [Introduction](#introduction)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Example](#example)
  - [Basics](#basics)
  - [Docker](#docker)
  - [Emby and Jellyfin Media Server Options](#emby-and-jellyfin-media-server-options)
  - [Plex Media Server](#plex-media-server)
  - [Plex Autoscan Server](#plex-autoscan-server)
  - [Google Drive Monitoring](#google-drive-monitoring)
  - [Rclone Remote Control](#rclone-remote-control)
- [Setup](#setup)
  - [Sonarr](#sonarr)
  - [Radarr](#radarr)
  - [Lidarr](#lidarr)
- [Donate](#donate)

<!-- /TOC -->

---


# Introduction

Plex Autoscan is a python script that assists in the importing of Sonarr, Radarr, and Lidarr downloads into Plex Media Server.

It does this by creating a web server to accept webhook requests from these apps, and in turn, sends a scan request to Plex. Plex will then only scan the parent folder (i.e. season folder for TV shows, movie folder for movies, and album folders for music) of the media file (versus scanning the entire library folder).

In addition to the above, Plex Autoscan can also monitor Google Drive for updates. When a new file is detected, it is checked against the Plex database and if this file is missing, a new scan request is sent to Plex (see section [below](README.md#google-drive-monitoring)).

Plex Autoscan is installed on the same server as the Plex Media Server.

# Requirements

1. Ubuntu/Debian

2. **Python 3.7 or higher** (`sudo apt install python3 python3-pip python3-venv`).

3. Curl (`sudo apt install curl`).

4. requirements.txt modules (see below).

**Note:** Python 2 support has been removed as of 2024. This version requires Python 3.7+.

# Installation

**First, choose your installation method**, then follow the instructions for your specific media server(s):

## 📊 Docker vs Native Comparison

| Feature | 🐳 Docker (Recommended) | 💻 Native Installation |
|---------|-------------------------|------------------------|
| **Setup Complexity** | Simple (no Python setup) | Moderate (Python + dependencies) |
| **Isolation** | Fully isolated | Shares host Python environment |
| **Updates** | `docker-compose pull` | `git pull` + `pip install` |
| **Home Server Support** | Perfect (Unraid, TrueNAS) | Manual setup required |
| **Disk Space** | ~161MB image | ~50MB (dependencies) |
| **Performance** | Native (minimal overhead) | Native |
| **Best For** | Home servers, beginners, containers | VPS, advanced users, custom setups |

---

## 🐳 Docker Installation (Recommended)

**Benefits:**
- ✅ No Python environment setup required
- ✅ Isolated dependencies (no conflicts)
- ✅ Easy updates with `docker-compose pull`
- ✅ Consistent environment across systems
- ✅ Perfect for home servers (Unraid, TrueNAS, etc.)

**Prerequisites:**
- Docker and Docker Compose installed
- Docker Engine 20.10.0+ and Docker Compose 2.0.0+ recommended

---

### Getting Your Plex Token

You need a Plex authentication token to allow Plex Autoscan to communicate with your Plex Media Server. Choose one of the methods below:

**Method 1: Plex Web App (Easiest)**

1. Open Plex Web App and play any media file
2. Click the "info" icon (ⓘ) or three dots menu
3. Select "Get Info" or "View XML"
4. Look for `X-Plex-Token=` in the URL or XML
5. Copy the token value (long alphanumeric string)

**Method 2: Official Plex Support Article**

Visit the official Plex documentation:
https://support.plex.tv/hc/en-us/articles/204059436-Finding-an-authentication-token-X-Plex-Token

**Method 3: Command Line (Advanced)**

```bash
# Using curl (requires Plex username and password)
curl -u 'your_plex_username' 'https://plex.tv/users/sign_in.xml' -X POST | grep -oP 'authToken="\K[^"]+'

# You will be prompted to enter your Plex password
# The output will be your Plex token
```

**Security Note:** Keep your Plex token secure. Never share it publicly or commit it to version control.

---

### Generating Secure Secrets

Before configuring Plex Autoscan, you need to generate secure random values for `SECRET_KEY` and `SERVER_PASS`.

**Generate SECRET_KEY (64-character hex string):**

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
# Output example: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2
```

**Generate SERVER_PASS (32-character hex string):**

```bash
python3 -c "import secrets; print(secrets.token_hex(16))"
# Output example: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

**Alternative (using UUID for SERVER_PASS):**

```bash
python3 -c "import uuid; print(uuid.uuid4().hex)"
# Output example: 9c4b81fe234e4d6eb9011cefe514d915
```

**Important:**
- Copy these values to your `.env` file immediately
- Never reuse secrets across different applications
- Store them securely (password manager recommended)
- Regenerate if compromised

---

### Option A: Docker + Plex Only

**Perfect for:** Pure Plex users running Docker

**1. Clone and setup:**
```bash
git clone https://github.com/neilcorp2kx/plex_emby_jellyfin_autoscan.git
cd plex_emby_jellyfin_autoscan
mkdir -p config database
```

**2. Generate your secrets:**

Run these commands and save the output:
```bash
# Generate SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# Generate SERVER_PASS
python3 -c "import secrets; print('SERVER_PASS=' + secrets.token_hex(16))"
```

**3. Get your Plex Token:**

See the "Getting Your Plex Token" section above for detailed instructions.

**4. Create `.env` file:**
```bash
cp .env.example .env
nano .env
```

**Add these values (use the secrets you generated above):**
```bash
# Required: Security keys (paste your generated values)
SECRET_KEY=your_generated_secret_key_here
SERVER_PASS=your_generated_server_pass_here

# Plex Configuration (paste your Plex token)
PLEX_TOKEN=your_plex_token_here
PLEX_LOCAL_URL=http://localhost:32400

# Leave blank (not using Jellyfin/Emby)
JELLYFIN_API_KEY=
EMBY_OR_JELLYFIN=
```

**5. Secure the `.env` file:**
```bash
chmod 600 .env
```

**6. Edit `docker-compose.yml` volumes:**
```yaml
volumes:
  # Your media library
  - /path/to/your/media:/media:ro

  # Plex database (adjust based on your setup)
  # If Plex is in Docker:
  - plex-config:/var/lib/plexmediaserver:ro
  # If Plex is native on host:
  # - /var/lib/plexmediaserver:/var/lib/plexmediaserver:ro
```

**7. Generate and configure:**
```bash
# Option 1: Start from example template (recommended)
cp config.example.json config/config.json
nano config/config.json

# Option 2: Generate from scratch
docker-compose run --rm autoscan python3 scan.py sections
nano config/config.json
```

**Configure these `config.json` settings:**
- `PLEX_USER`: `"plex"` (or `"abc"` for LinuxServer.io image)
- `PLEX_DATABASE_PATH`: Container path to Plex DB
- Leave `PLEX_TOKEN` empty (will use value from `.env`)
- Leave `JELLYFIN_API_KEY` and `EMBY_OR_JELLYFIN` at defaults

**8. Start container:**
```bash
docker-compose up -d
docker-compose logs -f autoscan  # View logs
```

**✅ Done!** Plex Autoscan is now running. Webhook URL: `http://your-ip:3468/your_server_pass`

---

### Option B: Docker + Jellyfin/Emby Only

**Perfect for:** Jellyfin or Emby users (no Plex)

**1. Clone and setup:**
```bash
git clone https://github.com/neilcorp2kx/plex_emby_jellyfin_autoscan.git
cd plex_emby_jellyfin_autoscan
mkdir -p config database
```

**2. Create `.env` file:**
```bash
cp .env.example .env
nano .env
```

**Add these values:**
```bash
# Required: Security keys
SECRET_KEY=<run: python3 -c "import secrets; print(secrets.token_hex(32))">
SERVER_PASS=<run: python3 -c "import uuid; print(uuid.uuid4().hex)">

# Jellyfin/Emby Configuration
JELLYFIN_API_KEY=your_jellyfin_api_key_here
EMBY_OR_JELLYFIN=jellyfin  # or "emby"

# Leave blank (not using Plex)
PLEX_TOKEN=
PLEX_LOCAL_URL=
```

**3. Get Jellyfin/Emby API Key:**
- **Jellyfin**: Dashboard → Advanced → API Keys → New API Key
- **Emby**: Dashboard → Advanced → API Keys → New API Key

**4. Edit `docker-compose.yml` volumes:**
```yaml
volumes:
  # Your media library
  - /path/to/your/media:/media:ro

  # No Plex database needed for Jellyfin/Emby
```

**5. Generate and configure:**
```bash
# Option 1: Start from example template (recommended)
cp config.example.json config/config.json
nano config/config.json

# Option 2: Generate from scratch
docker-compose run --rm autoscan python3 scan.py sections
nano config/config.json
```

**Configure these `config.json` settings:**
- `JELLYFIN_API_KEY`: Your API key from step 3
- `EMBY_OR_JELLYFIN`: `"jellyfin"` or `"emby"`
- Leave Plex settings at defaults (will be ignored)

**6. Start container:**
```bash
docker-compose up -d
docker-compose logs -f autoscan  # View logs
```

**Important Notes:**
- **Partial scan**: New episodes or upgrades = fast scan ✅
- **Full scan**: New folders = full library scan (Jellyfin/Emby limitation)

**✅ Done!** Webhook URL: `http://your-ip:3468/your_server_pass`

---

### Option C: Docker + Both Plex & Jellyfin/Emby

**Perfect for:** Running both media servers simultaneously

**1. Clone and setup:**
```bash
git clone https://github.com/neilcorp2kx/plex_emby_jellyfin_autoscan.git
cd plex_emby_jellyfin_autoscan
mkdir -p config database
```

**2. Create `.env` file:**
```bash
cp .env.example .env
nano .env
```

**Add these values:**
```bash
# Required: Security keys
SECRET_KEY=<run: python3 -c "import secrets; print(secrets.token_hex(32))">
SERVER_PASS=<run: python3 -c "import uuid; print(uuid.uuid4().hex)">

# Plex Configuration
PLEX_TOKEN=your_plex_token_here
PLEX_LOCAL_URL=http://localhost:32400

# Jellyfin/Emby Configuration
JELLYFIN_API_KEY=your_jellyfin_api_key_here
EMBY_OR_JELLYFIN=jellyfin  # or "emby"
```

**3. Get API keys:**
- **Plex Token**: https://support.plex.tv/hc/en-us/articles/204059436
- **Jellyfin/Emby**: Dashboard → Advanced → API Keys

**4. Edit `docker-compose.yml` volumes:**
```yaml
volumes:
  # Your media library (same for both servers)
  - /path/to/your/media:/media:ro

  # Plex database
  - plex-config:/var/lib/plexmediaserver:ro  # If Plex in Docker
  # - /var/lib/plexmediaserver:/var/lib/plexmediaserver:ro  # If native
```

**5. Generate and configure:**
```bash
# Option 1: Start from example template (recommended)
cp config.example.json config/config.json
nano config/config.json

# Option 2: Generate from scratch
docker-compose run --rm autoscan python3 scan.py sections
nano config/config.json
```

**Configure these `config.json` settings:**
- `PLEX_USER`, `PLEX_DATABASE_PATH`, `PLEX_TOKEN`
- `JELLYFIN_API_KEY`, `EMBY_OR_JELLYFIN`

**6. Start container:**
```bash
docker-compose up -d
docker-compose logs -f autoscan  # View logs
```

**How it works:**
- Single webhook → Scans **both** Plex and Jellyfin/Emby
- Each server scanned independently
- Same paths work for both servers

**✅ Done!** One webhook URL for both servers: `http://your-ip:3468/your_server_pass`

---

### Docker Common Commands

```bash
# Start container
docker-compose up -d

# Stop container
docker-compose down

# View logs
docker-compose logs -f autoscan

# Restart container
docker-compose restart autoscan

# Update to latest version
git pull
docker-compose build --no-cache
docker-compose up -d

# Execute commands in container
docker-compose exec autoscan python3 scan.py sections

# Check Plex sections
docker-compose exec autoscan python3 scan.py sections
```

---

## 💻 Native Installation

**For users who prefer traditional Python installation on VPS or custom setups.**

**Prerequisites:**
- Ubuntu/Debian (or similar Linux distribution)
- Python 3.7+ installed
- Curl installed

---

### Option A: Native + Plex Only

**Perfect for:** VPS or bare-metal Plex servers

**1. Install system dependencies:**
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv curl git
```

**2. Clone repository:**
```bash
cd /opt
sudo git clone https://github.com/neilcorp2kx/plex_emby_jellyfin_autoscan.git
sudo chown -R $USER:$USER plex_emby_jellyfin_autoscan
cd plex_emby_jellyfin_autoscan
```

**3. Setup Python environment:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**4. Create `.env` file:**
```bash
cp .env.example .env
nano .env
```

**Add these values:**
```bash
# Required: Security keys
SECRET_KEY=<run: python3 -c "import secrets; print(secrets.token_hex(32))">
SERVER_PASS=<run: python3 -c "import uuid; print(uuid.uuid4().hex)">

# Plex Configuration
PLEX_TOKEN=your_plex_token_here
PLEX_LOCAL_URL=http://localhost:32400

# Leave blank (not using Jellyfin/Emby)
JELLYFIN_API_KEY=
EMBY_OR_JELLYFIN=
```

**5. Get Plex Token:**
```bash
# Run included script
/opt/plex_emby_jellyfin_autoscan/scripts/plex_token.sh

# Or visit: https://support.plex.tv/hc/en-us/articles/204059436
```

**6. Generate and configure:**
```bash
# Option 1: Start from example template (recommended)
cp config.example.json config/config.json
nano config/config.json

# Option 2: Generate from scratch
python3 scan.py sections
nano config/config.json
```

**Configure these `config.json` settings:**
- `PLEX_USER`: `"plex"`
- `PLEX_DATABASE_PATH`: `/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db`
- `PLEX_SCANNER`: `/usr/lib/plexmediaserver/Plex\\ Media\\ Scanner`
- `PLEX_TOKEN`: Use value from step 5
- Leave `JELLYFIN_API_KEY` and `EMBY_OR_JELLYFIN` at defaults

**7. Setup systemd service:**
```bash
sudo cp system/plex_autoscan.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable plex_autoscan.service
sudo systemctl start plex_autoscan.service
```

**8. Check status:**
```bash
sudo systemctl status plex_autoscan.service
```

**✅ Done!** Webhook URL: `http://your-server-ip:3468/your_server_pass`

---

### Option B: Native + Jellyfin/Emby Only

**Perfect for:** VPS or bare-metal Jellyfin/Emby servers

**1. Install system dependencies:**
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv curl git
```

**2. Clone repository:**
```bash
cd /opt
sudo git clone https://github.com/neilcorp2kx/plex_emby_jellyfin_autoscan.git
sudo chown -R $USER:$USER plex_emby_jellyfin_autoscan
cd plex_emby_jellyfin_autoscan
```

**3. Setup Python environment:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**4. Create `.env` file:**
```bash
cp .env.example .env
nano .env
```

**Add these values:**
```bash
# Required: Security keys
SECRET_KEY=<run: python3 -c "import secrets; print(secrets.token_hex(32))">
SERVER_PASS=<run: python3 -c "import uuid; print(uuid.uuid4().hex)">

# Jellyfin/Emby Configuration
JELLYFIN_API_KEY=your_jellyfin_api_key_here
EMBY_OR_JELLYFIN=jellyfin  # or "emby"

# Leave blank (not using Plex)
PLEX_TOKEN=
PLEX_LOCAL_URL=
```

**5. Get Jellyfin/Emby API Key:**
- **Jellyfin**: Dashboard → Advanced → API Keys → New API Key
- **Emby**: Dashboard → Advanced → API Keys → New API Key

**6. Generate and configure:**
```bash
# Option 1: Start from example template (recommended)
cp config.example.json config/config.json
nano config/config.json

# Option 2: Generate from scratch
python3 scan.py sections
nano config/config.json
```

**Configure these `config.json` settings:**
- `JELLYFIN_API_KEY`: Your API key from step 5
- `EMBY_OR_JELLYFIN`: `"jellyfin"` or `"emby"`
- Leave Plex settings at defaults (will be ignored)

**7. Setup systemd service:**
```bash
sudo cp system/plex_autoscan.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable plex_autoscan.service
sudo systemctl start plex_autoscan.service
```

**8. Check status:**
```bash
sudo systemctl status plex_autoscan.service
```

**Important Notes:**
- **Partial scan**: New episodes or upgrades = fast scan ✅
- **Full scan**: New folders = full library scan (Jellyfin/Emby limitation)

**✅ Done!** Webhook URL: `http://your-server-ip:3468/your_server_pass`

---

### Option C: Native + Both Plex & Jellyfin/Emby

**Perfect for:** Running both media servers on the same machine

**1. Install system dependencies:**
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv curl git
```

**2. Clone repository:**
```bash
cd /opt
sudo git clone https://github.com/neilcorp2kx/plex_emby_jellyfin_autoscan.git
sudo chown -R $USER:$USER plex_emby_jellyfin_autoscan
cd plex_emby_jellyfin_autoscan
```

**3. Setup Python environment:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**4. Create `.env` file:**
```bash
cp .env.example .env
nano .env
```

**Add these values:**
```bash
# Required: Security keys
SECRET_KEY=<run: python3 -c "import secrets; print(secrets.token_hex(32))">
SERVER_PASS=<run: python3 -c "import uuid; print(uuid.uuid4().hex)">

# Plex Configuration
PLEX_TOKEN=your_plex_token_here
PLEX_LOCAL_URL=http://localhost:32400

# Jellyfin/Emby Configuration
JELLYFIN_API_KEY=your_jellyfin_api_key_here
EMBY_OR_JELLYFIN=jellyfin  # or "emby"
```

**5. Get API keys:**
- **Plex Token**: Run `/opt/plex_emby_jellyfin_autoscan/scripts/plex_token.sh`
- **Jellyfin/Emby**: Dashboard → Advanced → API Keys

**6. Generate and configure:**
```bash
# Option 1: Start from example template (recommended)
cp config.example.json config/config.json
nano config/config.json

# Option 2: Generate from scratch
python3 scan.py sections
nano config/config.json
```

**Configure these `config.json` settings:**
- `PLEX_USER`, `PLEX_DATABASE_PATH`, `PLEX_SCANNER`, `PLEX_TOKEN`
- `JELLYFIN_API_KEY`, `EMBY_OR_JELLYFIN`

**7. Setup systemd service:**
```bash
sudo cp system/plex_autoscan.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable plex_autoscan.service
sudo systemctl start plex_autoscan.service
```

**8. Check status:**
```bash
sudo systemctl status plex_autoscan.service
```

**How it works:**
- Single webhook → Scans **both** Plex and Jellyfin/Emby
- Each server scanned independently
- Same paths work for both servers

**✅ Done!** One webhook URL for both: `http://your-server-ip:3468/your_server_pass`

---

### Native Common Commands

```bash
# Check service status
sudo systemctl status plex_autoscan.service

# View logs
sudo journalctl -u plex_autoscan.service -f

# Restart service
sudo systemctl restart plex_autoscan.service

# Stop service
sudo systemctl stop plex_autoscan.service

# Update to latest version
cd /opt/plex_emby_jellyfin_autoscan
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart plex_autoscan.service

# Manual run (for testing)
source venv/bin/activate
python3 scan.py server

# Check Plex sections
source venv/bin/activate
python3 scan.py sections
```

## Security Best Practices

**Modern Security Features (2024/2025):**

This version includes comprehensive security enhancements designed to protect your media server infrastructure:

- **Environment Variable Support**: Store sensitive credentials in `.env` file instead of `config.json`
- **Input Validation**: All user inputs are validated and sanitized using the `validators.py` module
- **Path Traversal Protection**: Prevents directory traversal attacks (e.g., `../`, null bytes)
- **Session Security**: Secure cookie configuration with HttpOnly and SameSite flags
- **CSRF Protection**: Cross-Site Request Forgery protection with Flask-WTF
- **Security Headers**: Optional HTTP security headers with Flask-Talisman
- **Database Connection Pooling**: Improved performance and resource management
- **Jinja2 Templates**: Automatic XSS protection for web interface

### Secret Management

**Environment Variables (.env file):**

The `.env` file should contain your sensitive credentials:

```bash
# Plex Configuration
PLEX_TOKEN=your_plex_token_here
PLEX_LOCAL_URL=http://localhost:32400

# Jellyfin/Emby Configuration
JELLYFIN_API_KEY=your_jellyfin_api_key_here
EMBY_OR_JELLYFIN=jellyfin

# Server Security (REQUIRED - generate unique values)
SECRET_KEY=generate_random_secret_key_here
SERVER_PASS=generate_random_32_character_hex_string

# Generate secure keys:
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
python3 -c "import secrets; print('SERVER_PASS=' + secrets.token_hex(16))"
```

**Critical Security Rules:**

1. **Never commit secrets to version control**
   - The `.env` file is already in `.gitignore`
   - Always use `.env.example` as a template
   - Never put real secrets in `config.json`

2. **Generate strong, unique secrets**
   - Use cryptographically secure random generators
   - Never reuse secrets across applications
   - Store secrets in a password manager

3. **Restrict network access**
   - Use firewall rules to limit access to port 3468
   - Consider using a reverse proxy with authentication
   - For local-only use, set `SERVER_IP: "127.0.0.1"`

4. **Use read-only volume mounts**
   ```yaml
   volumes:
     - /path/to/media:/media:ro  # Read-only flag prevents writes
     - plex-config:/var/lib/plexmediaserver:ro  # Read-only Plex DB access
   ```

5. **Run as non-root user**
   ```yaml
   environment:
     - PUID=1000  # Your user ID
     - PGID=1000  # Your group ID
   ```

6. **Keep secrets out of config.json**
   ```json
   {
     "PLEX_TOKEN": "",  // Leave empty, use .env instead
     "SERVER_PASS": "",  // Leave empty, use .env instead
     "JELLYFIN_API_KEY": ""  // Leave empty, use .env instead
   }
   ```

### HTTPS and Production Security

**For Internet-Facing Deployments:**

Enable additional security features in your `.env` file:

```bash
# Enable HTTPS enforcement and security headers
ENABLE_TALISMAN=true
FORCE_HTTPS=true
SESSION_COOKIE_SECURE=true
```

**Recommendation:** Use a reverse proxy (nginx, Traefik, Caddy) with:
- Valid SSL/TLS certificates (Let's Encrypt)
- Rate limiting to prevent abuse
- HTTP authentication for additional protection
- Geographic restrictions if applicable

### File Permission Security

**Docker installations:**
```bash
# Set proper ownership
sudo chown -R 1000:1000 config/
sudo chown -R 1000:1000 database/

# Secure the .env file
chmod 600 .env
```

**Native installations:**
```bash
# Set proper ownership
sudo chown -R $USER:$USER /opt/plex_emby_jellyfin_autoscan/

# Secure the .env file
chmod 600 .env

# Restrict config directory
chmod 700 config/
```

### Regular Security Maintenance

**Monthly Tasks:**
- Review access logs for suspicious activity
- Check for dependency security updates: `pip list --outdated`
- Verify firewall rules are still appropriate

**Quarterly Tasks:**
- Rotate SECRET_KEY using the key rotation workflow (see below)
- Update all dependencies: `pip install -r requirements.txt --upgrade`
- Review and update security configurations

**Annually:**
- Conduct security audit of configuration
- Review and update access controls
- Consider penetration testing for internet-facing deployments

### Security Incident Response

If you suspect a security breach:

1. **Immediately rotate all secrets**
   ```bash
   # Generate new secrets
   python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
   python3 -c "import secrets; print('SERVER_PASS=' + secrets.token_hex(16))"

   # Update .env file
   nano .env

   # Restart service
   sudo systemctl restart plex_autoscan.service
   # OR for Docker
   docker-compose restart autoscan
   ```

2. **Review access logs**
   ```bash
   # Docker
   docker-compose logs autoscan | grep -i "error\|unauthorized\|forbidden"

   # Native
   sudo journalctl -u plex_autoscan.service | grep -i "error\|unauthorized\|forbidden"
   ```

3. **Check for unauthorized changes**
   ```bash
   # Verify configuration files
   git status
   git diff
   ```

4. **Update security measures**
   - Change all API keys (Plex, Jellyfin/Emby)
   - Review firewall rules
   - Enable additional security features (Talisman, HTTPS)
   - Consider network isolation

**Session Management:**
- Sessions automatically refresh on each request (extends the 1-hour lifetime)
- Supports graceful secret key rotation without invalidating existing sessions
- See "Secret Key Rotation" section below for key rotation workflow

## Secret Key Rotation

To rotate your SECRET_KEY without invalidating existing user sessions, follow this workflow:

**Step 1: Generate a new secret key**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Step 2: Update your .env file**
```bash
# Move your current SECRET_KEY to SECRET_KEY_FALLBACKS
SECRET_KEY=new_generated_key_here
SECRET_KEY_FALLBACKS=old_key_here

# For multiple old keys, use comma separation:
# SECRET_KEY_FALLBACKS=old_key_1,old_key_2,old_key_3
```

**Step 3: Restart the service**
```bash
sudo systemctl restart plex_autoscan.service
```

**How it works:**
- New sessions are signed with the new SECRET_KEY
- Existing sessions signed with old keys remain valid (using SECRET_KEY_FALLBACKS)
- After all old sessions expire (1 hour by default), you can remove the fallback keys
- Recommended: Keep fallback keys for 24-48 hours to avoid disrupting active users

**Best Practices:**
- Rotate keys regularly (quarterly or after suspected compromise)
- Keep no more than 2-3 fallback keys to limit complexity
- Remove fallback keys once all sessions have naturally expired
- Document key rotation dates in a secure location


# Troubleshooting

Common issues and their solutions for Docker and Native installations.

## Container Fails to Start (JSONDecodeError)

**Symptoms:**
- Docker container exits immediately after starting
- Logs show `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`

**Solution:**
This issue was fixed in recent versions. Update to the latest version:

```bash
cd /path/to/plex_emby_jellyfin_autoscan
git pull
docker-compose build --no-cache
docker-compose up -d
```

**Reference:** Issue #23

## Container Status: Unhealthy

**Symptoms:**
- Docker container shows "unhealthy" status: `docker ps` shows `(unhealthy)`
- Application may not respond to webhooks

**Solution:**

1. Check healthcheck logs:
   ```bash
   docker-compose logs -f autoscan | grep healthcheck
   ```

2. Verify SERVER_PASS is set correctly:
   ```bash
   # Check your .env file
   cat .env | grep SERVER_PASS

   # Test the healthcheck manually
   docker-compose exec autoscan curl -f http://localhost:3468/YOUR_SERVER_PASS || exit 1
   ```

3. Common fixes:
   - Ensure `SERVER_PASS` in `.env` matches your webhook URL
   - Restart the container: `docker-compose restart autoscan`
   - Regenerate config: `docker-compose run --rm autoscan python3 scan.py sections`

## Permission Errors

**Symptoms:**
- `PermissionError: [Errno 13] Permission denied`
- Container cannot access media files or Plex database

**Solution:**

1. Verify PUID/PGID match your user:
   ```bash
   # Find your user ID and group ID
   id $USER

   # Output: uid=1000(username) gid=1000(username)
   ```

2. Update `docker-compose.yml`:
   ```yaml
   environment:
     - PUID=1000  # Use your uid from above
     - PGID=1000  # Use your gid from above
   ```

3. Fix file permissions:
   ```bash
   # For config directory
   sudo chown -R 1000:1000 config/

   # For database directory
   sudo chown -R 1000:1000 database/
   ```

4. Restart container:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Scans Not Triggering

**Symptoms:**
- Webhooks from Sonarr/Radarr/Lidarr are not triggering scans
- No entries in Plex Autoscan logs

**Solution:**

1. Verify webhook URL format:
   ```
   http://your-server-ip:3468/your_server_pass
   ```

2. Test webhook manually:
   ```bash
   curl -d "eventType=Manual&filepath=/data/Movies/Test Movie (2024)/movie.mkv" \
     http://your-server-ip:3468/your_server_pass
   ```

3. Check container logs:
   ```bash
   docker-compose logs -f autoscan
   ```

4. Common issues:
   - **Wrong SERVER_PASS**: Verify it matches between `.env` and webhook URL
   - **Firewall blocking**: Check port 3468 is accessible
   - **Path mapping issues**: Verify `SERVER_PATH_MAPPINGS` in `config.json`
   - **Container not running**: Check status with `docker ps`

## Plex Database Not Accessible

**Symptoms:**
- `IOError: [Errno 2] No such file or directory: '/var/lib/plexmediaserver/.../com.plexapp.plugins.library.db'`
- Scans work but database operations fail

**Solution:**

The database path depends on your Plex container image:

### LinuxServer.io Plex Image

```yaml
# docker-compose.yml
volumes:
  - plex-config:/config:ro

# config.json
"PLEX_DATABASE_PATH": "/config/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db",
"PLEX_SUPPORT_DIR": "/config/Library/Application\\ Support",
"PLEX_USER": "abc"
```

### Official PlexInc Image

```yaml
# docker-compose.yml
volumes:
  - plex-config:/var/lib/plexmediaserver:ro

# config.json
"PLEX_DATABASE_PATH": "/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db",
"PLEX_SUPPORT_DIR": "/var/lib/plexmediaserver/Library/Application\\ Support",
"PLEX_USER": "plex"
```

### Verification

```bash
# Check if database path exists in container
docker-compose exec autoscan ls -la /path/to/database/file

# Check Plex container volume mounts
docker inspect plex | grep -A 10 Mounts
```

## Media Files Not Found

**Symptoms:**
- Scans complete but Plex doesn't show new media
- Logs show "File not found" or timeout waiting for file

**Solution:**

1. Verify path mappings in `config.json`:
   ```json
   "SERVER_PATH_MAPPINGS": {
     "/data/Movies/": [
       "/movies/"
     ]
   }
   ```

2. Check file exist path mappings:
   ```json
   "SERVER_FILE_EXIST_PATH_MAPPINGS": {
     "/actual/path/on/host/": [
       "/path/from/plex/container/"
     ]
   }
   ```

3. Test file accessibility:
   ```bash
   # From host
   ls -la /path/to/media/file

   # From container
   docker-compose exec autoscan ls -la /data/Movies/
   ```

4. Verify volume mounts in `docker-compose.yml`:
   ```yaml
   volumes:
     - /host/path/media:/data/Movies:ro
   ```

## Connection Refused / Network Errors

**Symptoms:**
- `Connection refused` when accessing webhook URL
- Cannot connect to Plex server

**Solution:**

1. Verify container is running:
   ```bash
   docker ps | grep autoscan
   ```

2. Check port mapping:
   ```bash
   docker-compose ps
   # Should show: 0.0.0.0:3468->3468/tcp
   ```

3. Test from host:
   ```bash
   curl http://localhost:3468/your_server_pass
   ```

4. Check firewall rules:
   ```bash
   # Ubuntu/Debian
   sudo ufw status
   sudo ufw allow 3468/tcp

   # Check if port is listening
   sudo netstat -tlnp | grep 3468
   ```

5. Verify `SERVER_IP` in `config.json`:
   ```json
   "SERVER_IP": "0.0.0.0"  # Allow external connections
   ```

## High CPU/Memory Usage

**Symptoms:**
- Container consuming excessive resources
- System slowdown during scans

**Solution:**

1. Adjust scan delay to reduce frequency:
   ```json
   "SERVER_SCAN_DELAY": 300  # Increase from 180 to 300 seconds
   ```

2. Disable analyze if not needed:
   ```json
   "PLEX_ANALYZE_TYPE": "off"  # or "basic" instead of "deep"
   ```

3. Limit concurrent scans:
   ```json
   "PLEX_WAIT_FOR_EXTERNAL_SCANNERS": true
   ```

4. Monitor container resources:
   ```bash
   docker stats autoscan
   ```

## Logs Not Showing / Empty Logs

**Symptoms:**
- `docker-compose logs` shows no output
- Cannot debug issues

**Solution:**

1. Check container status:
   ```bash
   docker-compose ps
   ```

2. View real-time logs:
   ```bash
   docker-compose logs -f --tail=100 autoscan
   ```

3. Check if logging to file:
   ```bash
   docker-compose exec autoscan ls -la /config/
   ```

4. Increase log verbosity (if available in future versions):
   ```bash
   # Add to docker-compose.yml environment section
   - LOG_LEVEL=DEBUG
   ```

## Getting Additional Help

If your issue is not covered above:

1. **Check existing issues**: https://github.com/neilcorp2kx/plex_emby_jellyfin_autoscan/issues
2. **Gather diagnostic information**:
   ```bash
   # Container status
   docker-compose ps

   # Recent logs
   docker-compose logs --tail=100 autoscan

   # Configuration (remove sensitive data)
   cat config/config.json
   ```
3. **Create a new issue** with:
   - Detailed description of the problem
   - Steps to reproduce
   - Log output
   - Docker compose file (remove secrets)
   - Configuration file (remove secrets)

---

# Configuration

_Note: Changes to config file or `.env` file require a restart of the Plex Autoscan service: `sudo systemctl restart plex_autoscan.service`._

## Configuration Priority

Settings are loaded in the following priority order (highest to lowest):

1. **Environment Variables** (from `.env` file or system environment)
2. **config.json** file
3. **Default Values**

**Best Practice:**
- **Secrets** (API keys, tokens, passwords) should be stored in the `.env` file
- **Non-sensitive configuration** (paths, settings) can be stored in `config.json`
- **Never commit** `.env` file to version control

**Example:**
```bash
# .env file (secrets only)
SECRET_KEY=abc123...
SERVER_PASS=def456...
PLEX_TOKEN=ghi789...
JELLYFIN_API_KEY=jkl012...

# config.json (leave secrets empty)
"PLEX_TOKEN": "",  # Will use value from .env
"SERVER_PASS": "",  # Will use value from .env
```

This approach keeps your secrets secure while maintaining readable configuration files.

## Example

```json
{
  "DOCKER_NAME": "plex",
  "JELLYFIN_API_KEY": "",
  "EMBY_OR_JELLYFIN": "jellyfin",
  "GOOGLE": {
    "ENABLED": false,
    "CLIENT_ID": "",
    "CLIENT_SECRET": "",
    "ALLOWED": {
      "FILE_PATHS": [],
      "FILE_EXTENSIONS": true,
      "FILE_EXTENSIONS_LIST": [
        "webm","mkv","flv","vob","ogv","ogg","drc","gif",
        "gifv","mng","avi","mov","qt","wmv","yuv","rm",
        "rmvb","asf","amv","mp4","m4p","m4v","mpg","mp2",
        "mpeg","mpe","mpv","m2v","m4v","svi","3gp","3g2",
        "mxf","roq","nsv","f4v","f4p","f4a","f4b","mp3",
        "flac","ts"
      ],
      "MIME_TYPES": true,
      "MIME_TYPES_LIST": [
        "video"
      ]
    },
    "TEAMDRIVE": false,
    "TEAMDRIVES": [],
    "POLL_INTERVAL": 60,
    "SHOW_CACHE_LOGS": false
  },
  "PLEX_ANALYZE_DIRECTORY": true,
  "PLEX_ANALYZE_TYPE": "basic",
  "PLEX_FIX_MISMATCHED": false,
  "PLEX_FIX_MISMATCHED_LANG": "en",
  "PLEX_DATABASE_PATH": "/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db",
  "PLEX_EMPTY_TRASH": false,
  "PLEX_EMPTY_TRASH_CONTROL_FILES": [
    "/mnt/unionfs/mounted.bin"
  ],
  "PLEX_EMPTY_TRASH_MAX_FILES": 100,
  "PLEX_EMPTY_TRASH_ZERO_DELETED": false,
  "PLEX_LD_LIBRARY_PATH": "/usr/lib/plexmediaserver/lib",
  "PLEX_SCANNER": "/usr/lib/plexmediaserver/Plex\\ Media\\ Scanner",
  "PLEX_SUPPORT_DIR": "/var/lib/plexmediaserver/Library/Application\\ Support",
  "PLEX_USER": "plex",
  "PLEX_TOKEN": "",
  "PLEX_LOCAL_URL": "http://localhost:32400",
  "PLEX_CHECK_BEFORE_SCAN": false,
  "PLEX_WAIT_FOR_EXTERNAL_SCANNERS": true,
  "RCLONE": {
    "BINARY": "",
    "CONFIG": "",
    "CRYPT_MAPPINGS": {
    },
    "RC_CACHE_REFRESH": {
      "ENABLED": false,  
      "FILE_EXISTS_TO_REMOTE_MAPPINGS": {
        "Media/": [
            "/mnt/rclone/Media/"
        ]      
      },
      "RC_URL": "http://localhost:5572"
    }
  },
  "RUN_COMMAND_BEFORE_SCAN": "",
  "RUN_COMMAND_AFTER_SCAN": "",
  "SERVER_ALLOW_MANUAL_SCAN": false,
  "SERVER_FILE_EXIST_PATH_MAPPINGS": {
      "/mnt/unionfs/media/": [
          "/data/"
      ]
  },
  "SERVER_IGNORE_LIST": [
    "/.grab/",
    ".DS_Store",
    "Thumbs.db"
  ],
  "SERVER_IP": "0.0.0.0",
  "SERVER_MAX_FILE_CHECKS": 10,
  "SERVER_FILE_CHECK_DELAY": 60,
  "SERVER_PASS": "",
  "SERVER_PATH_MAPPINGS": {
      "/mnt/unionfs/": [
          "/home/seed/media/fused/"
      ]
  },
  "SERVER_PORT": 3468,
  "SERVER_SCAN_DELAY": 180,
  "SERVER_SCAN_FOLDER_ON_FILE_EXISTS_EXHAUSTION": false,
  "SERVER_SCAN_PRIORITIES": {
    "1": [
      "/Movies/"
    ],
    "2": [
      "/TV/"
    ]
  },
  "SERVER_USE_SQLITE": true,
  "USE_DOCKER": false,
  "USE_SUDO": false
}

```
## Basics


```json
"USE_SUDO": true
```

**⚠️ DEPRECATED (v2.1+):** `USE_SUDO` - This option is **no longer used** with API-based scanning. Kept for backward compatibility only.

<details>
<summary>Legacy Documentation (CLI Scanner Only)</summary>

This option was used with the deprecated CLI scanner method:
  - The user that ran Plex Autoscan needed to be able to sudo without a password to execute the `PLEX_SCANNER` command as `plex`.
  - Default was `true`.

**With v2.1+ API-based scanning, this is not needed.**
</details>

## Docker

**⚠️ DEPRECATED (v2.1+):** Docker-specific options below are **no longer used** with API-based scanning.

<details>
<summary>Legacy Documentation (CLI Scanner Only)</summary>

_Note: These options were used when Plex scanning required Docker CLI execution._

```json
"USE_DOCKER": true,
"DOCKER_NAME": "plex",
```

`USE_DOCKER` - Set to `true` when Plex is in a Docker container. Default is `false`.

`DOCKER_NAME` - Name of the Plex docker container. Default is `"plex"`.

**With v2.1+ API-based scanning, these are not needed. The application uses HTTP API calls to Plex instead.**
</details>


## Emby and Jellyfin Media Server Options

  - This fork is only useful if you have a Plex server installed along a Jellyfin or Emby server (otherwise I recommend you to stick to the original plex_autoscan project: https://github.com/l3uddz/plex_autoscan)

  - If you have also have a Emby/Jellyfin server you need to add your Jellyfin or Emby api key to the 3rd line of the config.json file (get it from Emby/Jellyfin Dashboard) and edit the 4th line of mentioned file accordingly..

```json
Add new episode of a tv show or a higher quality version of a movie that was already on your Emby/Jellyfin library = partial scan will be performed :)
Add a video file to a folder that was never scanned = full library scan will be perfomed :( That's how Emby/Jellyfin works...
```


## Plex Media Server

Plex Media Server options.


### Plex Basics

```json
"PLEX_USER": "plex",
"PLEX_TOKEN": "abcdefghijkl",
"PLEX_LOCAL_URL": "http://localhost:32400",
"PLEX_CHECK_BEFORE_SCAN": false,
"PLEX_WAIT_FOR_EXTERNAL_SCANNERS": true,
"PLEX_ANALYZE_TYPE": "basic",
"PLEX_ANALYZE_DIRECTORY": true,
"PLEX_FIX_MISMATCHED": false,
"PLEX_FIX_MISMATCHED_LANG": "en",
```

**⚠️ DEPRECATED (v2.1+):** `PLEX_USER` - This option is **no longer used** with API-based scanning.

<details>
<summary>Legacy Documentation (CLI Scanner Only)</summary>

User account that Plex runs as. This was only used when either `USE_SUDO` or `USE_DOCKER` was set to `true`.

  - Native Install: User account (on the host) that Plex runs as.
  - Docker Install: User account within the container.
  - Default was `"plex"`.

**With v2.1+ API-based scanning, this is not needed.**
</details>

`PLEX_TOKEN` - Plex Access Token. This is used for checking Plex's status, emptying trash, or analyzing media.

  - **Recommended:** Set via environment variable `PLEX_TOKEN` in `.env` file
  - Run the Plex Token script by [Werner Beroux](https://github.com/wernight): `/opt/plex_autoscan/scripts/plex_token.sh`.

    or

  - Visit https://support.plex.tv/hc/en-us/articles/204059436-Finding-an-authentication-token-X-Plex-Token

`PLEX_LOCAL_URL` - URL of the Plex Media Server. Can be localhost or http/https address.

  - Examples:

    - `"http://localhost:32400"` (native install; docker with port 32400 exposed)

    - `"https://plex.domain.com"` (custom domain with reverse proxy enabled)

`PLEX_CHECK_BEFORE_SCAN` - When set to `true`, check and wait for Plex to respond before processing a scan request. Default is `false`.

**⚠️ DEPRECATED (v2.1+):** `PLEX_WAIT_FOR_EXTERNAL_SCANNERS` - This option is **no longer used** with API-based scanning.

<details>
<summary>Legacy Documentation (CLI Scanner Only)</summary>

When set to `true`, wait for other Plex Media Scanner CLI processes to finish before launching a new one.

**With v2.1+ API-based scanning, the Plex server handles scan queuing automatically, so this is not needed.**
</details>

  - For multiple Plex Docker instances on a host, set this as `false`.

`PLEX_ANALYZE_TYPE` - How Plex will analyze the media files that are scanned. Options are `off`, `basic`, `deep`. `off` will disable analyzing. Default is `basic`.

`PLEX_ANALYZE_DIRECTORY` - When set to `true`, Plex will analyze all the media files in the parent folder (e.g. movie folder, season folder) vs just the newly added file. Default is `true`.

`PLEX_FIX_MISMATCHED` - When set to `true`, Plex Autoscan will attempt to fix an incorrectly matched item in Plex.

  - Plex Autoscan will compare the TVDBID/TMDBID/IMDBID sent by Sonarr/Radarr with what Plex has matched with, and if this match is incorrect, it will autocorrect the match on the item (movie file or TV episode). If the incorrect match is a duplicate entry in Plex, it will auto split the original entry before correcting the match on the new item.

  - This only works when 1) requests come from Sonarr/Radarr, 2) season folders are being used, and 3) all movies and TV shows have their own unique paths.

  - Default is `false`.

`PLEX_FIX_MISMATCHED_LANG` - What language to use for TheTVDB agent in Plex. 
 
  - Default is `"en"`.

### Plex File Locations

**⚠️ DEPRECATED (v2.1+):** Most file location options below are **no longer used** with API-based scanning.

**Still Required:**
- `PLEX_DATABASE_PATH` - Only used for trash management and section detection

**No Longer Required:**
- ~~`PLEX_LD_LIBRARY_PATH`~~ - Not needed with API scanning
- ~~`PLEX_SCANNER`~~ - Not needed with API scanning
- ~~`PLEX_SUPPORT_DIR`~~ - Not needed with API scanning

<details>
<summary>Legacy Documentation (CLI Scanner Only)</summary>

```json
"PLEX_LD_LIBRARY_PATH": "/usr/lib/plexmediaserver/lib",
"PLEX_SCANNER": "/usr/lib/plexmediaserver/Plex\\ Media\\ Scanner",
"PLEX_SUPPORT_DIR": "/var/lib/plexmediaserver/Library/Application\\ Support",
"PLEX_DATABASE_PATH": "/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db",
```

`PLEX_LD_LIBRARY_PATH` - Library path for CLI scanner (no longer used)

`PLEX_SCANNER` - Location of Plex Media Scanner binary (no longer used)

`PLEX_SUPPORT_DIR` - Location of Plex "Application Support" path (no longer used)

**With v2.1+ API-based scanning, only `PLEX_DATABASE_PATH` is still used (for trash management and section detection).**
</details>

`PLEX_DATABASE_PATH` - Location of Plex library database.

  - Native Install: `"/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"`

  - Docker Install: If Plex Autoscan is running directly on the host, this will be the path on the host. If Plex Autoscan is running inside a Plex container (e.g. https://github.com/horjulf/docker-plex_autoscan), this will be a path within the container.


### Plex Section IDs

Running the following command, will return a list of Plex Library Names and their corresponding Section IDs (sorted by alphabetically Library Name):

```shell
python scan.py sections
```

This will be in the format of:

```
SECTION ID #: LIBRARY NAME
```

Sample output:

```
 2018-06-23 08:28:27,070 -     INFO -      PLEX [140425529542400]: Using Plex Scanner
  1: Movies
  2: TV
```

### Plex Emptying Trash

When media is upgraded by Sonarr/Radarr/Lidarr, the previous files are then deleted. When Plex gets the scan request after the upgrade, the new media is added in to the library, but the previous media files would still be listed there but labeled as "unavailable".

To remedy this, a trash emptying command needs to be sent to Plex to get rid of these missing files from the library. The options below enable that to happen.


```json
"PLEX_EMPTY_TRASH": true,
"PLEX_EMPTY_TRASH_CONTROL_FILES": [
  "/mnt/unionfs/mounted.bin"
],
"PLEX_EMPTY_TRASH_MAX_FILES": 100,
"PLEX_EMPTY_TRASH_ZERO_DELETED": true,
```

`PLEX_EMPTY_TRASH` - When set to `true`, empty trash of a section after a scan.

`PLEX_EMPTY_TRASH_CONTROL_FILES` - Only empty trash when this file exists. Useful when media files, located elsewhere, is mounted on the Plex Server host. Can be left blank if not needed.

`PLEX_EMPTY_TRASH_MAX_FILES` - The maximum amount of missing files to remove from Plex at one emptying trash request. If there are more missing files than the number listed, the emptying trash request is aborted. This is particularly useful when externally mounted media temporarily dismounts and a ton of files go "missing" in Plex. Default is `100`.

`PLEX_EMPTY_TRASH_ZERO_DELETED` - When set to `true`, Plex Autoscan will always empty the trash on the scanned section, even if there are 0 missing files. If `false`, trash will only be emptied when the database returns more than 0 deleted items. Default is `false`.


## Plex Autoscan Server

### Basics

```json
"SERVER_IP": "0.0.0.0",
"SERVER_PASS": "9c4b81fe234e4d6eb9011cefe514d915",
"SERVER_PORT": 3468,
"SERVER_SCAN_DELAY": 180,
"SERVER_USE_SQLITE": true
```

`SERVER_IP` -  Server IP that Plex Autoscan will listen on. Default is `0.0.0.0`.

  - `0.0.0.0` - Allow remote access (e.g. Sonarr/Radarr/Lidarr running on another/remote server).

  - `127.0.0.1` - Local access only.

`SERVER_PORT` - Port that Plex Autoscan will listen on.

`SERVER_PASS` - Plex Autoscan password. Used to authenticate requests from Sonarr/Radarr/Lidarr.

  - **Recommended:** Set via environment variable `SERVER_PASS` in `.env` file
  - Generate a secure random value: `python3 -c "import uuid; print(uuid.uuid4().hex)"`
  - Default is a random 32 character string generated during config build if not set
  - Your webhook URL will look like: http://ipaddress:3468/server_pass (or http://localhost:3468/server_pass if local only).

`SERVER_SCAN_DELAY` - How long (in seconds) Plex Autoscan will wait before sending a scan request to Plex.

  - This is useful, for example, when you want Plex Autoscan to wait for more episodes of the same TV show to come in before scanning the season folder, resulting in less work for Plex to do by not scanning the same folder multiple times. This works especially well with `SERVER_USE_SQLITE` enabled.

`SERVER_USE_SQLITE` - Option to enable a database to store queue requests. Default is `true`.

- The benefits to using this are:

  1. Queue will be restored on Plex Autoscan restart, and

  2. Multiple requests to the same folder can be merged into a single folder scan.

- Example log:

  ```
  Already processing '/data/TV/TV-Anime/Persona 5 the Animation/Season 1/Persona 5 the Animation - s01e01 - I am thou, thou art I.mkv' from same folder, aborting adding an extra scan request to the queue.
  Scan request from Sonarr for '/data/TV/TV-Anime/Persona 5 the Animation/Season 1/Persona 5 the Animation - s01e01 - I am thou, thou art I.mkv', sleeping for 180 seconds...
  ```

  The `180` seconds in the example above are from the `SERVER_SCAN_DELAY`, if any more requests come in during this time, the scan request will be delayed by another `180` seconds.

### Server - Path Mappings

List of paths that will be remapped before being scanned by Plex.

This is particularly useful when receiving scan requests, from a remote Sonarr/Radarr/Lidarr installation, that has different paths for the media.

#### Native Install

Format:
```
"SERVER_PATH_MAPPINGS": {
    "/path/on/local/plex/host/": [  <--- Plex Library path
        "/path/on/sonarr/host/"  <--- Sonarr root path
    ]
},
```

_Note: This format is used regardless of whether Sonarr is on the same server as Plex or not._

Example:

```json
"SERVER_PATH_MAPPINGS": {
    "/mnt/unionfs/": [
        "/home/seed/media/fused/"
    ]
},
```

#### Docker Install

Format:

```
"SERVER_PATH_MAPPINGS": {
    "/path/in/plex/container/": [  <--- Plex Library path
        "/path/from/sonarr/container/"  <--- Sonarr root path
    ]
},
```

Example:

```json
"SERVER_PATH_MAPPINGS": {
  "/data/Movies/": [
    "/movies/"
  ]
}
```



If the filepath that was reported to Plex Autoscan by Radarr was `/home/seed/media/fused/Movies/Die Hard/Die Hard.mkv` then the path that would be scanned by Plex would be `/mnt/unionfs/Movies/Die Hard/Die Hard.mkv`.


#### Multiple Paths

You can also have more than one folder paths pointing to a single one.

Example:

```json
"SERVER_PATH_MAPPINGS": {
  "/data/Movies/": [
    "/media/movies/",
    "/local/movies/"
  ]
}
```


### Server File Checks

After a `SERVER_SCAN_DELAY`, Plex Autoscan will check to see if file exists before sending a scan request to Plex.


```json
"SERVER_MAX_FILE_CHECKS": 10,
"SERVER_FILE_CHECK_DELAY": 60,
"SERVER_SCAN_FOLDER_ON_FILE_EXISTS_EXHAUSTION": false,
```

`SERVER_MAX_FILE_CHECKS` -  The number specifies how many times this check will occur, before giving up. If set to `0`, this check will not occur, and Plex Autoscan will simply send the scan request after the `SERVER_SCAN_DELAY`. Default is `10`.

`SERVER_FILE_CHECK_DELAY` - Delay in seconds between two file checks. Default is `60`.

`SERVER_SCAN_FOLDER_ON_FILE_EXISTS_EXHAUSTION` - Plex Autoscan will scan the media folder when the file exist checks (as set above) are exhausted. Default is `false`.

### Server File Exists - Path Mappings

List of paths that will be remapped before file exist checks are done.

This is particularly useful when using Docker, since the folder being scanned by the Plex container, may be different to the path on the host system running Plex Autoscan.


Format:
```json
"SERVER_FILE_EXIST_PATH_MAPPINGS": {
    "/actual/path/on/host/": [
        "/path/from/plex/container/"
    ]
},
```


Example:
```json
"SERVER_FILE_EXIST_PATH_MAPPINGS": {
    "/mnt/unionfs/media/": [
        "/data/"
    ]
},
```


You can leave this empty if it is not required:
```json
"SERVER_FILE_EXIST_PATH_MAPPINGS": {
},
```

### Misc

```json
"RUN_COMMAND_BEFORE_SCAN": "",
"RUN_COMMAND_AFTER_SCAN": "",
"SERVER_ALLOW_MANUAL_SCAN": false,
"SERVER_IGNORE_LIST": [
  "/.grab/",
  ".DS_Store",
  "Thumbs.db"
],
"SERVER_SCAN_PRIORITIES": {
  "1": [
    "/Movies/"
  ],
  "2": [
    "/TV/"
  ]
},
```


`RUN_COMMAND_BEFORE_SCAN` - If a command is supplied, it is executed before the Plex Media Scanner command.

`RUN_COMMAND_AFTER_SCAN` - If a command is supplied, it is executed after the Plex Media Scanner, Empty Trash and Analyze commands.

`SERVER_ALLOW_MANUAL_SCAN` - When enabled, allows GET requests to the webhook URL to allow manual scans on a specific filepath. Default is `false`.

  - All path mappings and section ID mappings, of the server, apply.

  - This is also a good way of testing your configuration, manually.

  - **Security Note:** The manual scan interface now includes input validation and path traversal protection to prevent security vulnerabilities.

  - To send a manual scan, you can either:

    - Visit your webhook url in a browser (e.g. http://ipaddress:3468/0c1fa3c9867e48b1bb3aa055cb86), and fill in the path to scan using the secure Jinja2 template interface.

      or

    - Initiate a scan via HTTP (e.g. curl):

      ```
      curl -d "eventType=Manual&filepath=/mnt/unionfs/Media/Movies/Shut In (2016)/Shut In (2016) - Bluray-1080p.x264.DTS-GECKOS.mkv" http://ipaddress:3468/0c1fa3c9867e48b1bb3aa055cb86`
      ```

`SERVER_IGNORE_LIST` - List of paths or filenames to ignore when a requests is sent to Plex Autoscan manually (see above). Case sensitive.

  - For example, `curl -d "eventType=Manual&filepath=/mnt/unionfs/Media/Movies/Thumbs.db" http://ipaddress:3468/0c1fa3c9867e48b1bb3aa055cb86` would be ignored if `Thumbs.db` was in the ignore list.


`SERVER_SCAN_PRIORITIES` - What paths are picked first when multiple scan requests are being processed.

  - Format:
    ```json
    "SERVER_SCAN_PRIORITIES": {
      "PRIORITY LEVEL#": [
        "/path/to/library/in/Plex"
      ],
    },
    ```

## Google Drive Monitoring

As mentioned earlier, Plex Autoscan can monitor Google Drive for changes. It does this by utilizing a proactive cache (vs building a cache from start to end).

Once a change is detected, the file will be checked against the Plex database to make sure this is not already there. If this match comes back negative, a scan request for the parent folder is added into the process queue, and if that parent folder is already in the process queue, the duplicate request will be ignored.

```json
"GOOGLE": {
  "ENABLED": false,
  "CLIENT_ID": "",
  "CLIENT_SECRET": "",
  "ALLOWED": {
    "FILE_PATHS": [],
    "FILE_EXTENSIONS": true,
    "FILE_EXTENSIONS_LIST": [
      "webm","mkv","flv","vob","ogv","ogg","drc","gif",
      "gifv","mng","avi","mov","qt","wmv","yuv","rm",
      "rmvb","asf","amv","mp4","m4p","m4v","mpg","mp2",
      "mpeg","mpe","mpv","m2v","m4v","svi","3gp","3g2",
      "mxf","roq","nsv","f4v","f4p","f4a","f4b","mp3",
      "flac","ts"
    ],
    "MIME_TYPES": true,
    "MIME_TYPES_LIST": [
      "video"
    ]
  },
  "TEAMDRIVE": false,
  "TEAMDRIVES": [],
  "POLL_INTERVAL": 60,
  "SHOW_CACHE_LOGS": false
},
"RCLONE": {
  "BINARY": "/usr/bin/rclone",
  "CONFIG": "/home/seed/.config/rclone/rclone.conf",
  "CRYPT_MAPPINGS": {
    "My Drive/encrypt/": [
      "gcrypt:"
    ]
  }
},
```

`ENABLED` - Enable or Disable Google Drive Monitoring. Requires one time authorization, see below.

`CLIENT_ID` - Google Drive API Client ID.

`CLIENT_SECRET` - Google Drive API Client Secret.

`ALLOWED` - Specify what paths, extensions, and mime types to whitelist.

  - `FILE_PATHS` - What paths to monitor.

    - Example ("My Drive" only):

      ```json
      "FILE_PATHS": [
        "My Drive/Media/Movies/",
        "My Drive/Media/TV/"
      ],
      ```
    - Example ("My Drive" with Teamdrives):

      ```json
      "FILE_PATHS": [
        "My Drive/Media/Movies/",
        "My Drive/Media/TV/",
        "Shared_Movies/Movies/",
        "Shared_Movies/4K_Movies/",
        "Shared_TV/TV/"
      ],
      ```    

  - `FILE_EXTENSIONS` - To filter files based on their file extensions. Default is `true`.

  - `FILE_EXTENSIONS_LIST` - What file extensions to monitor. Requires `FILE_EXTENSIONS` to be enabled.

    - Example:

      ```json
      "FILE_EXTENSIONS_LIST": [
        "webm","mkv","flv","vob","ogv","ogg","drc","gif",
        "gifv","mng","avi","mov","qt","wmv","yuv","rm",
        "rmvb","asf","amv","mp4","m4p","m4v","mpg","mp2",
        "mpeg","mpe","mpv","m2v","m4v","svi","3gp","3g2",
        "mxf","roq","nsv","f4v","f4p","f4a","f4b","mp3",
        "flac","ts"
      ],
      ```

  - `MIME_TYPES` - To filter files based on their mime types. Default is `true`.

  - `MIME_TYPES_LIST` - What file extensions to monitor. Requires `MIME_TYPES` to be enabled.

    - Example:

      ```json
      "MIME_TYPES_LIST": [
        "video"
      ]
      ```

`TEAMDRIVE` - Enable or Disable monitoring of changes inside Team Drives. Default is `false`.

- _Note: For the `TEAMDRIVE` setting to take effect, you set this to `true` and run the authorize command (see below)._


`TEAMDRIVES` - What Team Drives to monitor. Requires `TEAMDRIVE` to be enabled.

- Format:

  ```json
  "TEAMDRIVES": [
    "NAME_OF_TEAMDRIVE_1",
    "NAME_OF_TEAMDRIVE_2"
  ],
  ```

- Example:

  For 2 Teamdrives named `Shared_Movies` and `Shared_TV`.

  ```json
  "TEAMDRIVES": [
    "Shared_Movies",
    "Shared_TV"
  ],
  ```

- _Note: This is just a list of Teamdrives, not the specific paths within it._

`POLL_INTERVAL` - How often (in seconds) to check for Google Drive changes.

`SHOW_CACHE_LOGS` - Show cache messages from Google Drive. Default is `false`.

`BINARY` - Path to Rclone binary if not in standard location.

`CONFIG` - Path to Rclone config file containing Rclone Crypt remote configuration. Required for Rclone Crypt decoder.

`CRYPT_MAPPINGS` - Mapping of path (root or subfolder) of Google Drive crypt (`My Drive/` or `Team Drive Name/`) to Rclone mount name. These values enable Rclone crypt decoder.

- Example: Crypt folder on drive called `encrypt` mapped to Rclone crypt mount called `grypt:`.

  ```json
  "CRYPT_MAPPINGS": {
    "My Drive/encrypt/": [
      "gcrypt:"
    ]
  },
  ```
- Example: Crypt Teamdrive named `Shared_TV` mapped to Rclone crypt mount called `Shared_TV_crypt:`.

  ```json
  "CRYPT_MAPPINGS": {
    "Shared_TV/": [
      "Shared_TV_crypt:"
    ]
  },
  ```
---

To set this up:

1. Edit `config.json `file, to enable the Google Drive monitoring and fill in your Google Drive API Client ID and Secret.

    ```json
    "ENABLED": true,
    "CLIENT_ID": "yourclientid",
    "CLIENT_SECRET": "yourclientsecret",
    ```

1. Next, you will need to authorize Google Drive.

   ```shell
   scan.py authorize
   ```

1. Visit the link shown to get the authorization code and paste that in and hit `enter`.

    ```
    Visit https://accounts.google.com/o/oauth2/v2/auth?scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive&redirect_uri=urn%3Aietf%3Awg%3Aoauth%3A2.0%3Aoob&response_type=code&client_id=&access_type=offline and authorize against the account you wish to use
    Enter authorization code:
    ```
1. When access token retrieval is successful, you'll see this:

   ```
   2018-06-24 05:57:58,252 -     INFO -    GDRIVE [140007964366656]: Requesting access token for auth code '4/AAAfPHmX9H_kMkMasfdsdfE4r8ImXI_BddbLF-eoCOPsdfasdfHBBzffKto'
   2018-06-24 05:57:58,509 -     INFO -    GDRIVE [140007964366656]: Retrieved first access token!
   2018-06-24 05:57:58,511 -     INFO -  AUTOSCAN [140007964366656]: Access tokens were successfully retrieved!
   ```

   _Note: Message stating `Segmentation fault` at the end can be ignored._

1. You will now need to add in your Google Drive paths into `SERVER_PATH_MAPPINGS`. This will tell Plex Autoscan to map Google Drive paths to their local counter part.

   i. Native install

      - Format:

        ```json
        "SERVER_PATH_MAPPINGS": {
            "/path/on/local/host": [
                "/path/on/sonarr/host/",
                "path/on/google/drive/"
            ]
        },
        ```

        _Note 1: The Google Drive path does not start with a forward slash (` / `). Paths in My Drive will start with just `My Drive/`. and paths in a Google Teamdrive will start with `teamdrive_name/`._

        _Note 2: Foreign users of Google Drive might not see `My Drive` listed on their Google Drive. They can try using the `My Drive/...` path or see what the log shows and match it up to that. One example is `Mon\u00A0Drive/` for French users._

      - For example, if you store your files under My Drive's Media folder (`My Drive/Media/...`), the server path mappings will look like this:

        ```json
        "SERVER_PATH_MAPPINGS": {
          "/mnt/unionfs/Media/Movies/": [
            "/home/seed/media/fused/"
            "My Drive/Media/Movies/"
          ],
        },
        ```

      - For example, if you store your files under a Google Teamdrive called "shared_movies" and within a Media folder (`shared_movies/Media/...`), the server path mappings will look like this:

        ```json
        "SERVER_PATH_MAPPINGS": {
          "/mnt/unionfs/Media/Movies/": [
            "/home/seed/media/fused/"
            "shared_movies/Media/Movies/"
          ],
        },
        ```

   ii. Docker install

      - Format:

        ```json
        "SERVER_PATH_MAPPINGS": {
            "/path/in/plex/container/": [
               "/path/from/sonarr/container/",
               "path/on/google/drive/"
            ]
        },
        ```

        _Note 1: The Google Drive path does not start with a forward slash (` / `). Paths in My Drive will start with just `My Drive/`. and paths in a Google Teamdrive will start with_ `teamdrive_name/`.

        _Note 2: Foreign users of Google Drive might not see `My Drive` listed on their Google Drive. They can try using the `My Drive/...` path or see what the log shows and match it up to that. One example is `Mon\u00A0Drive/` for French users._

      - For example, if you store your files under Google Drive's My Drive Media folder (`My Drive/Media/...`) AND run Plex in a docker container, the server path mappings will look like this:

        ```json
        "SERVER_PATH_MAPPINGS": {
          "/data/Movies/": [
            "/movies/",
            "My Drive/Media/Movies/"
          ]
        }
        ```

      - For example, if you store your files under Google Drive's Teamdrive called "shared_movies" and within a Media folder (`shared_movies/Media/...`) AND run Plex in a docker container, the server path mappings will look like this:

        - Format:

          ```json
          "SERVER_PATH_MAPPINGS": {
            "/data/Movies/": [
              "/movies/",
              "NAME_OF_TEAMDRIVE/Media/Movies/"
            ]
          }
          ```

        - Example:

          ```json
          "SERVER_PATH_MAPPINGS": {
            "/data/Movies/": [
              "/movies/",
              "shared_movies/Media/Movies/"
            ]
          }
          ```

1. Rclone Crypt Support - If your mounted Google Drive is encrypted using Rclone Crypt, Plex Autoscan can also decode the filenames for processing changes. This includes drives/team drives entirely encrypted or just a subfolder i.e. in the below example only the encrypt subfolder is encrypted.

    1. Configure Rclone values. Example below:

        ```json
        "RCLONE": {
          "BINARY": "/usr/bin/rclone",
          "CONFIG": "/home/seed/.config/rclone/rclone.conf",
          "CRYPT_MAPPINGS": {
            "My Drive/encrypt/": [
               "gcrypt:"
            ]
          }
        },
        ```

    1. Disable mime type checking in your config file. This is not currently supported with Rclone Crypt Decoding. Rclone crypt encodes file paths and encrypts files causing Google Drive to reports all files in a crypt as '"mimeType": "application/octet-stream"'.

        `"MIME_TYPES": false`

    1. Add in your Rclone crypt paths on Google Drive into 'SERVER_PATH_MAPPINGS'. This will tell Plex Autoscan to map Rclone crypt paths on Google Drive to their local counter part.				

          ```json
          "SERVER_PATH_MAPPINGS": {
            "/home/seed/media/": [
            "My Drive/encrypt/"
            ]
          },
          ```

1. Google Drive Monitoring is now setup.
---


## Rclone Remote Control

_Note: This if for Rclone mounts using the "cache" or "vfs" backends._

When `RC_CACHE_REFRESH` is enabled, if a file exist check fails (as set in `SERVER_FILE_EXIST_PATH_MAPPINGS`), Plex Autoscan will keep sending an Rclone cache/expire or vfs/refresh requests, for that file's parent folder, until the file check succeeds.

For example, if the file `/mnt/unionfs/Media/A Good Movie (2000)/A Good Movie.mkv` doesn't exist locally, then a clear cache request will be sent to the remote for `A Good Movie (2000)` folder, on the Rclone remote. But if a file exist checks fails again, it will move to the parent folder and try to clear that (eg `Media`), and keep doing this until a file check exists comes back positive or checks count reaches `SERVER_MAX_FILE_CHECKS`.

```json
"RCLONE": {
  "RC_CACHE_REFRESH": {
    "ENABLED": false,
    "FILE_EXISTS_TO_REMOTE_MAPPINGS": {
      "Media/": [
        "/mnt/unionfs/Media/"
      ]
    },
    "RC_URL": "http://localhost:5572"
  }
},
```

`ENABLED` - enable or disable cache clearing.

`FILE_EXISTS_TO_REMOTE_MAPPINGS` - maps local mount path to Rclone remote one. Used during file exists checks.

- Format:

  ```json
  "FILE_EXISTS_TO_REMOTE_MAPPINGS": {
    "folder_on_rclone_remote/": [
      "/path/to/locally/mounted/folder/"
    ]
  },
  ```




`RC_URL` - URL and Port Rclone RC is set to.

# Setup

Setup instructions to connect Sonarr/Radarr/Lidarr to Plex Autoscan.

## Sonarr

1. Sonarr -> "Settings" -> "Connect".

1. Add a new "Webhook".

1. Add the following:

   1. Name: Plex Autoscan

   1. On Grab: `No`

   1. On Download: `Yes`

   1. On Upgrade:  `Yes`

   1. On Rename: `Yes`

   1. Filter Series Tags: _Leave Blank_

   1. URL: _Your Plex Autoscan Webhook URL_

   1. Method:`POST`

   1. Username: _Leave Blank_

   1. Password: _Leave Blank_

1. The settings will look like this:

    ![Sonarr Plex Autoscan](https://i.imgur.com/F8L8R3a.png)

1. Click "Save" to add Plex Autoscan.

## Radarr

1. Radarr -> "Settings" -> "Connect".

1. Add a new "Webhook".

1. Add the following:

   1. Name: Plex Autoscan

   1. On Grab: `No`

   1. On Download: `Yes`

   1. On Upgrade:  `Yes`

   1. On Rename: `Yes`

   1. Filter Movie Tags: _Leave Blank_

   1. URL: _Your Plex Autoscan Webhook URL_

   1. Method:`POST`

   1. Username: _Leave Blank_

   1. Password: _Leave Blank_

1. The settings will look like this:

    ![Radarr Plex Autoscan](https://i.imgur.com/jQJyvMA.png)

1. Click "Save" to add Plex Autoscan.


## Lidarr

1. Lidarr -> "Settings" -> "Connect".

1. Add a new "Webhook" Notification.

1. Add the following:

   1. Name: Plex Autoscan

   1. On Grab: `No`

   1. On Album Import: `No`

   1. On Track Import: `Yes`

   1. On Track Upgrade:  `Yes`

   1. On Rename: `Yes`

   1. Tags: _Leave Blank_

   1. URL: _Your Plex Autoscan Webhook URL_

   1. Method:`POST`

   1. Username: _Leave Blank_

   1. Password: _Leave Blank_

1. The settings will look like this:

    ![Radarr Plex Autoscan](https://i.imgur.com/43uZloh.png)

1. Click "Save" to add Plex Autoscan.


***

# Donate

If you find this project helpful, feel free to make a small donation to the developer:

  - [Monzo](https://monzo.me/today): Credit Cards, Apple Pay, Google Pay

  - [Beerpay](https://beerpay.io/l3uddz/traktarr): Credit Cards

  - [Paypal: l3uddz@gmail.com](https://www.paypal.me/l3uddz)

  - BTC: 3CiHME1HZQsNNcDL6BArG7PbZLa8zUUgjL
