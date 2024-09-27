# services.py
import logging
import json
import uuid
from django.conf import settings
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils import timezone
from datetime import datetime
from .models import Command, Reader, TagEvent, DetailedStatusEvent


logger = logging.getLogger(__name__)

def get_tag_events(search_query, sort_by):
    return TagEvent.objects.filter(
        Q(epc__icontains=search_query) |
        Q(reader__serial_number__icontains=search_query) |
        Q(reader_name__icontains=search_query)
    ).order_by(sort_by)

def get_paginated_items(queryset, page_number, per_page=10):
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(page_number)

def get_readers(search_query, sort_by):
    return Reader.objects.filter(
        Q(serial_number__icontains=search_query) |
        Q(ip_address__icontains=search_query) |
        Q(location__icontains=search_query)
    ).order_by(sort_by)

def send_command_service(request, reader_id, command_type, payload=None):
    
    reader = get_object_or_404(Reader, pk=reader_id)

    if not command_type:
        logger.error(f"No command type selected for reader {reader.serial_number}")
        return False, _("No command type selected.")

    if payload is None:
        payload = {}

    command_id = str(uuid.uuid4())
    message = {
        'command': command_type,
        'command_id': command_id,
        'payload': payload
    }

    if command_type == 'status-detailed':
        topic = f'smartreader/{reader.serial_number}/manage'
    else:
        topic = f'smartreader/{reader.serial_number}/control'

    logger.info(f"Sending command '{command_id}' - '{command_type}' to reader '{reader.serial_number}' on topic '{topic}' message: {message}")
    message_json = json.dumps(message)

    from .mqtt_client import get_mqtt_client
    client = get_mqtt_client()

    if not client.is_connected():
        logger.error("MQTT client is not connected. Attempting to reconnect...")
        try:
            client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
            logger.info("Reconnected to MQTT broker")
        except Exception as e:
            logger.exception(f"Failed to reconnect to MQTT broker: {e}")
            return False, _("Failed to send command. Please try again.")

    try:
        result = client.publish(topic, message_json)
        logger.info(f"Message queued successfully.")
        return True, _("Command queued successfully.")
    except Exception as e:
        logger.exception(f"An exception occurred while publishing the message: {e}")
        return False, _("Failed to send command. Please try again.")
    
def send_command(reader, command_type, payload=None):
    if not command_type:
        logger.error(f"No command type selected for reader {reader.serial_number}")
        return

    if not payload:
        payload = {}

    command_id = str(uuid.uuid4())
    message = {
        'command': command_type,
        'command_id': command_id,
        'payload': payload
    }

    if command_type == 'status-detailed':
        topic = f'smartreader/{reader.serial_number}/manage'
    else:
        topic = f'smartreader/{reader.serial_number}/control'

    logger.info(f"Sending command '{command_type}' to reader '{reader.serial_number}' with payload: {payload}")

    message_json = json.dumps(message)
    
    from .mqtt_client import get_mqtt_client
    client = get_mqtt_client()

    if not client.is_connected():
        logger.error("MQTT client is not connected. Attempting to reconnect...")
        try:
            client.reconnect()
            logger.info("Reconnected to MQTT broker")
        except Exception as e:
            logger.exception(f"Failed to reconnect to MQTT broker: {e}")
            return

    try:
        result = client.publish(topic, message_json)
        logger.info(f"Message published successfully.")
        return True
    except Exception as e:
        logger.exception(f"An exception occurred while publishing the message: {e}")
        return False

def handle_mode_command(reader, data):
    payload = {
        'type': data['type'],
        'antennas': data['antennas'],
        'antennaZone': data['antennaZone'],
        'antennaZoneState': data['antennaZoneState'],
        'transmitPower': data['transmitPower'],
        'groupIntervalInMs': data['groupIntervalInMs'],
        'rfMode': data['rfMode'],
        'searchMode': data['searchMode'],
        'session': data['session'],
        'tagPopulation': data['tagPopulation'],
        'filter': {
            'value': data.get('filter_value', ''),
            'match': data.get('filter_match', ''),
            'operation': data.get('filter_operation', ''),
            'status': data.get('filter_status', '')
        },
        'rssiFilter': {
            'threshold': data.get('rssi_threshold', '')
        }
    }
    return send_command(reader, 'mode', payload)

def store_command(reader, command_type):
    try:
        command = Command.objects.create(
            reader=reader,
            command=command_type,
            status='PENDING'
        )
        logger.info(f"Command stored: {command}")
        return command
    except Exception as e:
        logger.error(f"Error storing command: {str(e)}")
        raise

def update_command_status(reader_serial, command_type, status, response):
    try:
        command = Command.objects.filter(
            reader__serial_number=reader_serial,
            command=command_type,
            status='PROCESSING'
        ).latest('created_at')
        
        command.status = status
        command.response = response
        command.save()
        logger.info(f"Command status updated: {command}")
    except Command.DoesNotExist:
        logger.warning(f"No matching command found for update: {reader_serial} - {command_type}")
    except Exception as e:
        logger.error(f"Error updating command status: {str(e)}")

def get_detailed_status_events(search_query, sort_by):
    return DetailedStatusEvent.objects.filter(
        Q(reader__serial_number__icontains=search_query) |
        Q(event_type__icontains=search_query) |
        Q(component__icontains=search_query) |
        Q(status__icontains=search_query)
    ).order_by(sort_by)

def update_reader_last_communication(serial_number):
    try:
        reader = Reader.objects.get(serial_number=serial_number)
        reader.last_communication = timezone.now()
        reader.save(update_fields=['last_communication'])
        logger.info(f"Updated last_communication for reader {serial_number}")
        return reader
    except Reader.DoesNotExist:
        logger.warning(f"Reader with serial number {serial_number} does not exist")
        return None

def process_tag_events(reader, tag_reads):
    for tag_read in tag_reads:
        epc = tag_read.get('epc', '')
        first_seen_timestamp = tag_read.get('firstSeenTimestamp', 0)

        # Convert microseconds to seconds and make the datetime object timezone-aware
        naive_dt = datetime.fromtimestamp(first_seen_timestamp / 1000000)
        aware_dt = timezone.make_aware(naive_dt, timezone.get_default_timezone())

        TagEvent.objects.create(
            reader=reader,
            reader_name=tag_read.get('readerName', ''),
            mac_address=tag_read.get('mac', ''),
            epc=epc,
            first_seen_timestamp=aware_dt,
            antenna_port=tag_read.get('antennaPort', 0),
            antenna_zone=tag_read.get('antennaZone', ''),
            peak_rssi=tag_read.get('peakRssi', 0),
            tx_power=tag_read.get('txPower', 0),
            tag_data_key=tag_read.get('tagDataKey', ''),
            tag_data_key_name=tag_read.get('tagDataKeyName', ''),
            tag_data_serial=tag_read.get('tagDataSerial', '')
        )
        logger.info(f"Stored tag event for EPC {tag_read.get('epc', '')}")

def store_detailed_status_event(reader, payload):
    from datetime import datetime
    timestamp_str = payload.get('timestamp', '')
    try:
        if isinstance(timestamp_str, int):
            timestamp = datetime.fromtimestamp(timestamp_str / 1000000)
        else:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        timestamp = timezone.make_aware(timestamp, timezone.utc)
    except (ValueError, TypeError):
        timestamp = timezone.now()

    event_type = payload.get('eventType', 'unknown')
    non_antenna_details = {}

    if event_type == "gpi-status":
        non_antenna_details = {"gpiConfigurations": payload.get('gpiConfigurations', [])}
        logger.info(f"Processing GPI status event for reader {reader.serial_number}")
    elif "smartreader-mqtt-status" in payload:
        mqtt_status = payload.get("smartreader-mqtt-status", "")
        non_antenna_details = {"mqtt_status": mqtt_status}
        event_type = "mqtt-status"
        logger.info(f"Processing MQTT status event ({mqtt_status}) for reader {reader.serial_number}")
    elif "status" in payload:
        status = payload.get("status", "")
        non_antenna_details = {"status": status}
        event_type = "status"
        logger.info(f"Processing status event ({status}) for reader {reader.serial_number}")
    else:
        non_antenna_details = {k: v for k, v in payload.items() if 'antenna' not in k.lower()}
        logger.info(f"Processing generic event for reader {reader.serial_number}")

    DetailedStatusEvent.objects.create(
        reader=reader,
        event_type=event_type,
        component=payload.get('component', 'unknown'),
        timestamp=timestamp,
        mac_address=payload.get('macAddress', ''),
        status=payload.get('status', ''),
        details=payload,
        non_antenna_details=non_antenna_details
    )
    logger.info(f"Stored detailed status event (type: {event_type}) for reader {reader.serial_number}")
