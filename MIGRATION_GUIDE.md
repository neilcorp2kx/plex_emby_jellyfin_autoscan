# Dependency Update Migration Guide

## Overview
This guide documents the migration from 2019-era dependencies to 2024/2025 stable releases.

## Version Changes

### Core Web Framework
- **Flask**: 1.1.1 → 3.0.3 (Major version upgrade)
- **Werkzeug**: 0.16.0 → 3.0.4 (Major version upgrade)
- **Jinja2**: 2.10 → 3.1.4 (Major version upgrade)

### HTTP Client
- **requests**: 2.22.0 → 2.32.3
- **urllib3**: 1.25.7 → 2.2.2

### Database
- **peewee**: 2.10.2 → 3.17.6 (Major version upgrade)

### New Security Dependencies
- **python-dotenv**: 1.0.1 (NEW - for environment variables)
- **flask-talisman**: 1.1.0 (NEW - security headers)
- **flask-wtf**: 1.2.1 (NEW - CSRF protection)

## Breaking Changes & Required Code Updates

### 1. Peewee 3.x Changes

**Database Connection Methods:**
```python
# OLD (Peewee 2.x)
db.get_conn()
db.get_cursor()

# NEW (Peewee 3.x)
db.connection()
db.cursor()
```

**Context Managers:**
```python
# OLD
with db.execution_context():
    pass

# NEW
with db:
    pass
```

**Action Required:**
- Update `db.py` to use new connection methods
- Review all database context manager usage

### 2. Flask 3.x Changes

**Import Changes:**
```python
# OLD - Flask 2.x and earlier
from flask import json

# NEW - Flask 3.x
import json  # Use standard library
```

**Configuration:**
```python
# Some config keys have changed behavior
app.config['JSON_AS_ASCII']  # Review JSON handling
```

**Action Required:**
- Test all Flask routes
- Verify JSON serialization
- Check session handling

### 3. Werkzeug 3.x Changes

**Request/Response Objects:**
- Some deprecated methods removed
- URL parsing changes
- Security improvements enabled by default

**Action Required:**
- Test all HTTP request handling
- Verify file uploads work correctly

### 4. Requests Library

**Minimal Breaking Changes:**
- Mostly backward compatible
- Improved SSL/TLS handling
- Better timeout defaults recommended

**Action Required:**
- Add explicit timeouts to all requests
- Verify SSL certificate verification works

## Installation Steps

### 1. Backup Current Environment
```bash
pip freeze > requirements.old.txt
```

### 2. Create Virtual Environment (Recommended)
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Updated Dependencies
```bash
pip install -r requirements.txt
```

### 4. Test Installation
```bash
python -c "import flask, peewee, requests; print('All imports successful')"
```

## Testing Checklist

### Critical Functions to Test:
- [ ] Database connections and queries
- [ ] Flask server starts without errors
- [ ] HTTP requests to Plex API
- [ ] HTTP requests to Jellyfin/Emby API
- [ ] File path handling
- [ ] Google Drive integration (if enabled)
- [ ] Webhook endpoints
- [ ] Manual scan form
- [ ] Session handling

### Test Commands:
```bash
# Test database
python -c "from db import *; print('DB import successful')"

# Test Plex integration
python -c "from plex import *; print('Plex import successful')"

# Test main application
python -c "from scan import app; print('App import successful')"

# Run the application
python scan.py server
```

## Known Issues & Workarounds

### Issue 1: Peewee Database Connection
**Symptom:** `AttributeError: 'Database' object has no attribute 'get_conn'`

**Solution:** Update to use `db.connection()` instead of `db.get_conn()`

### Issue 2: Flask JSON Handling
**Symptom:** JSON serialization errors

**Solution:** Use `jsonify()` for all JSON responses

### Issue 3: Import Errors
**Symptom:** `ImportError: cannot import name 'xxx'`

**Solution:** Check the module migration in Flask/Werkzeug 3.x documentation

## Rollback Plan

If issues arise:

```bash
# Restore old requirements
cp requirements.old.txt requirements.txt

# Reinstall old versions
pip install -r requirements.txt --force-reinstall
```

## Next Steps After Migration

1. Update code for Peewee 3.x compatibility
2. Add security headers (Flask-Talisman)
3. Implement CSRF protection (Flask-WTF)
4. Move secrets to environment variables (python-dotenv)
5. Run full integration tests

## Support

- Flask 3.x Changelog: https://flask.palletsprojects.com/en/latest/changes/
- Peewee 3.x Changes: http://docs.peewee-orm.com/en/latest/peewee/changes.html
- Werkzeug 3.x Changes: https://werkzeug.palletsprojects.com/en/latest/changes/

## Related GitHub Issues

- Issue #3: Dependency updates
- Issue #1: Session security (requires Flask 3.x)
- Issue #12: Environment variables (uses python-dotenv)
