# services.py
import logging
import json
import uuid
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from .models import Reader, TagEvent, DetailedStatusEvent
from .mqtt_client import client
import paho.mqtt.client as mqtt

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

    logger.info(f"Sending command '{command_type}' to reader '{reader.serial_number}' with payload: {payload}")
    message_json = json.dumps(message)

    if not client.is_connected():
        logger.error("MQTT client is not connected. Attempting to reconnect...")
        try:
            client.reconnect()
            logger.info("Reconnected to MQTT broker")
        except Exception as e:
            logger.exception(f"Failed to reconnect to MQTT broker: {e}")
            return False, _("Failed to reconnect to MQTT broker.")

    try:
        result, mid = client.publish(topic, message_json)
        if result == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Message published successfully with message ID: {mid}")
            return True, _("Command '%(command)s' sent to reader '%(serial)s' successfully.") % {
                'command': command_type, 'serial': reader.serial_number}
        else:
            logger.error(f"Failed to publish message. Error code: {result}")
            return False, _("Failed to publish message. Error code: %(result)s.") % {'result': str(result)}
    except Exception as e:
        logger.exception(f"An exception occurred while publishing the message: {e}")
        return False, _("An error occurred: %(error)s") % {'error': str(e)}
    
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
    
    if not client.is_connected():
        logger.error("MQTT client is not connected. Attempting to reconnect...")
        try:
            client.reconnect()
            logger.info("Reconnected to MQTT broker")
        except Exception as e:
            logger.exception(f"Failed to reconnect to MQTT broker: {e}")
            return

    try:
        result, mid = client.publish(topic, message_json)
        if result == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Message published successfully with message ID: {mid}")
            return True
        else:
            logger.error(f"Failed to publish message. Error code: {result}")
            return False
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

def get_detailed_status_events(search_query, sort_by):
    return DetailedStatusEvent.objects.filter(
        Q(reader__serial_number__icontains=search_query) |
        Q(event_type__icontains=search_query) |
        Q(component__icontains=search_query) |
        Q(status__icontains=search_query)
    ).order_by(sort_by)
