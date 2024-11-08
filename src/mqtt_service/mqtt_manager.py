# mqtt_service/mqtt_manager.py

import time
import os
import django
from django.conf import settings
import paho.mqtt.client as mqtt
import json
import logging
from threading import Lock
from datetime import datetime
import ssl
from pathlib import Path

from app.services import (
    update_reader_connection_status, update_reader_last_communication, process_tag_events, 
    store_detailed_status_event, update_command_status
)


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
        if not os.environ.get('DJANGO_SETTINGS_MODULE'):
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
            django.setup()

        self._setup_logging()
        self._setup_connection_state()
        self._setup_mqtt_client()
    
    def _setup_logging(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _setup_connection_state(self):
        self.connection_state = "DISCONNECTED"
        self.last_connect_time = None
        self.reconnect_count = 0
        self.max_reconnect_attempts = getattr(settings, 'MQTT_MAX_RECONNECT_ATTEMPTS', 5)
        self.reconnect_delay = getattr(settings, 'MQTT_RECONNECT_DELAY', 5)
        self.publish_attempts = 0
        self.successful_publishes = 0
        
    def _setup_mqtt_client(self):
        client_id = f"django_mqtt_{int(time.time())}"
        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        
        # Configure TLS if enabled
        use_tls = getattr(settings, 'MQTT_USE_TLS', False)
        if use_tls:
            self._configure_tls()
        
        # Set up credentials if configured
        if hasattr(settings, 'MQTT_USERNAME') and hasattr(settings, 'MQTT_PASSWORD'):
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        
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

    def _configure_tls(self):
        """Configure TLS settings for the MQTT client"""
        try:
            # Get TLS configuration from settings
            ca_certs = getattr(settings, 'MQTT_CA_CERTS', None)
            certfile = getattr(settings, 'MQTT_CERTFILE', None)
            keyfile = getattr(settings, 'MQTT_KEYFILE', None)
            tls_version = getattr(settings, 'MQTT_TLS_VERSION', ssl.PROTOCOL_TLS_CLIENT)
            ciphers = getattr(settings, 'MQTT_CIPHERS', None)
            
            # Verify paths exist if specified
            if ca_certs and not Path(ca_certs).exists():
                raise FileNotFoundError(f"CA certificate file not found: {ca_certs}")
            if certfile and not Path(certfile).exists():
                raise FileNotFoundError(f"Client certificate file not found: {certfile}")
            if keyfile and not Path(keyfile).exists():
                raise FileNotFoundError(f"Client key file not found: {keyfile}")

            # Configure TLS
            self.client.tls_set(
                ca_certs=ca_certs,
                certfile=certfile,
                keyfile=keyfile,
                cert_reqs=ssl.CERT_REQUIRED if ca_certs else ssl.CERT_NONE,
                tls_version=tls_version,
                ciphers=ciphers
            )
            
            # Disable hostname checking if specified
            verify_hostname = getattr(settings, 'MQTT_VERIFY_HOSTNAME', True)
            if not verify_hostname:
                self.client.tls_insecure_set(True)
                
            self.logger.info("TLS configuration completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error configuring TLS: {str(e)}")
            raise

    def _setup_mqtt_client(self):
        self.client = mqtt.Client(client_id=f"django_mqtt_{int(time.time())}")
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        
        # Set up credentials if configured
        if hasattr(settings, 'MQTT_USERNAME') and hasattr(settings, 'MQTT_PASSWORD'):
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        
        # Configure TLS if enabled
        use_tls = getattr(settings, 'MQTT_USE_TLS', False)
        self.logger.warning(f">>>>>>>>Use TLS {use_tls}")
        if use_tls is True:
            self._configure_tls()
        else:
            self.logger.info("TLS is disabled, skipping TLS configuration")

        self.topics = [
            'smartreader/+/manageResult',
            'smartreader/+/tagEvents',
            'smartreader/+/event',
            'smartreader/+/metrics',
            'smartreader/+/lwt'
        ]

    def connect(self):
        try:
            if self.connection_state == "CONNECTING":
                self.logger.warning("Connection attempt already in progress")
                return False

            self.connection_state = "CONNECTING"
            mqtt_port = int(settings.MQTT_PORT)
            mqtt_broker = settings.MQTT_BROKER

            self.logger.info(f"Attempting connection to broker at {mqtt_broker}:{mqtt_port}")
            self.logger.info(f"TLS Enabled: {getattr(settings, 'MQTT_USE_TLS', False)}")
            
            # Set keep alive interval
            keepalive = getattr(settings, 'MQTT_KEEPALIVE', 60)
            self.client.connect(mqtt_broker, mqtt_port, keepalive)
            
            self.logger.info(f"Attempting connection to broker at {mqtt_broker}:{mqtt_port}")
            
            self.client.connect(mqtt_broker, mqtt_port, keepalive)
            
            # Start network loop in background thread
            self.client.loop_start()
            
            return True

        except ValueError as ve:
            self.logger.error(f"Invalid port number in MQTT settings: {str(ve)}")
            self.connection_state = "DISCONNECTED"
            return False
        except ssl.SSLError as ssle:
            self.logger.error(f"SSL/TLS error: {str(ssle)}")
            self.connection_state = "DISCONNECTED"
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {str(e)}")
            self.connection_state = "DISCONNECTED"
            return False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connection_state = "CONNECTED"
            self.last_connect_time = datetime.now()
            self.reconnect_count = 0
            
            self.logger.info(f"Successfully connected to MQTT broker")
            self.logger.info(f"Client ID: {client._client_id}")
            self.logger.info(f"Protocol version: {client._protocol}")
            
            self.subscribe_to_topics()
        else:
            self.connection_state = "DISCONNECTED"
            self.logger.error(f"Connection failed with result code {rc}: {mqtt.connack_string(rc)}")

    def on_disconnect(self, client, userdata, rc):
        self.connection_state = "DISCONNECTED"
        
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection from MQTT broker. RC: {rc}")
            self._handle_reconnection()

    def _handle_reconnection(self):
        if self.reconnect_count >= self.max_reconnect_attempts:
            self.logger.error("Max reconnection attempts reached. Manual intervention required.")
            return

        self.reconnect_count += 1
        self.logger.info(f"Attempting reconnection {self.reconnect_count}/{self.max_reconnect_attempts}")
        
        time.sleep(self.reconnect_delay)
        self.connect()

    def subscribe_to_topics(self):
        for topic in self.topics:
            try:
                result, mid = self.client.subscribe(topic)
                if result == mqtt.MQTT_ERR_SUCCESS:
                    self.logger.info(f"Successfully subscribed to topic: {topic}")
                else:
                    self.logger.error(f"Failed to subscribe to topic {topic}. Result code: {result}")
            except Exception as e:
                self.logger.error(f"Error subscribing to topic {topic}: {str(e)}")
    
    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in MQTT message: {msg.payload}")
            return

        self.logger.info(f"Received message {payload} on topic {topic}")
        
        try:
            serial_number = topic.split('/')[1]
            reader = update_reader_last_communication(serial_number)
            if reader is None:
                self.logger.warning(f"No reader found for serial number: {serial_number}")
                return

            if '/tagEvents' in topic:
                tag_reads = payload.get('tag_reads', [])
                process_tag_events(reader, tag_reads)
                
            elif '/lwt' in topic:
                mqtt_status = payload.get('smartreader-mqtt-status')
                if mqtt_status == 'disconnected':
                    update_reader_connection_status(reader, False)
                store_detailed_status_event(reader, payload)
                
            elif '/event' in topic:
                mqtt_status = payload.get('smartreader-mqtt-status')
                if mqtt_status == 'connected':
                    update_reader_connection_status(reader, True)
                store_detailed_status_event(reader, payload)
                
            elif '/manageResult' in topic or '/controlResult' in topic:
                self._handle_command_response(reader, payload, serial_number)
                
        except Exception as e:
            self.logger.error(f"Error processing MQTT message: {str(e)}", exc_info=True)

    def _handle_command_response(self, reader, payload, serial_number):
        """Handle command response messages"""
        try:
            # Update reader connection status
            update_reader_connection_status(reader, True)
            
            # Extract command details with default values
            command_type = payload.get('command', 'unknown')
            command_status = payload.get('response', '')
            command_id = payload.get('command_id', 'unknown')
            command_message = payload.get('message', '')
            
            # Determine status
            status = 'COMPLETED' if command_status == 'success' else 'FAILED'
            
            # Construct response string safely
            response_parts = []
            if command_status:
                response_parts.append(command_status)
            if command_message:
                response_parts.append(command_message)
            
            response = " ".join(filter(None, response_parts))  # Join non-empty parts
            
            # Log the command response
            self.logger.info(
                f'Command Response - ID: {command_id}, '
                f'Serial: {serial_number}, '
                f'Type: {command_type}, '
                f'Status: {status}, '
                f'Response: {response}'
            )
            
            # Update command status in database
            update_command_status(
                command_id=command_id,
                reader_serial=serial_number,
                command_type=command_type,
                status=status,
                response=response if response else 'No response message'
            )
            
        except Exception as e:
            self.logger.error(
                f"Error processing command response - "
                f"Serial: {serial_number}, "
                f"Payload: {payload}, "
                f"Error: {str(e)}", 
                exc_info=True
            )
            raise

    def publish(self, topic, message):
        with self._publish_lock:
            self.publish_attempts += 1
            
            if not self._verify_connection():
                return False

            try:
                json_message = json.dumps(message)
                if len(json_message) > getattr(settings, 'MQTT_MAX_MESSAGE_SIZE', 10000):
                    self.logger.error(f"Message size exceeds maximum allowed")
                    return False
                
                result = self.client.publish(
                    topic,
                    json_message,
                    qos=getattr(settings, 'MQTT_QOS', 1),
                    retain=getattr(settings, 'MQTT_RETAIN', False)
                )
                
                result.wait_for_publish(timeout=10.0)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    self.successful_publishes += 1
                    self.logger.info(f"Successfully published message to {topic}")
                    return True
                else:
                    self.logger.error(f"Failed to publish message. Result code: {result.rc}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error publishing message: {str(e)}")
                return False

    def _verify_connection(self):
        if not self.client.is_connected():
            self.logger.warning("Client disconnected. Attempting reconnection...")
            return self.connect()
        return True

    def get_diagnostics(self):
        return {
            "connected": self.client.is_connected(),
            "connection_state": self.connection_state,
            "last_connect_time": self.last_connect_time,
            "reconnect_count": self.reconnect_count,
            "publish_attempts": self.publish_attempts,
            "successful_publishes": self.successful_publishes,
            "client_id": self.client._client_id.decode() if self.client._client_id else None,
            "broker": getattr(settings, 'MQTT_BROKER', 'unknown'),
            "port": getattr(settings, 'MQTT_PORT', 'unknown'),
            "keepalive": self.client._keepalive,
            "protocol_version": self.client._protocol,
            "loop_status": self.client._thread is not None and self.client._thread.is_alive()
        }

mqtt_manager = MQTTManager()

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