#!/bin/bash
set -e

if [ "$1" = "web" ]; then
    exec gunicorn --bind 0.0.0.0:8000 config.wsgi:application
elif [ "$1" = "celery" ]; then
    exec celery -A config worker -l debug
elif [ "$1" = "celery-beat" ]; then
    exec celery -A config beat -l debug
elif [ "$1" = "mqtt_service" ]; then
    exec python manage.py run_mqtt_service
else
    exec "$@"
fi