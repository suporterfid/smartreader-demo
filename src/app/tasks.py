#tasks.py

from django.utils import timezone
import logging
from celery import shared_task
from .models import Command
from .services import send_command_service
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)

@shared_task
def process_pending_commands():
    pending_commands = Command.objects.filter(status='PENDING')
    for command in pending_commands:
        command.status = 'PROCESSING'
        command.save()
        try:
            success, message = send_command_service(None, command.reader.id, command.command_type)
            if success:
                command.status = 'COMPLETED'
                command.response = message
            else:
                command.status = 'FAILED'
                command.response = message
        except Exception as e:
            logger.error(f"Error processing command {command.id}: {str(e)}")
            command.status = 'FAILED'
            command.response = f"Unexpected error: {str(e)}"
        finally:
            command.updated_at = timezone.now()
            command.save()

@shared_task
def cleanup_stale_commands():
    timeout = timezone.now() - timezone.timedelta(seconds=30)
    stale_commands = Command.objects.filter(status='PROCESSING', updated_at__lt=timeout)
    for command in stale_commands:
        command.status = 'FAILED'
        command.response = "Command processing timed out"
        command.save()
        logger.warning(f"Command {command.id} timed out and marked as failed")

@shared_task
def process_and_cleanup_commands():
    process_pending_commands()
    cleanup_stale_commands()
        
@shared_task
def process_command(command_id):
    #from .mqtt_client import client
    command = None
    try:
        command = Command.objects.get(id=command_id)
        command.status = 'PROCESSING'
        command.save()

        success, message = send_command_service(None, command.reader.id, command.command)

        if success:
            command.status = 'COMPLETED'
            command.response = message
        else:
            command.status = 'FAILED'
            command.response = message

        command.save()
        logger.info(f"Command {command_id} processed with status: {command.status}")
    except ObjectDoesNotExist:
        logger.error(f"Command with id {command_id} not found")
    except ValueError as e:
        logger.error(f"Error processing command {command_id}: Invalid return value from send_command_service - {str(e)}")
        if command:
            command.status = 'FAILED'
            command.response = f"Error: {str(e)}"
            command.save()
    except Exception as e:
        logger.error(f"Error processing command {command_id}: {str(e)}")
        if command:
            command.status = 'FAILED'
            command.response = f"Unexpected error: {str(e)}"
            command.save()
    finally:
        if command and command.status == 'PROCESSING':
            command.status = 'FAILED'
            command.response = "Command processing interrupted unexpectedly"
            command.save()

@shared_task
def execute_scheduled_commands_task():
    from .services import execute_scheduled_commands
    execute_scheduled_commands()