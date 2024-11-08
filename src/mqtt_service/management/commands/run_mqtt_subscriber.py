import logging
import json
import os
import requests
from django.core.management.base import BaseCommand
from django.core.wsgi import get_wsgi_application
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the MQTT subscriber service using Dapr'

    def handle(self, *args, **options):
        application = get_wsgi_application()

        logger.info("Starting MQTT subscriber service...")

        # Subscribe to MQTT topics via Dapr
        DAPR_HTTP_PORT = 3503

        # Subscribe to topics
        subscription = {
            "pubsubname": "mqtt-pubsub",
            "topic": "smartreader/+/controlResult",
            "route": "/api/mqtt/process/"
        }

        try:
            headers = {'X-API-Key': os.environ.get('API_KEY')}
            response = requests.post(
                f"http://localhost:{DAPR_HTTP_PORT}/dapr/subscribe",
                json=[subscription],
                headers=headers
            )
            if response.status_code == 200:
                logger.info("Successfully subscribed to MQTT topics")
            else:
                logger.error(f"Failed to subscribe: {response.status_code}")
                return

        except Exception as e:
            logger.error(f"Error subscribing to topics: {e}")
            return

        # Keep the service running
        while True:
            time.sleep(1)