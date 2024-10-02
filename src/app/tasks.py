# app/tasks.py

from __future__ import absolute_import, unicode_literals
from django.utils import timezone
import logging
import threading
from celery import shared_task
from .models import Command, TaskExecution
from .services import send_command_service
from django.core.exceptions import ObjectDoesNotExist


logger = logging.getLogger(__name__)

# def silence_task_logs(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         logger = logging.getLogger('celery.task')
#         original_level = logger.level
#         logger.setLevel(logging.ERROR)  # Only log errors
#         try:
#             return func(*args, **kwargs)
#         finally:
#             logger.setLevel(original_level)
#     return wrapper

@shared_task
def process_pending_commands():
    print('>>>>>>>> process_pending_commands')
    pending_commands = Command.objects.filter(status='PENDING')
    for command in pending_commands:
        print(f'command: {command.command}')
        command.status = 'PROCESSING'
        command.save()
        try:
            success, message = send_command_service(None, command.reader.id, command.command_id, command.command, command.details)
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
    print("Processing and cleaning up commands")
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

        success, message = send_command_service(None, command.reader.id, command.command_id, command.command_type, command.details)

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
    print("Executing scheduled commands")
    from .services import execute_scheduled_commands
    execute_scheduled_commands()

# @shared_task
# def setup_periodic_tasks():
#     logger.info('********STARTING PERIODIC TASKS SETUP********')
#     try:
#         # Set up Process and Cleanup Commands task (every 10 seconds)
#         interval, _ = IntervalSchedule.objects.get_or_create(
#             every=10,
#             period=IntervalSchedule.SECONDS,
#         )
#         PeriodicTask.objects.get_or_create(
#             name='Process and Cleanup Commands',
#             task='app.tasks.process_and_cleanup_commands',
#             interval=interval,
#         )
#         logger.info('Added periodic task: Process and Cleanup Commands (every 10 seconds)')
        
#         # Set up Execute Scheduled Commands task (every minute)
#         crontab, _ = CrontabSchedule.objects.get_or_create(
#             minute='*',
#             hour='*',
#             day_of_week='*',
#             day_of_month='*',
#             month_of_year='*',
#         )
#         PeriodicTask.objects.get_or_create(
#             name='Execute Scheduled Commands',
#             task='app.tasks.execute_scheduled_commands_task',
#             crontab=crontab,
#         )
#         logger.info('Added periodic task: Execute Scheduled Commands (every minute)')
        
#         logger.info('********PERIODIC TASKS SETUP COMPLETE********')
#     except Exception as e:
#         logger.exception(f"An unexpected error occurred while setting up periodic tasks: {e}")
    
#     logger.info('********EXITING PERIODIC TASKS SETUP FUNCTION********')

