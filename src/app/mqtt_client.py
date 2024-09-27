# mqtt_client.py

import os
import django
from django.conf import settings
import paho.mqtt.client as mqtt
import json
import logging
from .services import (
    update_reader_last_communication, process_tag_events, 
    store_detailed_status_event, update_command_status
)

# Set up Django environment
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"Connected to MQTT broker at {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
    else:
        logger.error(f"Connection failed with result code {rc}")
    client.subscribe('smartreader/+/manageResult')
    client.subscribe('smartreader/+/tagEvents')
    client.subscribe('smartreader/+/event')
    client.subscribe('smartreader/+/metrics')
    client.subscribe('smartreader/+/lwt')
    logger.info("Subscribed to topics")

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
    elif '/event' in topic:
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

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning(f"Unexpected disconnection from MQTT broker {settings.MQTT_BROKER}:{settings.MQTT_PORT}. Attempting to reconnect...")
        try:
            client.reconnect()
        except Exception as e:
            logger.error(f"Failed to reconnect: {e}")

def publish(topic, message):
    try:
        if client.is_connected():
            result = client.publish(topic, json.dumps(message))
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"Failed to publish message to {topic}. Error code: {result.rc}")
            return result
        else:
            logger.error("Cannot publish message: MQTT client is not connected.")
            # Attempt to reconnect
            try:
                client.reconnect()
            except Exception as e:
                logger.error(f"Failed to reconnect: {e}")
            return None
    except Exception as e:
        logger.exception(f"Error publishing message to {topic}: {e}")
        return None

def on_publish(client, userdata, mid):
    logger.info(f"Message {mid} published successfully")

def get_task_mqtt_client():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_publish = on_publish

    try:
        client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
        client.loop_start()
        logger.info(f"Task MQTT client connected to {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
    except Exception as e:
        logger.error(f"Failed to connect task MQTT client: {str(e)}")

    return client

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

# client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
# client.loop_start()

def start_client():
    try:
        logger.info(f"Connecting to {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
        client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        logger.error(f"Failed to start MQTT client: {e}")
