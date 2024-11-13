import logging
import json
import os
import django
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.wsgi import get_wsgi_application
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the MQTT subscriber service using Dapr'

    if not os.environ.get('DJANGO_SETTINGS_MODULE'):
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
            django.setup()

    def handle(self, *args, **options):
        application = get_wsgi_application()

        logger.info("Starting MQTT subscriber service...")

        # Get configuration from environment
        DAPR_HTTP_PORT = os.environ.get('DAPR_HTTP_PORT', '3503')
        APP_PORT = os.environ.get('APP_PORT', '3502')
        APP_ID = os.environ.get('APP_ID', 'mqtt-subscriber')

        # Import MQTT topics from settings
        from dapr_integration.config import MQTT_TOPICS

        # Create subscription configs for all topics
        subscriptions = []
        for topic in MQTT_TOPICS:
            subscriptions.append({
                "pubsubname": "mqtt-pubsub",  # This should match your MQTT pubsub component name
                "topic": topic,
                "route": "/api/mqtt/process/",
                "metadata": {
                    "headers": {
                        "X-API-Key": os.environ.get('API_KEY')
                    }
                }
            })

        # # Wait for Dapr sidecar to be ready
        # logger.info("Waiting for Dapr sidecar to be ready...")
        # max_retries = 30
        # retry_count = 0
        
        # while retry_count < max_retries:
        #     try:
        #         # Test sidecar health endpoint using the Docker service name
        #         health_check = requests.get(f"http://dapr-sidecar-subscriber:{DAPR_HTTP_PORT}/v1.0/healthz")
        #         if health_check.status_code == 200:
        #             logger.info("Dapr sidecar is ready")
        #             break
        #     except requests.exceptions.ConnectionError:
        #         logger.info(f"Waiting for Dapr sidecar... Attempt {retry_count + 1}/{max_retries}")
        #         time.sleep(2)
        #         retry_count += 1
        #         continue
            
        # if retry_count >= max_retries:
        #     logger.error("Failed to connect to Dapr sidecar after maximum retries")
        #     return

        try:
            response = requests.post(
                f"http://dapr-sidecar-subscriber:{DAPR_HTTP_PORT}/dapr/subscribe",
                json=subscriptions
            )
            if response.status_code == 200:
                logger.info(f"Successfully subscribed to MQTT topics: {MQTT_TOPICS}")
            else:
                logger.error(f"Failed to subscribe: {response.status_code} - {response.text}")
                return

        except Exception as e:
            logger.error(f"Error subscribing to topics: {e}")
            return

        # Keep the service running
        logger.info("MQTT subscriber service is running and waiting for messages...")
        
        try:
            # Set up a simple subscription endpoint for the app
            from http.server import HTTPServer, BaseHTTPRequestHandler
            from threading import Thread

            class PubSubHandler(BaseHTTPRequestHandler):
                def do_POST(self):
                    try:
                        content_length = int(self.headers['Content-Length'])
                        message_data = self.rfile.read(content_length)
                        logger.info(f"Received message on path {self.path}: {message_data.decode()}")
                        
                        # Process the message here
                        # You might want to add your message processing logic here
                        
                        # Send success response
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "success"}).encode())
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        self.send_response(500)
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())


            # Start HTTP server to handle subscribed messages
            server = HTTPServer(('0.0.0.0', int(APP_PORT)), PubSubHandler)
            server_thread = Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            logger.info(f"Started HTTP server on port {APP_PORT}")

            # Register subscriptions with Dapr
            response = requests.post(
                f"http://dapr-sidecar-subscriber:{DAPR_HTTP_PORT}/dapr/subscribe",
                json=subscriptions,
                headers={
                    "Content-Type": "application/json",
                    "dapr-app-id": APP_ID
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully registered subscriptions for topics: {MQTT_TOPICS}")
            else:
                logger.error(f"Failed to register subscriptions: {response.status_code} - {response.text}")
                return

        except Exception as e:
            logger.error(f"Error setting up subscriber: {e}")
            return

        # Keep the service running
        logger.info("MQTT subscriber service is running and waiting for messages...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down subscriber service...")
            server.shutdown()
            server.server_close()