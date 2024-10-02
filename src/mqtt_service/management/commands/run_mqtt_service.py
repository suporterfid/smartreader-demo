# mqtt_service/management/commands/run_mqtt_service.py
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from mqtt_service.mqtt_manager import mqtt_manager

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the MQTT service'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting MQTT service...'))
        try:
            mqtt_port = int(settings.MQTT_PORT)
            mqtt_broker = settings.MQTT_BROKER
            logger.info(f"==================================================")
            logger.info(f"Trying broker at {mqtt_broker}:{mqtt_port}")
            logger.info(f"==================================================")
            mqtt_manager.client.connect(mqtt_broker, mqtt_port, 60)
            # This will keep the script running
            mqtt_manager.client.loop_forever()
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Stopping MQTT service...'))
            logger.info(self.style.SUCCESS('Stopping MQTT service...'))
            mqtt_manager.client.disconnect()