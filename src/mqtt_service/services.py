import logging
from datetime import datetime
from django.utils import timezone
from app.models import Reader, TagEvent, DetailedStatusEvent
from app.services import update_reader_connection_status, update_reader_last_communication

logger = logging.getLogger(__name__)

def process_mqtt_message(topic: str, payload: dict) -> bool:
    """Process an MQTT message and store it in the database"""
    try:
        serial_number = topic.split('/')[1]
        reader = update_reader_last_communication(serial_number)
        if reader is None:
            logger.warning(f"No reader found for serial number: {serial_number}")
            return False

        if '/tagEvents' in topic:
            tag_reads = payload.get('tag_reads', [])
            process_tag_events(reader, tag_reads)
            return True
                
        elif '/lwt' in topic:
            mqtt_status = payload.get('smartreader-mqtt-status')
            if mqtt_status == 'disconnected':
                update_reader_connection_status(reader, False)
            store_detailed_status_event(reader, payload)
            return True
                
        elif '/event' in topic:
            mqtt_status = payload.get('smartreader-mqtt-status')
            if mqtt_status == 'connected':
                update_reader_connection_status(reader, True)
            store_detailed_status_event(reader, payload)
            return True
                
        elif '/manageResult' in topic or '/controlResult' in topic:
            return process_command_response(reader, payload, serial_number)

        return True

    except Exception as e:
        logger.error(f"Error processing MQTT message: {str(e)}", exc_info=True)
        return False

def process_tag_events(reader: Reader, tag_reads: list) -> None:
    """Process and store tag events"""
    for tag_read in tag_reads:
        epc = tag_read.get('epc', '')
        first_seen_timestamp = tag_read.get('firstSeenTimestamp', 0)

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
        logger.info(f"Stored tag event for EPC {epc}")

def store_detailed_status_event(reader: Reader, payload: dict) -> None:
    """Store a detailed status event"""
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
    elif "smartreader-mqtt-status" in payload:
        mqtt_status = payload.get("smartreader-mqtt-status", "")
        non_antenna_details = {"mqtt_status": mqtt_status}
        event_type = "mqtt-status"
    elif event_type in ["status", "status-detailed"]:
        non_antenna_details = {key: value for key, value in payload.items() 
                             if 'antenna' not in key and key != "eventType"}
    else:
        non_antenna_details = {k: v for k, v in payload.items() 
                             if 'antenna' not in k.lower()}

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

def process_command_response(reader: Reader, payload: dict, serial_number: str) -> bool:
    """Process a command response message"""
    try:
        update_reader_connection_status(reader, True)
        
        command_type = payload.get('command', 'unknown')
        command_status = payload.get('response', '')
        command_id = payload.get('command_id', 'unknown')
        command_message = payload.get('message', '')
        
        status = 'COMPLETED' if command_status == 'success' else 'FAILED'
        
        response_parts = []
        if command_status:
            response_parts.append(command_status)
        if command_message:
            response_parts.append(command_message)
        
        response = " ".join(filter(None, response_parts))
        
        logger.info(
            f'Command Response - ID: {command_id}, '
            f'Serial: {serial_number}, '
            f'Type: {command_type}, '
            f'Status: {status}, '
            f'Response: {response}'
        )
        
        from app.services import update_command_status
        update_command_status(
            command_id=command_id,
            reader_serial=serial_number,
            command_type=command_type,
            status=status,
            response=response if response else 'No response message'
        )
        
        return True

    except Exception as e:
        logger.error(
            f"Error processing command response - "
            f"Serial: {serial_number}, "
            f"Payload: {payload}, "
            f"Error: {str(e)}", 
            exc_info=True
        )
        return False
