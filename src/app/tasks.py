#tasks.py

import logging
from celery import shared_task
from .models import Command
from .services import send_command_service
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)

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