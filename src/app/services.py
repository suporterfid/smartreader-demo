# services.py
import logging
import json
import uuid
from django.conf import settings
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils import timezone
from datetime import datetime

from .models import Command, Reader, TagEvent, DetailedStatusEvent, Alert, AlertLog, ScheduledCommand, Firmware


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

def send_command_service(request, reader_id, command_id, command_type, payload=None):
    reader = get_object_or_404(Reader, pk=reader_id)
    command_payload = None
    try:
        command = Command.objects.filter(
            command_id=command_id,
            reader__serial_number=reader.serial_number
        ).latest('date_sent')
        
        # Check if command.details is a string and convert it to a dictionary if needed
        if isinstance(command.details, str):
            try:
                command_payload = json.loads(command.details)  # Parse it to a dictionary
            except json.JSONDecodeError:
                # If it's not valid JSON, replace single quotes with double quotes
                logger.warning("command.details is not valid JSON, trying to fix format")
                try:
                    command_payload = json.loads(command.details.replace("'", '"'))
                except Exception as e:
                    logger.warning("Invalid JSON stored in command details.")
                    command_payload = {}
        else:
            if not isinstance(command.details, (str, bytearray, int, float, type(None))):
                try:
                    command_payload = str(command.details)  # It's already a dictionary 
                    command_payload = json.loads(command_payload)
                    logger.info(f'command payload from database: {command.details}')
                except Exception as e:
                    logger.error(f"Failed to convert command details to string: {e}")
                    return False       
    except ObjectDoesNotExist:
        command = None
    except Exception as e:
        command = None
        logger.error(f"Error searching command: {str(e)}")

    logger.info(f'Command payload to send: {command_payload}')
    payload = command_payload
    
    print(f'send_command_service {command_type}')
    if not command_type:
        logger.error(f"No command type selected for reader {reader.serial_number}")
        return False, _("No command type selected.")

    if payload is None:
        payload = {}

    message = {
        'command': command_type,
        'command_id': command_id,
        'payload': payload  # payload should now be a proper dictionary
    }

    if command_type == 'status-detailed':
        topic = f'smartreader/{reader.serial_number}/manage'
    else:
        topic = f'smartreader/{reader.serial_number}/control'

    # Convert the message to a JSON string with proper formatting
    # message_json = json.dumps(message, indent=4)
    # message_json = json.dumps(message)

    logger.info(f"Sending command '{command_id}' - '{command_type}' to reader '{reader.serial_number}' on topic '{topic}' message: {message}")
   
    # The following block is unnecessary, as `message['payload']` is already a dictionary
    # Therefore, we don't need to sanitize it again

    from .mqtt_client import publish_message
    try:
        if publish_message(topic, message):
            logger.info(f"Message queued successfully.")
        else:
            logger.error(f"An exception occurred while publishing the message.")
    except Exception as e:
        logger.exception(f"Failed to reconnect to MQTT broker: {e}")
        return False, _("Failed to send command. Please try again.")


    # from .mqtt_client import get_mqtt_client
    # client = get_mqtt_client()

    # if not client.is_connected():
    #     logger.error("MQTT client is not connected. Attempting to reconnect...")
    #     try:
    #         mqtt_port = int(settings.MQTT_PORT)
    #         mqtt_broker = settings.MQTT_BROKER
    #         logger.info(f"Connecting to broker at {mqtt_broker}:{mqtt_port}")
    #         client.connect(mqtt_broker, mqtt_port, 60)
    #         logger.info("Reconnected to MQTT broker")
    #     except Exception as e:
    #         logger.exception(f"Failed to reconnect to MQTT broker: {e}")
    #         return False, _("Failed to send command. Please try again.")

    # try:
    #     result = client.publish(topic, message_json)
    #     logger.info(f"Message queued successfully.")
    #     return True, _("Command queued successfully.")
    # except Exception as e:
    #     logger.exception(f"An exception occurred while publishing the message: {e}")
    #     return False, _("Failed to send command. Please try again.")

# Recursive function to remove empty fields
def remove_empty_fields(d):
    if isinstance(d, dict):
        return {k: remove_empty_fields(v) for k, v in d.items() if v not in ("", None, [], {})}
    elif isinstance(d, list):
        return [remove_empty_fields(v) for v in d if v not in ("", None, [], {})]
    else:
        return d

def mode_clean_up(message_json):
    # Remove any empty fields from the data
    message_json = remove_empty_fields(message_json)
    
    # Access rssiFilter inside the payload, not at the root level
    payload = message_json.get('payload', {})
    rssi_filter = payload.get('rssiFilter', {})
    
    # Set the threshold to -90 if it's empty or not present
    if not rssi_filter.get('threshold'):
        rssi_filter['threshold'] = -92
    
    # Update the rssiFilter in the payload
    payload['rssiFilter'] = rssi_filter
    message_json['payload'] = payload
    
    # Log the cleaned-up message
    logger.info(f'Message after clean-up: {message_json}')
    
    return message_json

def send_firmware_update_command(reader, firmware):
    command_id = str(uuid.uuid4())
    payload = {
        "url": f"{settings.FIRMWARE_URL_BASE}{firmware.file.url}",
        "timeoutInMinutes": 4,
        "maxRetries": 3
    }
    message = {
        "command": "upgrade",
        "command_id": command_id,
        "payload": payload
    }
    topic = f"smartreader/{reader.serial_number}/manage"
    
    from .mqtt_client import publish_message
    try:
        if publish_message(topic, json.dumps(message)):
            logger.info(f"Message published successfully.")
            return True
        else:
            logger.error(f"An exception occurred while publishing the message.")
            return False
    except Exception as e:
        logger.exception(f"Failed to reconnect to MQTT broker: {e}")
        return False
    # client = get_mqtt_client()
    # if not client.is_connected():
    #     logger.error("MQTT client is not connected. Attempting to reconnect...")
    #     try:
    #         mqtt_port = int(settings.MQTT_PORT)
    #         mqtt_broker = settings.MQTT_BROKER
    #         logger.info(f"Connecting to broker at {mqtt_broker}:{mqtt_port}")
    #         client.connect(mqtt_broker, mqtt_port, 60)
    #         logger.info("Reconnected to MQTT broker")
    #     except Exception as e:
    #         logger.exception(f"Failed to reconnect to MQTT broker: {e}")
    #         return False, _("Failed to send command. Please try again.")
    # result = client.publish(topic, json.dumps(message))
    # return result.rc == client.mqtt.MQTT_ERR_SUCCESS
    
def send_command(reader, command_id, command_type, payload=None):
    if not command_type:
        logger.error(f"No command type selected for reader {reader.serial_number}")
        return

    if not payload:
        payload = {}

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

    # message_json = json.dumps(message)
    message_json = message
    
    # if command_type == 'mode':
    #     # Call mode-specific clean-up function
    #     message_json = mode_clean_up(message_json)

    #     if not isinstance(message_json, str):
    #         message_json = json.dumps(message_json)

    from .mqtt_client import publish_message
    try:
        if publish_message(topic, message_json):
            logger.info(f"Message published successfully.")
        else:
            logger.error(f"An exception occurred while publishing the message.")
    except Exception as e:
        logger.exception(f"Failed to reconnect to MQTT broker: {e}")
        return False, _("Failed to send command. Please try again.")

    # from .mqtt_client import get_mqtt_client
    # client = get_mqtt_client()

    # if not client.is_connected():
    #     logger.error("MQTT client is not connected. Attempting to reconnect...")
    #     try:
    #         client.reconnect()
    #         logger.info("Reconnected to MQTT broker")
    #     except Exception as e:
    #         logger.exception(f"Failed to reconnect to MQTT broker: {e}")
    #         return

    # try:
    #     result = client.publish(topic, message_json)
    #     logger.info(f"Message published successfully.")
    #     return True
    # except Exception as e:
    #     logger.exception(f"An exception occurred while publishing the message: {e}")
    #     return False

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
    # Remove any empty fields from the data
    payload = remove_empty_fields(payload)
    
    # Access rssiFilter inside the payload, not at the root level  
    rssi_filter = payload.get('rssiFilter', {})
    
    # Set the threshold to -90 if it's empty or not present
    if not rssi_filter.get('threshold'):
        rssi_filter['threshold'] = -92
    
    # Update the rssiFilter in the payload
    payload['rssiFilter'] = rssi_filter
    
    # Log the cleaned-up message
    logger.info(f'Payload after clean-up: {payload}')

    # command = store_command(reader, 'mode', payload)
    # return send_command(reader, command.command_id, command.command_type, payload)
    # message_json = json.dumps(payload)
    return store_command(reader, 'mode', payload)

def store_command(reader, command_type, details=None):
    try:
        command_id = str(uuid.uuid4())
        command = Command.objects.create(
            command_id = command_id,
            reader=reader,
            command=command_type,
            status='PENDING',
            details=details
        )
        logger.info(f"Command stored: {command}")
        return command
    except Exception as e:
        logger.error(f"Error storing command: {str(e)}")
        raise

def update_command_status(command_id, reader_serial, command_type, status, response):
    try:
        command = Command.objects.filter(
            command_id=command_id,
            reader__serial_number=reader_serial,
            command=command_type
        ).latest('date_sent')
        
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
    elif event_type == "status" or event_type == "status-detailed":
        # 1) Store all non-antenna items and remove "eventType"
        non_antenna_details = {key: value for key, value in payload.items() if 'antenna' not in key and key != "eventType"}
        logger.info(f"Processing status event ({event_type}) for reader {reader.serial_number}")
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

def update_reader_connection_status(reader, is_connected):
    reader.is_connected = is_connected
    reader.save(update_fields=['is_connected', 'last_communication'])
    logger.info(f"Reader {reader.serial_number} connection status updated: {'connected' if is_connected else 'disconnected'}")

def get_alerts(user, search_query, sort_by, page):
    alerts = Alert.objects.filter(user=user)
    
    if search_query:
        alerts = alerts.filter(
            Q(name__icontains=search_query) |
            Q(condition_type__icontains=search_query)
        )
    
    alerts = alerts.order_by(sort_by)
    return get_paginated_items(alerts, page)

def create_alert(form, user):
    alert = form.save(commit=False)
    alert.user = user
    alert.save()
    return alert

def update_alert(form):
    return form.save()

def delete_alert(pk, user):
    alert = get_object_or_404(Alert, pk=pk, user=user)
    alert.delete()

def toggle_alert(pk, user):
    alert = get_object_or_404(Alert, pk=pk, user=user)
    alert.is_active = not alert.is_active
    alert.save()
    return alert

def get_alert_logs(user, search_query, sort_by, page):
    alert_logs = AlertLog.objects.filter(alert__user=user)
    
    if search_query:
        alert_logs = alert_logs.filter(
            Q(alert__name__icontains=search_query) |
            Q(details__icontains=search_query)
        )
    
    alert_logs = alert_logs.order_by(sort_by)
    return get_paginated_items(alert_logs, page)

def get_alert_by_id(pk, user):
    return get_object_or_404(Alert, pk=pk, user=user)

def get_scheduled_commands(search_query, sort_by):
    return ScheduledCommand.objects.filter(
        Q(reader__serial_number__icontains=search_query) |
        Q(command_type__icontains=search_query) |
        Q(recurrence__icontains=search_query)
    ).order_by(sort_by)

def create_scheduled_command(data):
    try:
        scheduled_command = ScheduledCommand.objects.create(**data)
        logger.info(f"Created scheduled command: {scheduled_command}")
        return scheduled_command
    except Exception as e:
        logger.error(f"Error creating scheduled command: {str(e)}")
        raise

def update_scheduled_command(scheduled_command_id, data):
    try:
        scheduled_command = ScheduledCommand.objects.get(id=scheduled_command_id)
        for key, value in data.items():
            setattr(scheduled_command, key, value)
        scheduled_command.save()
        logger.info(f"Updated scheduled command: {scheduled_command}")
        return scheduled_command
    except ScheduledCommand.DoesNotExist:
        logger.error(f"Scheduled command with id {scheduled_command_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error updating scheduled command: {str(e)}")
        raise

def delete_scheduled_command(scheduled_command_id):
    try:
        scheduled_command = ScheduledCommand.objects.get(id=scheduled_command_id)
        scheduled_command.delete()
        logger.info(f"Deleted scheduled command: {scheduled_command}")
    except ScheduledCommand.DoesNotExist:
        logger.error(f"Scheduled command with id {scheduled_command_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error deleting scheduled command: {str(e)}")
        raise

def execute_scheduled_commands():
    now = timezone.now()
    scheduled_commands = ScheduledCommand.objects.filter(is_active=True, scheduled_time__lte=now)
    
    for command in scheduled_commands:
        try:
            from tasks import process_command
            process_command.delay(command.reader.id, command.command)
            logger.info(f"Executed scheduled command: {command}")
            
            if command.recurrence == 'ONCE':
                command.is_active = False
            else:
                if command.recurrence == 'DAILY':
                    command.scheduled_time += timezone.timedelta(days=1)
                elif command.recurrence == 'WEEKLY':
                    command.scheduled_time += timezone.timedelta(weeks=1)
                elif command.recurrence == 'MONTHLY':
                    command.scheduled_time += timezone.timedelta(days=30)  # Approximate
            
            command.last_run = now
            command.save()
        except Exception as e:
            logger.error(f"Error executing scheduled command {command.id}: {str(e)}")

def get_all_firmwares():
    return Firmware.objects.all().order_by('-upload_date')

def upload_firmware(form):
    return form.save()

def get_active_firmwares():
    return Firmware.objects.filter(is_active=True).order_by('-upload_date')

def get_reader(reader_id):
    return get_object_or_404(Reader, id=reader_id)

def get_firmware(firmware_id):
    return get_object_or_404(Firmware, id=firmware_id)

def get_pending_commands():
    """Get all pending commands and update their status to PROCESSING"""
    pending_commands = Command.objects.filter(status='PENDING')
    command_list = []
    
    for command in pending_commands:
        command_data = {
            'id': command.id,
            'command_id': command.command_id,
            'reader_serial': command.reader.serial_number,
            'command': command.command,
            'details': command.details,
            'date_sent': command.date_sent.isoformat() if command.date_sent else None
        }
        command_list.append(command_data)
        command.status = 'PROCESSING'
        command.save()
        
    return command_list
