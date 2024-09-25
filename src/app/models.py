from django.db import models
from django.utils import timezone

# Create your models here.

class Reader(models.Model):
    serial_number = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField()
    location = models.CharField(max_length=255, blank=True, null=True)
    last_communication = models.DateTimeField(blank=True, null=True)
    enabled = models.BooleanField(default=True)

class Command(models.Model):
    COMMAND_TYPES = [
        ('start', 'Start'),
        ('stop', 'Stop'),
        ('status-detailed', 'Status Detailed'),
        ('mode', 'Mode'),
    ]
    command_type = models.CharField(max_length=50, choices=COMMAND_TYPES)
    reader = models.ForeignKey(Reader, on_delete=models.CASCADE)
    date_sent = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50)
    details = models.TextField()

class TagEvent(models.Model):
    reader = models.ForeignKey(Reader, on_delete=models.CASCADE)
    reader_name = models.CharField(max_length=255)
    mac_address = models.CharField(max_length=255)
    epc = models.CharField(max_length=255)
    first_seen_timestamp = models.DateTimeField()
    antenna_port = models.IntegerField()
    antenna_zone = models.CharField(max_length=255)
    peak_rssi = models.FloatField()
    tx_power = models.FloatField()
    tag_data_key = models.CharField(max_length=255)
    tag_data_key_name = models.CharField(max_length=255)
    tag_data_serial = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.epc} - {self.reader.serial_number}"
    
class DetailedStatusEvent(models.Model):
    reader = models.ForeignKey(Reader, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=255)
    component = models.CharField(max_length=255)
    timestamp = models.DateTimeField()
    mac_address = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    details = models.JSONField()
    non_antenna_details = models.JSONField(default=dict, null=True, blank=True)

    def __str__(self):
        return f"{self.reader.serial_number} - {self.timestamp}"