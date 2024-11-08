# views.py
import os
import logging
import json
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from app.authentication import APIKeyAuthentication

from app.tasks import process_command

from app.models import DetailedStatusEvent, Reader, Command, ScheduledCommand
from .services import (
    get_active_firmwares, get_all_firmwares, get_reader, get_tag_events, get_paginated_items, get_readers, send_command,
    handle_mode_command, get_detailed_status_events,
    store_command, get_alerts, create_alert, update_alert, delete_alert, 
    toggle_alert, get_alert_logs, get_alert_by_id, get_scheduled_commands, 
    create_scheduled_command, update_scheduled_command, delete_scheduled_command, upload_firmware,
    get_firmware, send_firmware_update_command
)
from .forms import FirmwareUploadForm, ReaderForm, ModeForm, AlertForm, ScheduledCommandForm
from app import services

logger = logging.getLogger(__name__)

@login_required
def tag_event_list(request):
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-first_seen_timestamp')
    export = request.GET.get('export', '')
    tag_events = get_tag_events(search_query, sort_by)

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

    page_obj = get_paginated_items(tag_events, request.GET.get('page'))
    return render(request, 'app/tag_event_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by
    })

@login_required
def reader_list(request):
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'serial_number')
    readers = get_readers(search_query, sort_by)
    page_obj = get_paginated_items(readers, request.GET.get('page'))
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

@login_required
def reader_edit(request, pk):
    reader = get_object_or_404(Reader, pk=pk)
    if request.method == 'POST':
        form = ReaderForm(request.POST, instance=reader)
        if form.is_valid():
            form.save()
            return redirect('reader_list')
    else:
        form = ReaderForm(instance=reader)
    return render(request, 'app/reader_form.html', {'form': form})

# def send_command(request, reader_id):
#     if request is None or not hasattr(request, 'user') or not request.user.is_authenticated:
#         return redirect(f"{reverse('login')}?next={request.path}")

#     command_type = request.POST.get('command_type')

#     if not command_type:
#         messages.error(request, _("No command type selected."))
#         return redirect('reader_list')

#     # Get the payload from the POST data
#     payload = request.POST.get('payload')
#     parsed_payload = {}

#     if payload:
#         try:
#             parsed_payload = json.loads(payload)
#         except json.JSONDecodeError:
#             messages.error(request, _("Invalid JSON payload provided."))
#             return redirect('reader_list')

#     # Use the service to send the command
#     success, message = send_command_service(request, reader_id, command_type, client, parsed_payload)
    
#     if success:
#         messages.success(request, message)
#     else:
#         messages.error(request, message)

#     return redirect('reader_list')

def send_command(request, reader_id):
    if request.method == 'POST':
        command_type = request.POST.get('command_type')
        if command_type == 'mode':
            return redirect('mode_command', reader_id=reader_id)
        reader = get_object_or_404(Reader, id=reader_id)

        if not command_type:
            messages.error(request, _("No command type selected."))
            return redirect('reader_list')
        try:
            command = store_command(reader, command_type)
            messages.success(request, _("Command '%(command)s' queued for processing.") % {'command': command_type})
        except Exception as e:
            logger.error(f"Error queueing command: {str(e)}")
            messages.error(request, _("An error occurred while processing the command."))
    return redirect('reader_list')

@login_required
def send_command_to_readers(request):
    if request.method == 'POST':
        reader_ids = request.POST.getlist('reader_ids')
        command_type = request.POST.get('command')
        readers = Reader.objects.filter(id__in=reader_ids)

        # from .mqtt_client import client
        for reader in readers:
            send_command(reader, command_type)
        
        return redirect('reader_list')

@login_required
def mode_command(request, reader_id):
    reader = get_object_or_404(Reader, id=reader_id)
    if request.method == 'POST':
        form = ModeForm(request.POST)
        if form.is_valid():
            handle_mode_command(reader, form.cleaned_data)
            messages.success(request, _('Mode command sent successfully.'))
            return redirect('reader_list')
    else:
        form = ModeForm()
    return render(request, 'app/mode_form.html', {'form': form, 'reader': reader})

def command_history(request):
    search_query = request.GET.get('search', '')
    reader_serial = request.GET.get('reader', '')
    
    commands = Command.objects.all()
    
    if reader_serial:
        commands = commands.filter(reader__serial_number=reader_serial)
    
    if search_query:
        commands = commands.filter(
            Q(reader__serial_number__icontains=search_query) |
            Q(command__icontains=search_query) |
            Q(status__icontains=search_query)
        )
    
    commands = commands.select_related('reader').order_by('-date_sent')

    paginator = Paginator(commands, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'reader_serial': reader_serial,
    }
    return render(request, 'app/command_history.html', context)

@login_required
def command_detail(request, command_id):
    command = get_object_or_404(Command, id=command_id)
    return render(request, 'app/command_detail.html', {'command': command})

@login_required
def detailed_status_event_list(request):
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-timestamp')
    events = get_detailed_status_events(search_query, sort_by)
    page_obj = get_paginated_items(events, request.GET.get('page'))
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

@login_required
def alert_list(request):
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'name')
    page_obj = get_alerts(request.user, search_query, sort_by, request.GET.get('page'))
    
    return render(request, 'app/alert_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by
    })

@login_required
def alert_create(request):
    if request.method == 'POST':
        form = AlertForm(request.POST)
        if form.is_valid():
            create_alert(form, request.user)
            messages.success(request, _('Alert created successfully.'))
            return redirect('alert_list')
    else:
        form = AlertForm()
    return render(request, 'app/alert_form.html', {'form': form})

@login_required
def alert_edit(request, pk):
    alert = get_alert_by_id(pk, request.user)
    if request.method == 'POST':
        form = AlertForm(request.POST, instance=alert)
        if form.is_valid():
            update_alert(form)
            messages.success(request, _('Alert updated successfully.'))
            return redirect('alert_list')
    else:
        form = AlertForm(instance=alert)
    return render(request, 'app/alert_form.html', {'form': form, 'alert': alert})

@login_required
def alert_delete(request, pk):
    if request.method == 'POST':
        delete_alert(pk, request.user)
        messages.success(request, _('Alert deleted successfully.'))
    return redirect('alert_list')

@login_required
def alert_toggle(request, pk):
    alert = toggle_alert(pk, request.user)
    status = _('activated') if alert.is_active else _('deactivated')
    messages.success(request, _(f'Alert {status} successfully.'))
    return redirect('alert_list')

@login_required
def alert_log_list(request):
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-triggered_at')
    page_obj = get_alert_logs(request.user, search_query, sort_by, request.GET.get('page'))
    
    return render(request, 'app/alert_log_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by
    })

@login_required
def scheduled_command_list(request):
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'scheduled_time')
    scheduled_commands = get_scheduled_commands(search_query, sort_by)
    page_obj = get_paginated_items(scheduled_commands, request.GET.get('page'))
    return render(request, 'app/scheduled_command_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by
    })

@login_required
def scheduled_command_create(request):
    if request.method == 'POST':
        form = ScheduledCommandForm(request.POST)
        if form.is_valid():
            try:
                create_scheduled_command(form.cleaned_data)
                messages.success(request, _("Scheduled command created successfully."))
                return redirect('scheduled_command_list')
            except Exception as e:
                messages.error(request, _("Error creating scheduled command: %s") % str(e))
    else:
        form = ScheduledCommandForm()
    return render(request, 'app/scheduled_command_form.html', {'form': form})

@login_required
def scheduled_command_edit(request, pk):
    scheduled_command = get_object_or_404(ScheduledCommand, pk=pk)
    if request.method == 'POST':
        form = ScheduledCommandForm(request.POST, instance=scheduled_command)
        if form.is_valid():
            try:
                update_scheduled_command(pk, form.cleaned_data)
                messages.success(request, _("Scheduled command updated successfully."))
                return redirect('scheduled_command_list')
            except Exception as e:
                messages.error(request, _("Error updating scheduled command: %s") % str(e))
    else:
        form = ScheduledCommandForm(instance=scheduled_command)
    return render(request, 'app/scheduled_command_form.html', {'form': form})

@login_required
def scheduled_command_delete(request, pk):
    if request.method == 'POST':
        try:
            delete_scheduled_command(pk)
            messages.success(request, _("Scheduled command deleted successfully."))
        except Exception as e:
            messages.error(request, _("Error deleting scheduled command: %s") % str(e))
    return redirect('scheduled_command_list')

@login_required
def firmware_list(request):
    firmwares = get_all_firmwares()
    return render(request, 'app/firmware_list.html', {'firmwares': firmwares})

@login_required
def firmware_upload(request):
    if request.method == 'POST':
        form = FirmwareUploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload_firmware(form)
            messages.success(request, _('Firmware uploaded successfully.'))
            return redirect('firmware_list')
    else:
        form = FirmwareUploadForm()
    return render(request, 'app/firmware_upload.html', {'form': form})

@login_required
def firmware_update(request, reader_id):
    reader = get_reader(reader_id)
    firmwares = get_active_firmwares()
    
    if request.method == 'POST':
        firmware_id = request.POST.get('firmware')
        firmware = get_firmware(firmware_id)
        success = send_firmware_update_command(reader, firmware)
        if success:
            messages.success(request, _('Firmware update command sent successfully.'))
        else:
            messages.error(request, _('Failed to send firmware update command.'))
        return redirect('reader_list')
    
    return render(request, 'app/firmware_update.html', {'reader': reader, 'firmwares': firmwares})

def api_docs(request):
    return render(request, 'app/api_docs.html')

class PendingCommandsView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            commands = services.get_pending_commands()
            return Response({'commands': commands})
        except Exception as e:
            logger.error(f"Error retrieving pending commands: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve pending commands'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

def home(request):
    return redirect('reader_list')

class ProcessMQTTMessageView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # This endpoint will be called by Dapr when messages arrive
        try:
            # Extract topic from Dapr cloud event
            topic = request.data.get('topic', '')
            # Extract payload from Dapr cloud event
            payload = request.data.get('data', {})
            
            if not topic or not payload:
                return Response(
                    {'error': 'Both topic and payload are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            from mqtt_service.services import process_mqtt_message
            success = process_mqtt_message(topic, payload)
            
            if success:
                # Return 200 to acknowledge message
                return Response({'status': 'success'})
            else:
                # Return 500 to trigger Dapr retry
                return Response(
                    {'error': 'Failed to process message'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error processing Dapr event: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CleanupStaleCommandsView(APIView):
    """API endpoint to cleanup stale commands"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            timeout = timezone.now() - timezone.timedelta(seconds=30)
            stale_commands = Command.objects.filter(status='PROCESSING', updated_at__lt=timeout)
            count = stale_commands.count()
            
            for command in stale_commands:
                command.status = 'FAILED'
                command.response = "Command processing timed out"
                command.save()
                logger.warning(f"Command {command.id} timed out and marked as failed")
            
            return Response({
                'status': 'success',
                'message': f'Cleaned up {count} stale commands',
                'cleaned_count': count
            })
        except Exception as e:
            logger.error(f"Error cleaning up stale commands: {str(e)}")
            return Response(
                {'error': 'Failed to cleanup stale commands'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PublishMQTTMessageView(APIView):
    """API endpoint to publish MQTT messages"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            topic = request.data.get('topic')
            payload = request.data.get('payload')
            
            if not topic or not payload:
                return Response(
                    {'error': 'Both topic and payload are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            from .mqtt_client import publish_message
            success = publish_message(topic, payload)
            
            if success:
                return Response({
                    'status': 'success',
                    'message': f'Message published to topic {topic}'
                })
            else:
                return Response(
                    {'error': 'Failed to publish message'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error publishing MQTT message: {str(e)}")
            return Response(
                {'error': 'Failed to publish message'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CommandStatusUpdateView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def put(self, request, command_id):
        try:
            command = get_object_or_404(Command, command_id=command_id)
            new_status = request.data.get('status')
            response_message = request.data.get('response', '')
            
            if not new_status:
                return Response(
                    {'error': 'Status is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            if new_status not in ['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED']:
                return Response(
                    {'error': 'Invalid status value'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            command.status = new_status
            command.response = response_message
            command.save()
            
            return Response({
                'command_id': command.command_id,
                'status': command.status,
                'response': command.response
            })
            
        except Exception as e:
            logger.error(f"Error updating command status: {str(e)}")
            return Response(
                {'error': 'Failed to update command status'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
from django.core.management.base import BaseCommand
import logging
import json
import requests
import requests
from django.conf import settings
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the MQTT subscriber service using Dapr'
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def handle(self, *args, **options):
        headers = {'X-API-Key': os.environ.get('API_KEY')}
        from django.core.wsgi import get_wsgi_application
        application = get_wsgi_application()

        logger.info("Starting MQTT subscriber service...")
        
        # Subscribe to MQTT topics via Dapr
        DAPR_HTTP_PORT = 3503
        
        # Subscribe to topics
        subscription = {
            "pubsubname": "mqtt-pubsub",
            "topic": "smartreader/+/controlResult",
            "route": "/api/mqtt/process/"
        }
        
        try:
            response = requests.post(
                f"http://localhost:{DAPR_HTTP_PORT}/dapr/subscribe",
                json=[subscription]
            )
            if response.status_code == 200:
                logger.info("Successfully subscribed to MQTT topics")
            else:
                logger.error(f"Failed to subscribe: {response.status_code}")
                return
                
        except Exception as e:
            logger.error(f"Error subscribing to topics: {e}")
            return

        # Keep the service running
        while True:
            time.sleep(1)
import logging
import json
import requests
from django.conf import settings
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the MQTT subscriber service using Dapr'

    def handle(self, *args, **options):
        from django.core.wsgi import get_wsgi_application
        application = get_wsgi_application()

        logger.info("Starting MQTT subscriber service...")
        
        # Subscribe to MQTT topics via Dapr
        DAPR_HTTP_PORT = 3503
        
        # Subscribe to topics
        subscription = {
            "pubsubname": "mqtt-pubsub",
            "topic": "smartreader/+/controlResult",
            "route": "/api/mqtt/process/"
        }
        
        try:
            response = requests.post(
                f"http://localhost:{DAPR_HTTP_PORT}/dapr/subscribe",
                json=[subscription]
            )
            if response.status_code == 200:
                logger.info("Successfully subscribed to MQTT topics")
            else:
                logger.error(f"Failed to subscribe: {response.status_code}")
                return
                
        except Exception as e:
            logger.error(f"Error subscribing to topics: {e}")
            return

        # Keep the service running
        while True:
            time.sleep(1)
import time
from django.conf import settings
from django.core.management.base import BaseCommand
import logging
import requests
from app.services import send_command_service

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the MQTT publisher service using Dapr'
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def handle(self, *args, **options):
        headers = {'X-API-Key': os.environ.get('API_KEY')}
        from django.core.wsgi import get_wsgi_application
        application = get_wsgi_application()

        logger.info("Starting MQTT publisher service...")
        
        DAPR_HTTP_PORT = 3501
        DJANGO_API_URL = "http://web:8000"
        
        while True:
            try:
                # Get pending commands
                response = requests.get(f"{DJANGO_API_URL}/api/commands/pending/")
                if response.status_code == 200:
                    commands = response.json().get('commands', [])
                    
                    for command in commands:
                        try:
                            # Process command using existing logic
                            success, message = send_command_service(
                                None,
                                command['reader_id'],
                                command['command_id'],
                                command['command'],
                                command['details']
                            )
                            
                            # Publish via Dapr
                            if success:
                                # Publish message using Dapr
                                publish_data = {
                                    "data": message,
                                    "pubsubname": "mqtt-pubsub",
                                    "topic": f"smartreader/{command['reader_serial']}/control"
                                }
                                
                                pub_response = requests.post(
                                    f"http://localhost:{DAPR_HTTP_PORT}/v1.0/publish",
                                    json=publish_data
                                )
                                
                                if pub_response.status_code == 200:
                                    # Update command status
                                    status_data = {
                                        "status": "COMPLETED",
                                        "response": "Command sent successfully"
                                    }
                                else:
                                    status_data = {
                                        "status": "FAILED",
                                        "response": f"Failed to publish: {pub_response.status_code}"
                                    }
                                    
                                requests.put(
                                    f"{DJANGO_API_URL}/api/commands/{command['command_id']}/status/",
                                    json=status_data
                                )
                                
                        except Exception as e:
                            logger.error(f"Error processing command {command['command_id']}: {e}")
                            
                            # Update command status as failed
                            status_data = {
                                "status": "FAILED",
                                "response": f"Error: {str(e)}"
                            }
                            requests.put(
                                f"{DJANGO_API_URL}/api/commands/{command['command_id']}/status/",
                                json=status_data
                            )
                            
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                
            time.sleep(5)  # Wait before next poll

# Initialize the dapr_integration package
import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class DaprPubSub:
    def __init__(self, pubsub_name="mqtt-pubsub", dapr_port=3500):
        self.pubsub_name = pubsub_name
        self.dapr_url = f"http://localhost:{dapr_port}/v1.0"
        
    def publish(self, topic: str, data: dict) -> bool:
        """Publish a message to a topic via Dapr"""
        try:
            url = f"{self.dapr_url}/publish/{self.pubsub_name}/{topic}"
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                logger.info(f"Successfully published message to {topic}")
                return True
            else:
                logger.error(f"Failed to publish message: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing message: {str(e)}")
            return False
            
    def subscribe(self, topic: str, route: str):
        """Subscribe to a topic"""
        try:
            subscription = {
                "pubsubname": self.pubsub_name,
                "topic": topic,
                "route": route
            }
            
            url = f"{self.dapr_url}/subscribe"
            response = requests.post(url, json=[subscription])
            
            if response.status_code == 200:
                logger.info(f"Successfully subscribed to {topic}")
                return True
            else:
                logger.error(f"Failed to subscribe: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error subscribing to topic: {str(e)}")
            return False

# Create a singleton instance
dapr_pubsub = DaprPubSub()
import json
import logging
import requests
from typing import Any, Optional

logger = logging.getLogger(__name__)

class DaprState:
    def __init__(self, store_name="statestore", dapr_port=3500):
        self.store_name = store_name
        self.dapr_url = f"http://localhost:{dapr_port}/v1.0"
        
    def save_state(self, key: str, value: Any) -> bool:
        """Save a value to the state store"""
        try:
            url = f"{self.dapr_url}/state/{self.store_name}"
            state_item = [{
                "key": key,
                "value": value
            }]
            
            response = requests.post(url, json=state_item)
            
            if response.status_code == 204:
                logger.info(f"Successfully saved state for key {key}")
                return True
            else:
                logger.error(f"Failed to save state: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
            return False
            
    def get_state(self, key: str) -> Optional[Any]:
        """Get a value from the state store"""
        try:
            url = f"{self.dapr_url}/state/{self.store_name}/{key}"
            response = requests.get(url)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return None
            else:
                logger.error(f"Failed to get state: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting state: {str(e)}")
            return None

# Create a singleton instance
dapr_state = DaprState()
from django.conf import settings

# Dapr configuration settings
DAPR_HTTP_PORT = getattr(settings, 'DAPR_HTTP_PORT', 3500)
DAPR_GRPC_PORT = getattr(settings, 'DAPR_GRPC_PORT', 50001)
DAPR_PUBSUB_NAME = getattr(settings, 'DAPR_PUBSUB_NAME', 'mqtt-pubsub')
DAPR_STATE_STORE = getattr(settings, 'DAPR_STATE_STORE', 'statestore')

# MQTT topics configuration
MQTT_TOPICS = [
    'smartreader/+/controlResult',
    'smartreader/+/manageResult', 
    'smartreader/+/tagEvents',
    'smartreader/+/event',
    'smartreader/+/metrics',
    'smartreader/+/lwt'
]
