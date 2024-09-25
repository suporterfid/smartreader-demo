# mqtt_client.py

import os
import django
from django.conf import settings
import paho.mqtt.client as mqtt
import json
from django.utils import timezone
import logging

# Set up Django environment
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# django.setup()

if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from app.models import DetailedStatusEvent, Reader, TagEvent

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
    try:
        reader = Reader.objects.get(serial_number=serial_number)
        reader.last_communication = timezone.now()
        reader.save(update_fields=['last_communication'])
        logger.info(f"Updated last_communication for reader {serial_number}")
    except Reader.DoesNotExist:
        logger.warning(f"Reader with serial number {serial_number} does not exist")
        return
    if '/tagEvents' in topic:
        tag_reads = payload.get('tag_reads', [])
        for tag_read in tag_reads:
            TagEvent.objects.create(
                reader=reader,
                reader_name=payload.get('readerName', ''),
                mac_address=payload.get('mac', ''),
                epc=tag_read.get('epc', ''),
                first_seen_timestamp=timezone.datetime.fromtimestamp(
                    tag_read.get('firstSeenTimestamp', 0)/1000000
                ),
                antenna_port=tag_read.get('antennaPort', 0),
                antenna_zone=tag_read.get('antennaZone', ''),
                peak_rssi=tag_read.get('peakRssi', 0),
                tx_power=tag_read.get('txPower', 0),
                tag_data_key=tag_read.get('tagDataKey', ''),
                tag_data_key_name=tag_read.get('tagDataKeyName', ''),
                tag_data_serial=tag_read.get('tagDataSerial', '')
            )
            logger.info(f"Stored tag event for EPC {tag_read.get('epc', '')}")
    elif '/event' in topic:
        # Process detailed status events
        from datetime import datetime
        timestamp_str = payload.get('timestamp', '')
        non_antenna_details = {k: v for k, v in payload.items() if 'antenna' not in k.lower()}
        try:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            timestamp = timezone.make_aware(timestamp, timezone.utc)            
        except ValueError:
            timestamp = timezone.now()
        DetailedStatusEvent.objects.create(
            reader=reader,
            event_type=payload.get('eventType', ''),
            component=payload.get('component', ''),
            timestamp=timestamp,
            mac_address=payload.get('macAddress', ''),
            status=payload.get('status', ''),
            details=payload,
            non_antenna_details=non_antenna_details  # Save non-antenna details
        )
        logger.info(f"Stored detailed status event for reader {serial_number}")

client = None  # Global client variable

def start_client():
    global client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    # Use broker settings from settings.py
    client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
    client.loop_start()

# client.on_connect = on_connect
# client.on_message = on_message

# client.connect(MQTT_BROKER, MQTT_PORT, 60)
# client.loop_forever()
