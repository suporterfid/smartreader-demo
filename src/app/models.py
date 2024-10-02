from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

# Create your models here.

class Reader(models.Model):
    serial_number = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField()
    location = models.CharField(max_length=255, blank=True, null=True)
    last_communication = models.DateTimeField(blank=True, null=True)
    enabled = models.BooleanField(default=True)
    is_connected = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.serial_number} - {self.ip_address}"
    
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
    command_id = models.CharField(max_length=50, default=None, blank=True, null=True, verbose_name=_('Command ID'))
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
    
class Alert(models.Model):
    CONDITION_TYPES = [
        ('tag_frequency', _('Tag Read Frequency')),
        ('reader_status', _('Reader Status Change')),
        ('tag_pattern', _('Specific Tag Pattern')),
        ('access_violation', _('Access Control Violation')),
    ]
    NOTIFICATION_METHODS = [
        ('email', _('Email')),
        ('in_app', _('In-App Notification')),
    ]
    name = models.CharField(_('Name'), max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('User'))
    condition_type = models.CharField(_('Condition Type'), max_length=20, choices=CONDITION_TYPES)
    condition_params = models.JSONField(_('Condition Parameters'))
    notification_method = models.CharField(_('Notification Method'), max_length=10, choices=NOTIFICATION_METHODS)
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    def __str__(self):
        return self.name

class AlertLog(models.Model):
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, verbose_name=_('Alert'))
    triggered_at = models.DateTimeField(_('Triggered At'), auto_now_add=True)
    details = models.JSONField(_('Details'))

    def __str__(self):
        return f"{self.alert.name} - {self.triggered_at}"
    
class ScheduledCommand(models.Model):
    RECURRENCE_CHOICES = [
        ('ONCE', _('Once')),
        ('DAILY', _('Daily')),
        ('WEEKLY', _('Weekly')),
        ('MONTHLY', _('Monthly')),
    ]

    reader = models.ForeignKey(Reader, on_delete=models.CASCADE, verbose_name=_('Reader'))
    command_type = models.CharField(max_length=50, choices=Command.COMMAND_TYPES, verbose_name=_('Command Type'))
    scheduled_time = models.DateTimeField(verbose_name=_('Scheduled Time'))
    recurrence = models.CharField(max_length=10, choices=RECURRENCE_CHOICES, default='ONCE', verbose_name=_('Recurrence'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    last_run = models.DateTimeField(null=True, blank=True, verbose_name=_('Last Run'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Scheduled Command')
        verbose_name_plural = _('Scheduled Commands')

    def __str__(self):
        return f"{self.reader.serial_number} - {self.command_type} ({self.get_recurrence_display()})"
    
class TaskExecution(models.Model):
    task_name = models.CharField(max_length=255)
    is_executed = models.BooleanField(default=False)

    def __str__(self):
        return self.task_name
    
    @classmethod
    def reset_task_status(cls, task_name):
        """
        Resets the execution status of the task, allowing it to run again.
        """
        try:
            task_exec = cls.objects.get(task_name=task_name)
            task_exec.is_executed = False
            task_exec.save()
            print(f"Task {task_name} status reset to allow execution.")
        except cls.DoesNotExist:
            # If the task doesn't exist, create it with the default status
            cls.objects.create(task_name=task_name, is_executed=False)
            print(f"Task {task_name} created with reset status.")

class Firmware(models.Model):
    version = models.CharField(max_length=50, unique=True)
    file = models.FileField(
        upload_to='firmware/',
        validators=[FileExtensionValidator(allowed_extensions=['upgx'])]
    )
    description = models.TextField(blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    checksum = models.CharField(default=None, null=True, blank=True, max_length=64)  # For file integrity

    def __str__(self):
        return f"Firmware v{self.version}"

    def save(self, *args, **kwargs):
        if not self.pk:  # Only on create
            self.checksum = self.calculate_checksum()
        super().save(*args, **kwargs)

    def calculate_checksum(self):
        # Implement checksum calculation here
        pass

class FirmwareUpdateStatus(models.Model):
    reader = models.ForeignKey(Reader, on_delete=models.CASCADE)
    firmware = models.ForeignKey(Firmware, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', _('Pending')),
        ('IN_PROGRESS', _('In Progress')),
        ('COMPLETED', _('Completed')),
        ('FAILED', _('Failed'))
    ])
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Firmware update for {self.reader.serial_number}: {self.status}"
