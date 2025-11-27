#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WSGI Entry Point for Gunicorn

This module provides a proper WSGI entry point for Gunicorn, ensuring that
background workers (queue processor, Google Drive monitor) are started when
the application is run in server mode.
"""

import os
import sys

# Ensure the application directory is in the Python path
sys.path.insert(0, os.path.dirname(__file__))

# CRITICAL: Set sys.argv BEFORE any imports that use argparse
# The config.py module uses argparse which runs during import
# Gunicorn passes arguments like 'wsgi:application' which confuses argparse
# We need to replace sys.argv with a clean set that includes 'server'
#
# Also fix sys.argv[0] to point to the application directory, not gunicorn's path
# This ensures config.py derives correct paths for logfile, queuefile, etc.
original_argv = sys.argv.copy()
app_dir = os.path.dirname(os.path.abspath(__file__))
sys.argv = [os.path.join(app_dir, 'scan.py'), 'server']

# Import the Flask app and configuration
from scan import app, conf, start_queue_reloader, start_google_monitor, logger

# Restore original argv after import (in case anything needs it)
sys.argv = original_argv

# Initialize background services when running in production
# This is executed once when Gunicorn starts the master process
if conf.args.get('cmd') == 'server' or 'server' in sys.argv:
    logger.info("Initializing background services for Gunicorn...")

    if conf.configs['SERVER_USE_SQLITE']:
        logger.info("Starting queue reloader...")
        start_queue_reloader()

    if conf.configs['GOOGLE']['ENABLED']:
        logger.info("Starting Google Drive monitor...")
        start_google_monitor()

    logger.info("Background services initialized.")

# Export the Flask application for Gunicorn
# Gunicorn will look for the 'application' or 'app' variable
application = app

if __name__ == "__main__":
    # This allows testing the WSGI module directly
    logger.info("Starting WSGI application in development mode...")
    app.run(host=conf.configs['SERVER_IP'], port=conf.configs['SERVER_PORT'], debug=False, use_reloader=False)
