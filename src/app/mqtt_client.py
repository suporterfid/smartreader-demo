# mqtt_client.py

import os
import django
from django.conf import settings
import paho.mqtt.client as mqtt
import json
import logging
from threading import Lock

logger = logging.getLogger(__name__)

class MQTTManager:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MQTTManager, cls).__new__(cls)
                cls._instance.initialize()
        return cls._instance

    def initialize(self):
        # Set up Django environment
        if not os.environ.get('DJANGO_SETTINGS_MODULE'):
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
            django.setup()

        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.connect()

    def connect(self):
        try:
            mqtt_port = int(settings.MQTT_PORT)
            mqtt_broker = settings.MQTT_BROKER
            self.logger.info(f"Connecting to broker at {mqtt_broker}:{mqtt_port}")
            self.client.connect(mqtt_broker, mqtt_port, 60)
            self.client.loop_start()
            self.logger.info(f"Connected to MQTT broker at {mqtt_broker}:{mqtt_port}")
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {str(e)}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info(f"Connected to MQTT broker at {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
        else:
            self.logger.error(f"Connection failed with result code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection. Attempting to reconnect...")
            self.connect()

    def publish(self, topic, message):
        try:
            if self.client.is_connected():
                result = self.client.publish(topic, json.dumps(message))
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    self.logger.info(f"Message published successfully to {topic}")
                    return True
                else:
                    self.logger.error(f"Failed to publish message to {topic}")
                    return False
            else:
                self.logger.error("Cannot publish message: MQTT client is not connected.")
                self.connect()  # Attempt to reconnect
                return False
        except Exception as e:
            self.logger.exception(f"Error publishing message to {topic}: {e}")
            return False

mqtt_manager = MQTTManager()

def get_mqtt_client():
    return mqtt_manager.client