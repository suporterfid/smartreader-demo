# mqtt_service/mqtt_manager.py

import os
import django
from django.conf import settings
import paho.mqtt.client as mqtt
import json
import logging
from threading import Lock

from app.services import (
    update_reader_connection_status, update_reader_last_communication, process_tag_events, 
    store_detailed_status_event, update_command_status
)

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
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.topics = [
            'smartreader/+/manageResult',
            'smartreader/+/tagEvents',
            'smartreader/+/event',
            'smartreader/+/metrics',
            'smartreader/+/lwt'
        ]
        self.connect()

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
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.topics = settings.MQTT_TOPICS

    def connect(self):
        try:
            mqtt_port = int(settings.MQTT_PORT)
            mqtt_broker = settings.MQTT_BROKER
            self.logger.info(f"==================================================")
            self.logger.info(f"Trying broker at {mqtt_broker}:{mqtt_port}")
            self.logger.info(f"==================================================")
            self.client.connect(mqtt_broker, mqtt_port, 60)
            self.client.loop_start()
            self.logger.info(f"Connected to MQTT broker at {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
        except ValueError as ve:
            self.logger.error(f"Invalid port number in MQTT settings: {str(ve)}")
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {str(e)}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info(f"Connected to MQTT broker at {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
            self.subscribe_to_topics()
        else:
            self.logger.error(f"Connection failed with result code {rc}")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection from MQTT broker {settings.MQTT_BROKER}:{settings.MQTT_PORT}. Attempting to reconnect...")
            self.connect(self)

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in MQTT message: {msg.payload}")
            return

        self.logger.info(f"Received message {payload} on topic {topic}")
        serial_number = topic.split('/')[1]

        reader = update_reader_last_communication(serial_number)
        if reader is None:
            return

        if '/tagEvents' in topic:
            tag_reads = payload.get('tag_reads', [])
            process_tag_events(reader, tag_reads)
        elif '/lwt' in topic:
            if payload.get('smartreader-mqtt-status') == 'disconnected':
                update_reader_connection_status(reader, False)
            store_detailed_status_event(reader, payload)
        elif '/event' in topic:
            if payload.get('smartreader-mqtt-status') == 'connected':
                update_reader_connection_status(reader, True)
            store_detailed_status_event(reader, payload)
        elif '/manageResult' in topic or '/controlResult' in topic:
            try:
                update_reader_connection_status(reader, True)
                command_type = payload.get('command')
                command_status= payload.get('response')
                if command_status == 'success':
                    status = 'COMPLETED'
                else:
                    status = 'FAILED'
                command_id = payload.get('command_id')
                command_response = payload.get('response')
                command_message = payload.get('message')
                response = command_response + " " + command_message
                logger.info(f'Received command response {command_id}, {serial_number}, {command_type}, {status}, {response}')
                update_command_status(command_id, serial_number, command_type, status, response)
            except Exception as e:
                self.logger.error(f"Error processing MQTT message: {str(e)}")

    def subscribe_to_topics(self):
        for topic in self.topics:
            self.client.subscribe(topic)
            self.logger.info(f"Subscribed to topic: {topic}")

    def publish(self, topic, message):
        try:
            if self.client.is_connected():
                result = self.client.publish(topic, json.dumps(message))
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    self.logger.info(f"Message published successfully to {topic}")
                return True
            else:
                self.logger.error("Cannot publish message: MQTT client is not connected.")
                self.connect()  # Attempt to reconnect
                return False
        except Exception as e:
            self.logger.exception(f"Error publishing message to {topic}: {e}")
            return False

mqtt_manager = MQTTManager()

# def get_mqtt_client():
#     return mqtt_manager.client

def get_mqtt_client():
    if not mqtt_manager.client.is_connected():
        mqtt_manager.connect()
    return mqtt_manager.client

from django.apps import AppConfig

class MQTTClientConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mqtt_client'

    def ready(self):
        # Uncomment the next line if you want to start the MQTT client
        # when Django starts. Be cautious with this in development
        # as it may cause the client to start multiple times.
        # mqtt_handler.run()
        pass