from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils.translation import gettext as _
from .authentication import APIKeyAuthentication
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Reader, TagEvent, Command
from .serializers import ReaderSerializer, TagEventSerializer, CommandSerializer
from .services import send_command_service, store_command

import logging

logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000

class ReaderListView(generics.ListAPIView):
    queryset = Reader.objects.all()
    serializer_class = ReaderSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Reader.objects.all()
        serial_number = self.request.query_params.get('serial_number', None)
        if serial_number is not None:
            queryset = queryset.filter(serial_number__icontains=serial_number)
        return queryset

class ReaderDetailView(generics.RetrieveAPIView):
    queryset = Reader.objects.all()
    serializer_class = ReaderSerializer
    lookup_field = 'serial_number'

class TagEventListView(generics.ListAPIView):
    queryset = TagEvent.objects.all()
    serializer_class = TagEventSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = TagEvent.objects.all()
        epc = self.request.query_params.get('epc', None)
        reader_serial = self.request.query_params.get('reader_serial', None)
        if epc is not None:
            queryset = queryset.filter(epc__icontains=epc)
        if reader_serial is not None:
            queryset = queryset.filter(reader__serial_number=reader_serial)
        return queryset
    
@method_decorator(csrf_exempt, name='dispatch')
class CommandCreateView(generics.CreateAPIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CommandSerializer

    def create(self, request, *args, **kwargs):
        success = False
        command = None
        reader_serial_number = None
        command_type = None
        details = None
        reader = None
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Read values from the serializer
            reader_serial_number = serializer.validated_data['reader_serial_number']
            command_type = serializer.validated_data['command_type']
            details = serializer.validated_data.get('details')
            # Log the received data
            logger.info(f"Received command: type={command_type}, reader={reader_serial_number}, details={details}")

            # Get the reader instance
            try:
                reader = Reader.objects.get(serial_number=reader_serial_number)
            except Reader.DoesNotExist:
                return Response({'error': _('Reader not found')}, status=status.HTTP_404_NOT_FOUND)
            
            command = store_command(reader, command_type, details)
            success = True
            logger.info(f"Command stored: type={command_type}, reader={reader_serial_number}, details={details}")
            # command = self.perform_create(serializer)
            # command = serializer.save()
            # headers = self.get_success_headers(serializer.data)
            
        except Exception as e:
            logger.error(f"CommandCreateView - Error storing command: {str(e)}")

        # Send the command
        # reader = command.reader
        # success, message = store_command(reader, command.command, command.details)
        # success, message = send_command_service(request, reader.id, command.command_id, command.command, command.details)

        if success:
            logger.info(f"API command sent successfully: {command_type} to {reader_serial_number}")
            serializer = self.get_serializer(command)  # Serialize the created command
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            logger.error(f"API command failed: {command_type} to {reader_serial_number}.")
            return Response({'error': _('Failed to send command')}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        return serializer.save()