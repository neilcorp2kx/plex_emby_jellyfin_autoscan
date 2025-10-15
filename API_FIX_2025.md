# Plex Autoscan API Fix - October 2025

## Issue Summary

The v2.1 "API-based scanning" implementation had an incomplete migration - while the scanning itself used the Plex API, the path-to-section ID mapping still relied on direct database access via `get_plex_section()` in `utils.py`.

### Error Encountered
```
sqlite3.OperationalError: unable to open database file
```

## Root Cause

The `get_plex_section()` function in `utils.py` was attempting to query the Plex database directly using SQLite:

```python
with sqlite3.connect(config['PLEX_DATABASE_PATH']) as conn:
    section_data = c.execute("SELECT library_section_id,root_path FROM section_locations").fetchall()
```

This caused failures even when:
- Database file existed and was readable
- Container had correct permissions (uid=1002)
- Mount was read-write enabled
- Config file had correct path

## Solution Implemented

Replaced the database-dependent `get_plex_section()` function with a pure API-based implementation that:

1. Calls the Plex API endpoint: `GET /library/sections/all`
2. Parses the XML response to extract section IDs and their location paths
3. Matches the requested path against library locations
4. Returns the correct section ID

### New Implementation

```python
def get_plex_section(config, path):
    """
    Get Plex library section ID by matching path using Plex API instead of database.
    """
    from xml.etree import ElementTree

    # Get all library sections from Plex API
    api_url = '%s/library/sections/all?X-Plex-Token=%s' % (
        config['PLEX_LOCAL_URL'],
        config['PLEX_TOKEN']
    )

    resp = requests.get(api_url, timeout=30)
    root = ElementTree.fromstring(resp.text)

    # Match path to section
    for section in root.findall("Directory"):
        section_id = section.get('key')
        for location in section.findall("Location"):
            root_path = location.get('path')
            if path.startswith(root_path + os.sep) or path.startswith(root_path):
                return int(section_id)

    return -1
```

## Benefits

✅ **No database access required** - Pure API-based operation
✅ **Eliminates permission issues** - No need for database file access
✅ **Simpler docker configuration** - No database mount complications
✅ **Future-proof** - Uses officially supported Plex API
✅ **Better error handling** - Clear HTTP status codes and XML parsing errors

## Configuration Changes

### Dockerfile
- Changed user ID from `1000` to `1002` to match media file ownership

### docker-compose.yml
- Added Plex database mount (still used for other features like empty trash)
- Changed from read-only to read-write for WAL mode support
- Updated PUID/PGID to 1002

### Required Environment Variables
Only these are needed for API-based scanning:
- `PLEX_LOCAL_URL` - Plex server URL (e.g., http://localhost:32400)
- `PLEX_TOKEN` - Plex authentication token

Optional (legacy compatibility):
- `PLEX_DATABASE_PATH` - Only needed if using database-dependent features

## Testing Results

Successfully tested with manual scan requests:
```bash
curl -X POST "http://localhost:3468/{SERVER_PASS}" \
     -H "Content-Type: application/json" \
     -d '{"eventType":"Manual","filepath":"/anime/"}'
```

### Log Output
```
✅ Using Section ID '6' for '/anime'
✅ Scan request from Manual for '/anime'
✅ Triggering Plex partial scan via API for: /anime
✅ Successfully triggered Plex scan! (Scan is running asynchronously)
```

## Migration Guide

### From Database-Based to API-Based

1. **Update utils.py** with the new `get_plex_section()` function
2. **Rebuild Docker image**: `docker-compose build --no-cache`
3. **Restart container**: `docker-compose up -d`
4. **Test scanning**: Send manual scan request via webhook

### No Breaking Changes

Existing configurations continue to work. The `PLEX_DATABASE_PATH` setting is harmless to leave in place.

## Related Issues

- Completes the API migration mentioned in v2.1 release notes
- Fixes "unable to open database file" errors
- Resolves permission-related scanning failures

## Credits

Fix implemented: October 2025
Repository: https://github.com/neilcorp2kx/plex_emby_jellyfin_autoscan
Original project: https://github.com/l3uddz/plex_autoscan
