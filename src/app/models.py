from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Create your models here.

class Reader(models.Model):
    serial_number = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField()
    location = models.CharField(max_length=255, blank=True, null=True)
    last_communication = models.DateTimeField(blank=True, null=True)
    enabled = models.BooleanField(default=True)

class Command(models.Model):
    COMMAND_TYPES = [
        ('start', _('Start')),
        ('stop', _('Stop')),
        ('status-detailed', _('Status Detailed')),
        ('mode', _('Mode')),
    ]
    COMMAND_STATUS = [
        ('PENDING', _('Pending')),
        ('PROCESSING', _('Processing')),
        ('COMPLETED', _('Completed')),
        ('FAILED', _('Failed')),
    ]
    command_type = models.CharField(max_length=50, choices=COMMAND_TYPES, verbose_name=_('Command Type'))
    reader = models.ForeignKey(Reader, on_delete=models.CASCADE, verbose_name=_('Reader'))
    command = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Command'))
    details = models.TextField(default=None, blank=True, null=True, verbose_name=_('Details'))
    status = models.CharField(max_length=50, choices=COMMAND_STATUS, default='PENDING', verbose_name=_('Status'))
    date_sent = models.DateTimeField(auto_now_add=True, verbose_name=_('Date Sent'))
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True, verbose_name=_('Updated At'))
    response = models.TextField(default=None, blank=True, null=True, verbose_name=_('Response'))  
    
    class Meta:
        verbose_name = _('Command')
        verbose_name_plural = _('Commands')

    def __str__(self):
        return f"{self.reader.serial_number} - {self.command} ({self.status})"

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