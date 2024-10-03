import uuid
from rest_framework import serializers
from .models import Reader, TagEvent, Command

class ReaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reader
        fields = ['serial_number', 'ip_address', 'location', 'last_communication', 'enabled', 'is_connected']

class TagEventSerializer(serializers.ModelSerializer):
    reader_serial_number = serializers.CharField(source='reader.serial_number')

    class Meta:
        model = TagEvent
        fields = ['reader_serial_number', 'epc', 'first_seen_timestamp', 'antenna_port', 'antenna_zone', 'peak_rssi']

from rest_framework import serializers
from .models import Command, Reader
from .services import store_command

class CommandSerializer(serializers.ModelSerializer):
    reader_serial_number = serializers.CharField(write_only=True)
    command_type = serializers.CharField()
    details = serializers.JSONField(required=False)
    
    class Meta:
        model = Command
        fields = ['command_id', 'reader_serial_number', 'command_type', 'details', 'status']
        read_only_fields = ['command_id', 'status']

    def create(self, validated_data):
        reader_serial_number = validated_data.pop('reader_serial_number')
        try:
            reader = Reader.objects.get(serial_number=reader_serial_number)
        except Reader.DoesNotExist:
            raise serializers.ValidationError("Reader with this serial number does not exist.")
        
        command_type = validated_data.get('command_type')
        details = validated_data.get('details')
        
        return store_command(reader, command_type, details)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['reader_serial_number'] = instance.reader.serial_number
        representation['command_type'] = instance.command_type
        representation['details'] = instance.details
        return representation

    def validate_reader_serial_number(self, value):
        try:
            Reader.objects.get(serial_number=value)
        except Reader.DoesNotExist:
            raise serializers.ValidationError("Reader with this serial number does not exist.")
        return value