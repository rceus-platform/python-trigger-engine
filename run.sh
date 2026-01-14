#!/bin/bash
exec /opt/apps/python-trigger-engine/.venv/bin/gunicorn --bind 0.0.0.0:8003 trigger_engine.wsgi:application
