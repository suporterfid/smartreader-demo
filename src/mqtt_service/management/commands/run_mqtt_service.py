# mqtt_service/management/commands/run_mqtt_service.py
import os
import logging
from rest_framework.permissions import IsAuthenticated
from app.authentication import APIKeyAuthentication
from django.conf import settings
from django.core.management.base import BaseCommand
import requests
from mqtt_service.mqtt_manager import mqtt_manager

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the MQTT service'
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def handle(self, *args, **options):
        headers = {'X-API-Key': os.environ.get('API_KEY')}
        self.stdout.write(self.style.SUCCESS('Starting MQTT service...'))
        try:
            mqtt_port = int(settings.MQTT_PORT)
            mqtt_broker = settings.MQTT_BROKER
            mqtt_keepalive = int(settings.MQTT_KEEPALIVE)
            logger.info(f"==================================================")
            logger.info(f"Trying broker at {mqtt_broker}:{mqtt_port}")
            logger.info(f"==================================================")
            mqtt_manager.client.connect(mqtt_broker, mqtt_port, mqtt_keepalive)
            # The initial connection is now handled by the MQTTManager
            # Just start the loop
            mqtt_manager.client.loop_forever(retry_first_connection=True)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Stopping MQTT service...'))
            logger.info('Stopping MQTT service...')
            mqtt_manager.client.disconnect()
        except Exception as e:
            logger.error(f"MQTT service error: {str(e)}")
            # Add proper cleanup
            try:
                mqtt_manager.client.disconnect()
            except:
                pass
            raise
import time
from django.conf import settings
from app.services import send_command_service

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the MQTT publisher service using Dapr'

    def handle(self, *args, **options):
        from django.core.wsgi import get_wsgi_application
        application = get_wsgi_application()

        logger.info("Starting MQTT publisher service...")
        
        DAPR_HTTP_PORT = 3501
        DJANGO_API_URL = "http://web:8000"
        
        while True:
            try:
                # Get pending commands
                headers = {'X-API-Key': os.environ.get('API_KEY')}
                response = requests.get(f"{DJANGO_API_URL}/api/commands/pending/", headers=headers)
                if response.status_code == 200:
                    commands = response.json().get('commands', [])
                    
                    for command in commands:
                        try:
                            # Process command using existing logic
                            success, message = send_command_service(
                                None,
                                command['reader_id'],
                                command['command_id'],
                                command['command'],
                                command['details']
                            )
                            
                            # Publish via Dapr
                            if success:
                                # Publish message using Dapr
                                publish_data = {
                                    "data": message,
                                    "pubsubname": "mqtt-pubsub",
                                    "topic": f"smartreader/{command['reader_serial']}/control"
                                }
                                
                                pub_response = requests.post(
                                    f"http://localhost:{DAPR_HTTP_PORT}/v1.0/publish",
                                    json=publish_data
                                )
                                
                                if pub_response.status_code == 200:
                                    # Update command status
                                    status_data = {
                                        "status": "COMPLETED",
                                        "response": "Command sent successfully"
                                    }
                                else:
                                    status_data = {
                                        "status": "FAILED",
                                        "response": f"Failed to publish: {pub_response.status_code}"
                                    }
                                    
                                requests.put(
                                    f"{DJANGO_API_URL}/api/commands/{command['command_id']}/status/",
                                    headers=headers,
                                    json=status_data
                                )
                                
                        except Exception as e:
                            logger.error(f"Error processing command {command['command_id']}: {e}")
                            
                            # Update command status as failed
                            status_data = {
                                "status": "FAILED",
                                "response": f"Error: {str(e)}"
                            }
                            requests.put(
                                f"{DJANGO_API_URL}/api/commands/{command['command_id']}/status/",
                                json=status_data
                            )
                            
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                
            time.sleep(5)  # Wait before next poll
import logging
import json
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
            response = requests.post(
                f"http://localhost:{DAPR_HTTP_PORT}/dapr/subscribe",
                json=[subscription]
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
import logging
import time
from django.core.management.base import BaseCommand
from django.core.wsgi import get_wsgi_application
from app.tasks import execute_scheduled_commands_task

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the scheduled commands service'

    def handle(self, *args, **options):
        application = get_wsgi_application()
        
        logger.info("Starting scheduled commands service...")
        
        while True:
            try:
                execute_scheduled_commands_task()
                logger.debug("Executed scheduled commands")
            except Exception as e:
                logger.error(f"Error executing scheduled commands: {e}")
            
            time.sleep(60)  # Run every minute
import logging
import time
from django.core.management.base import BaseCommand
from django.core.wsgi import get_wsgi_application
from app.tasks import process_and_cleanup_commands

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the command cleanup service'

    def handle(self, *args, **options):
        application = get_wsgi_application()
        
        logger.info("Starting command cleanup service...")
        
        while True:
            try:
                process_and_cleanup_commands()
                logger.debug("Processed and cleaned up commands")
            except Exception as e:
                logger.error(f"Error cleaning up commands: {e}")
            
            time.sleep(10)  # Run every 10 seconds
