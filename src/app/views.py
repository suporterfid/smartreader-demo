# views.py
import json
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from .mqtt_client import client

from app.models import DetailedStatusEvent, Reader
from .services import (
    get_tag_events, get_paginated_items, get_readers, send_command,
    handle_mode_command, get_detailed_status_events, send_command_service
)
from .forms import ReaderForm, ModeForm

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

def send_command(request, reader_id):
    if request is None or not hasattr(request, 'user') or not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={request.path}")

    command_type = request.POST.get('command_type')

    if not command_type:
        messages.error(request, _("No command type selected."))
        return redirect('reader_list')

    # Get the payload from the POST data
    payload = request.POST.get('payload')
    parsed_payload = {}

    if payload:
        try:
            parsed_payload = json.loads(payload)
        except json.JSONDecodeError:
            messages.error(request, _("Invalid JSON payload provided."))
            return redirect('reader_list')

    # Use the service to send the command
    success, message = send_command_service(request, reader_id, command_type, client, parsed_payload)
    
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect('reader_list')

@login_required
def send_command_to_readers(request):
    if request.method == 'POST':
        reader_ids = request.POST.getlist('reader_ids')
        command_type = request.POST.get('command')
        readers = Reader.objects.filter(id__in=reader_ids)

        for reader in readers:
            send_command(reader, command_type, client)
        
        return redirect('reader_list')

@login_required
def mode_command(request, reader_id):
    reader = get_object_or_404(Reader, id=reader_id)
    if request.method == 'POST':
        form = ModeForm(request.POST)
        if form.is_valid():
            handle_mode_command(reader, form.cleaned_data)
            return redirect('reader_list')
    else:
        form = ModeForm()
    return render(request, 'app/mode_form.html', {'form': form, 'reader': reader})

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

def home(request):
    return redirect('reader_list')
