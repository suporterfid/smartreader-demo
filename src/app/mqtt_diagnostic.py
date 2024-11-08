import os
import django
from django.conf import settings
import paho.mqtt.client as mqtt
import json
import logging
from threading import Lock
import time

from app.mqtt_client import MQTTManager

logger = logging.getLogger(__name__)

class MQTTManagerDiagnostic(MQTTManager):
    def __init__(self):
        super().__init__()
        self.last_connect_time = None
        self.connection_state = False
        self.publish_attempts = 0
        self.successful_publishes = 0
        
    def _on_connect(self, client, userdata, flags, rc):
        self.last_connect_time = time.time()
        self.connection_state = (rc == 0)
        super()._on_connect(client, userdata, flags, rc)
        
    def _on_disconnect(self, client, userdata, rc):
        self.connection_state = False
        super()._on_disconnect(client, userdata, rc)

    def publish(self, topic, message):
        self.publish_attempts += 1
        
        # Check connection status
        if not self.client.is_connected():
            logger.error("Client reports as disconnected")
            return False
            
        # Verify broker settings
        try:
            mqtt_port = int(settings.MQTT_PORT)
            mqtt_broker = settings.MQTT_BROKER
            logger.info(f"Current broker settings - Host: {mqtt_broker}, Port: {mqtt_port}")
        except Exception as e:
            logger.error(f"Invalid broker settings: {str(e)}")
            return False

        # Check message format
        try:
            json_message = json.dumps(message)
            if len(json_message) > settings.MQTT_MAX_MESSAGE_SIZE:
                logger.error(f"Message size ({len(json_message)} bytes) exceeds maximum allowed")
                return False
        except Exception as e:
            logger.error(f"Message serialization failed: {str(e)}")
            return False

        # Check topic format
        if not isinstance(topic, str) or len(topic) == 0:
            logger.error(f"Invalid topic format: {topic}")
            return False

        # Attempt publish with QoS and retain settings
        try:
            result = self.client.publish(
                topic,
                message,
                qos=getattr(settings, 'MQTT_QOS', 0),
                retain=getattr(settings, 'MQTT_RETAIN', False)
            )
            
            # Wait for message to be sent
            result.wait_for_publish()
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.successful_publishes += 1
                logger.info(f"Message published successfully to {topic}")
                return True
            else:
                logger.error(f"Publish failed with result code: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Publication error: {str(e)}")
            return False

    def get_diagnostics(self):
        return {
            "connected": self.client.is_connected(),
            "last_connect_time": self.last_connect_time,
            "connection_state": self.connection_state,
            "publish_attempts": self.publish_attempts,
            "successful_publishes": self.successful_publishes,
            "client_id": self.client._client_id,
            "broker": getattr(settings, 'MQTT_BROKER', 'unknown'),
            "port": getattr(settings, 'MQTT_PORT', 'unknown'),
            "keepalive": self.client._keepalive,
            "loop_status": self.client._thread is not None and self.client._thread.is_alive()
        }

def diagnose_mqtt_issues():
    """
    Run diagnostics on MQTT connection and publishing
    """
    manager = MQTTManagerDiagnostic()
    
    # Test message
    test_topic = "test/diagnostic"
    test_message = {"test": "diagnostic"}
    
    # Attempt publish
    result = manager.publish(test_topic, test_message)
    
    # Get diagnostic info
    diagnostics = manager.get_diagnostics()
    
    return {
        "test_publish_result": result,
        "diagnostics": diagnostics
    }