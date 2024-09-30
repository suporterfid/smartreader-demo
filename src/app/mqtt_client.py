# mqtt_client.py

import os
import django
from django.conf import settings
import paho.mqtt.client as mqtt
import json
import logging
from .services import (
    update_reader_connection_status, update_reader_last_communication, process_tag_events, 
    store_detailed_status_event, update_command_status
)
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
        logger.addHandler(handler)

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.topics = [
            'smartreader/+/manageResult',
            'smartreader/+/tagEvents',
            'smartreader/+/event',
            'smartreader/+/metrics',
            'smartreader/+/lwt'
        ]

    def connect(self):
        try:
            self.client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
            self.client.loop_start()
            logger.info(f"Connected to MQTT broker at {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {str(e)}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
            self.subscribe_to_topics()
        else:
            logger.error(f"Connection failed with result code {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker {settings.MQTT_BROKER}:{settings.MQTT_PORT}. Attempting to reconnect...")
            try:
                self.client.reconnect()
            except Exception as e:
                logger.error(f"Failed to reconnect: {e}")

    def on_message(client, userdata, msg):
        topic = msg.topic
        payload = json.loads(msg.payload.decode())
        logger.info(f"Received message on topic {topic}")
        serial_number = topic.split('/')[1]

        reader = update_reader_last_communication(serial_number)
        if reader is None:
            return

        if '/tagEvents' in topic:
            tag_reads = payload.get('tag_reads', [])
            process_tag_events(reader, tag_reads)
        if '/lwt' in topic:
            if payload.get('smartreader-mqtt-status') == 'disconnected':
                update_reader_connection_status(reader, False)
                store_detailed_status_event(reader, payload)
        elif '/event' in topic:
            if payload.get('smartreader-mqtt-status') == 'connected':
                update_reader_connection_status(reader, True)
            store_detailed_status_event(reader, payload)
        elif '/manageResult' in topic:
            try:
                payload_data = json.loads(msg.payload.decode())
                command_type = payload_data.get('command')
                status = 'COMPLETED' if payload_data.get('success') else 'FAILED'
                response = json.dumps(payload_data)
                update_command_status(serial_number, command_type, status, response)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in MQTT message: {msg.payload}")
            except Exception as e:
                logger.error(f"Error processing MQTT message: {str(e)}")
        elif '/controlResult' in topic:
            try:
                payload_data = json.loads(msg.payload.decode())
                command_type = payload_data.get('command')
                status = 'COMPLETED' if payload_data.get('success') else 'FAILED'
                response = json.dumps(payload_data)
                update_command_status(serial_number, command_type, status, response)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in MQTT message: {msg.payload}")
            except Exception as e:
                logger.error(f"Error processing MQTT message: {str(e)}")

    def subscribe_to_topics(self):
        for topic in self.topics:
            self.client.subscribe(topic)
            logger.info(f"Subscribed to topic: {topic}")
            
    def publish(self, topic, message):
        try:
            if self.client.is_connected():
                result = self.client.publish(topic, json.dumps(message))
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"Message published successfully to {topic}")
                return True
            else:
                logger.error("Cannot publish message: MQTT client is not connected.")
                # Attempt to reconnect
                try:
                    self.client.reconnect()
                except Exception as e:
                    logger.error(f"Failed to reconnect: {e}")
                return False
        except Exception as e:
            logger.exception(f"Error publishing message to {topic}: {e}")
            return False

    def run(self):
        self.connect()
        self.client.loop()

mqtt_manager = MQTTManager()

def get_mqtt_client():
    if not mqtt_manager.client.is_connected:
        mqtt_manager.connect()
    return mqtt_manager.client

# This function is no longer needed
# def get_task_mqtt_client():
#     ...

def start_client():
    # This is now a no-op, as the client is started when MQTTManager is instantiated
    pass