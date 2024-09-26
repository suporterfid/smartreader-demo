import logging
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from .models import DetailedStatusEvent, Reader, TagEvent
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import ReaderForm, ModeForm
from django.utils.translation import gettext as _
import uuid
from .mqtt_client import client
import paho.mqtt.client as mqtt
import json

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add handler if not already configured
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

@login_required
def tag_event_list(request):
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-first_seen_timestamp')
    export = request.GET.get('export', '')
    tag_events = TagEvent.objects.filter(
        Q(epc__icontains=search_query) |
        Q(reader__serial_number__icontains=search_query) |
        Q(reader_name__icontains=search_query)
    ).order_by(sort_by)
    if export == 'csv':
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tag_events.csv"'
        writer = csv.writer(response)
        writer.writerow(['EPC', 'Reader Serial Number', 'First Seen Timestamp', 'Antenna Port', 'Antenna Zone', 'Peak RSSI'])
        for event in tag_events:
            writer.writerow([
                event.epc,
                event.reader.serial_number,
                event.first_seen_timestamp,
                event.antenna_port,
                event.antenna_zone,
                event.peak_rssi,
            ])
        return response
    paginator = Paginator(tag_events, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'app/tag_event_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by
    })

@login_required
def reader_list(request):
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'serial_number')
    readers = Reader.objects.filter(
        Q(serial_number__icontains=search_query) |
        Q(ip_address__icontains=search_query) |
        Q(location__icontains=search_query)
    ).order_by(sort_by)
    paginator = Paginator(readers, 10)  # Show 10 readers per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'app/reader_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by
    })

@login_required
def reader_create(request):
    if request.method == 'POST':
        form = ReaderForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('reader_list')
    else:
        form = ReaderForm()
    return render(request, 'app/reader_form.html', {'form': form})

def send_command(reader, command_type, payload={}):
    logger.info(f"Preparing to send command '{command_type}' to reader '{reader.serial_number}'")
    if command_type == 'mode' and not payload:
        logger.error("Mode command requires a payload but none was provided")
        return
    if command_type == 'status-detailed':
        topic = f'smartreader/{reader.serial_number}/manage'
    else:
        topic = f'smartreader/{reader.serial_number}/control'
    command_id = str(uuid.uuid4())
    message = {
        'command': command_type,
        'command_id': command_id,
        'payload': payload
    }
    message_json = json.dumps(message)
    logger.info(f"Publishing message to topic '{topic}': {message_json}")
    # Ensure the client is connected
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
        else:
            logger.error(f"Failed to publish message. Error code: {result}")
    except Exception as e:
        logger.exception(f"An exception occurred while publishing the message: {e}")


def send_command_to_readers(request):
    if request.method == 'POST':
        reader_ids = request.POST.getlist('reader_ids')
        command_type = request.POST.get('command')
        readers = Reader.objects.filter(id__in=reader_ids)
        if command_type == 'mode':
            if len(readers) == 1:
                return redirect('mode_command', reader_id=readers[0].id)
            else:
                # Optional: Handle multiple readers for mode command
                pass
        else:
            for reader in readers:
                send_command(reader, command_type)
        return redirect('reader_list')
    
@login_required
def mode_command(request, reader_id):
    reader = get_object_or_404(Reader, id=reader_id)
    if request.method == 'POST':
        form = ModeForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
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
            send_command(reader, 'mode', payload)
            return redirect('reader_list')
    else:
        form = ModeForm()
    return render(request, 'app/mode_form.html', {'form': form, 'reader': reader})

@login_required
def detailed_status_event_list(request):
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-timestamp')
    events = DetailedStatusEvent.objects.filter(
        Q(reader__serial_number__icontains=search_query) |
        Q(event_type__icontains=search_query) |
        Q(component__icontains=search_query) |
        Q(status__icontains=search_query)
    ).order_by(sort_by)
    paginator = Paginator(events, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'app/detailed_status_event_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by
    })

@login_required
def detailed_status_event_detail(request, event_id):
    event = get_object_or_404(DetailedStatusEvent, id=event_id)
    filter_query = request.GET.get('filter', '')
    return render(request, 'app/detailed_status_event_detail.html', {
        'event': event,
        'filter_query': filter_query
    })

def home(request):
    return redirect('reader_list')