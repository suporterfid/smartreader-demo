# mqtt_client.py

import time
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
    _publish_lock = Lock()

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
            self.logger.info(f"Client ID: {client._client_id}")
            self.logger.info(f"Protocol version: {client._protocol}")
            self.subscribe_to_topics()
        else:
            self.logger.error(f"Connection failed with result code {rc}")
            self.logger.error(f"Result code meaning: {mqtt.connack_string(rc)}")

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection from MQTT broker {settings.MQTT_BROKER}:{settings.MQTT_PORT}. Attempting to reconnect...")
            try:
                # Add delay before reconnect attempt
                time.sleep(5)  
                self.connect()
            except Exception as e:
                self.logger.error(f"Reconnection failed: {str(e)}")

    def publish(self, topic, message):
        with self._publish_lock:  # Ensure thread-safe publishing
            try:
                # Convert message to string if it's not already in an acceptable format
                if not isinstance(message, (str, bytearray, int, float, type(None))):
                    try:
                        message = str(message)  # Convert to string
                    except Exception as e:
                        self.logger.error(f"Failed to convert message to string: {e}")
                        return False

                if self.client.is_connected():
                    result = self.client.publish(topic, message)
                    # Wait for message to be sent
                    result.wait_for_publish()
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        self.logger.info(f"Message published successfully to {topic}")
                        return True
                    else:
                        self.logger.error(f"Failed to publish message to {topic}")
                        return False
                else:
                    self.logger.error("Cannot publish message: MQTT client is not connected.")
                    mqtt_port = int(settings.MQTT_PORT)
                    mqtt_broker = settings.MQTT_BROKER
                    logger.info(f"Connecting to broker to {mqtt_broker}:{mqtt_port}")
                    result = self.client.connect(mqtt_broker, mqtt_port, 60)                   
                    if result == mqtt.MQTT_ERR_SUCCESS:
                        logger.info("Reconnected to MQTT broker")
                        result = self.client.publish(topic, message)
                        self.logger.info(f"Message published successfully to {topic}")
                        return True
                    else:
                        self.logger.error(f"Failed to publish message to {topic}")
                        return False
            except Exception as e:
                self.logger.exception(f"Error publishing message to {topic}: {e}")
                return False
    
    def get_diagnostics(self):
        return {
            "connected": self.client.is_connected(),
            "client_id": self.client._client_id,
            "broker": getattr(settings, 'MQTT_BROKER', 'unknown'),
            "port": getattr(settings, 'MQTT_PORT', 'unknown'),
            "keepalive": self.client._keepalive,
            "loop_status": self.client._thread is not None and self.client._thread.is_alive()
        }

# mqtt_manager = MQTTManager()

# def get_mqtt_client():
#     return mqtt_manager.client

# Global instance
_mqtt_manager = None
_manager_lock = Lock()

def get_mqtt_manager():
    """
    Thread-safe way to get the MQTT manager instance
    """
    global _mqtt_manager
    with _manager_lock:
        if _mqtt_manager is None:
            _mqtt_manager = MQTTManager()
        return _mqtt_manager

# Function to publish messages from external classes/threads
def publish_message(topic: str, message: dict) -> bool:
    """
    Thread-safe function to publish messages to MQTT broker
    
    Args:
        topic (str): The MQTT topic to publish to
        message (dict): The message to publish (will be converted to JSON)

            
    Returns:
        bool: True if published successfully, False otherwise
    """
    return get_mqtt_manager().publish(topic, message)