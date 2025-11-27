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

# Set the command to 'server' mode for Gunicorn execution
# This is necessary because Gunicorn imports the module directly without command-line args
if 'gunicorn' in os.environ.get('SERVER_SOFTWARE', '').lower() or \
   any('gunicorn' in arg.lower() for arg in sys.argv):
    # Inject 'server' command for Gunicorn
    if len(sys.argv) == 1:
        sys.argv.append('server')

# Import the Flask app and configuration
from scan import app, conf, start_queue_reloader, start_google_monitor, logger

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
