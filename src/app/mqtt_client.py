# mqtt_client.py

import os
import django
from django.conf import settings
import paho.mqtt.client as mqtt
import json
import logging
from .services import update_reader_last_communication, process_tag_events, store_detailed_status_event


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
        logger.info("Connected to MQTT broker")
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

def on_disconnect(self, client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected disconnection from MQTT broker. Attempting to reconnect...")
        self.connect()

def publish(topic, message):
    try:
        result = client.publish(topic, json.dumps(message))
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error(f"Failed to publish message to {topic}. Error code: {result.rc}")
        return result
    except Exception as e:
        logger.exception(f"Error publishing message to {topic}: {e}")
        return None

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

# client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
# client.loop_start()

def start_client():
    client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
    client.loop_start()
