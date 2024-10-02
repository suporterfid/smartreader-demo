# config/celery.py
from __future__ import absolute_import, unicode_literals

import os

import sys
from pathlib import Path

# Add the project root directory to Python's sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
import logging
from datetime import timedelta
from celery.signals import celeryd_init
from celery.schedules import schedule
from celery.schedules import crontab
from celery import Celery
from celery.signals import after_setup_logger, import_modules, task_rejected, task_unknown
from celery.schedules import crontab
# from app import tasks

# Set up logging
logger = logging.getLogger(__name__)



# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create the Celery app
app = Celery('config')

# Load task modules from all registered Django app configs.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Ensure the app uses the Django-Celery-Beat scheduler
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'

# Explicitly set the scheduler (optional)
app.conf.beat_scheduler = 'celery.beat.PersistentScheduler'

app.autodiscover_tasks()

# @import_modules.connect
# def handle_import_modules(sender=None, **kwargs):
#     try:
#         # Auto-discover tasks in all installed apps
#         app.autodiscover_tasks()
#         print('TASK AUTO-DISCOVER DONE. ')
#     except Exception as e:
#         logger.error(f"Error during task autodiscovery: {e}", exc_info=True)

# @app.task
# def test_scheduled_task():
#     logger.info("This is a test scheduled task")



# @app.on_after_configure.connect
# def setup_periodic_tasks(sender, **kwargs):
#     logger.info("Setting up periodic tasks")
#     print("-------------------Loading beat schedule...-------------------")
#     try:
#         # Define your periodic tasks here
#         app.conf.beat_schedule = {
#             'test-task-every-30-seconds': {
#                 'task': 'config.celery.test_scheduled_task',
#                 'schedule': 30.0,
#             },
#             'process-and-cleanup-commands': {
#                 'task': 'app.tasks.process_and_cleanup_commands',
#                 'schedule': 10.0,  # every 10 seconds
#             },
#             'execute-scheduled-commands': {
#                 'task': 'app.tasks.execute_scheduled_commands_task',
#                 'schedule': crontab(minute='*/1'),  # every minute
#             },
#         }
#         logger.info(f"Beat schedule: {sender.conf.beat_schedule}")
#     except Exception as e:
#         logger.exception(f">>>>>>>>> setup_periodic_tasks ERROR: An unexpected error occurred while setting up periodic tasks: {e}")

# @app.task(bind=True)
# def debug_task(self):
#     print(f'Request: {self.request!r}')

# @task_rejected.connect
# def handle_task_rejected(sender=None, headers=None, body=None, **kwargs):
#     logger.error(f"Task rejected: {headers} {body}")

# @task_unknown.connect
# def handle_task_unknown(sender=None, name=None, id=None, **kwargs):
#     logger.error(f"Unknown task: {name} (id: {id})")

if __name__ == '__main__':
    app.start()

# @celeryd_init.connect
# def call_setup_periodic_tasks(**kwargs):
#     from app.tasks import setup_periodic_tasks
#     setup_periodic_tasks.delay()

# @celeryd_init.connect
# def configure_workers(sender=None, conf=None, **kwargs):
#     setup_periodic_tasks(sender)

# @celeryd_init.connect
# def configure_workers(sender=None, conf=None, **kwargs):
#     logger.info('Configuring worker')

#@app.on_after_finalize.connect
# def setup_periodic_tasks(sender, **kwargs):
#     print('********STARTING PERIODIC TASKS********')
#     try:

#         logger.info(f'Sender object: {sender}')
#         logger.info(f'Sender type: {type(sender)}')
        
#         if sender is None:
#             logger.error('Sender object is None. Cannot set up periodic tasks.')
#             return

#         if not hasattr(sender, 'add_periodic_task'):
#             logger.error('Sender object does not have add_periodic_task method. Cannot set up periodic tasks.')
#             return
        
#         from celery.schedules import crontab
#         # Import the tasks
#         from app.tasks import process_and_cleanup_commands, execute_scheduled_commands_task
        
#         logger.info('********IMPORT SUCCESSFUL********')
        
#         # Explicitly schedule the tasks here
        
#         logger.info('Attempting to add Process and Cleanup Commands task')
#         # Process and Cleanup Commands every 10 seconds
#         task = sender.add_periodic_task(
#             10.0,
#             process_and_cleanup_commands.s(),
#             name='Process and Cleanup Commands'
#         )
#         logger.info(f'Added periodic task: Process and Cleanup Commands (every 10 seconds). Task object: {task}')
        
#         logger.info('Attempting to add Execute Scheduled Commands task')
        
#         # Execute Scheduled Commands every minute
#         task = sender.add_periodic_task(
#             crontab(minute='*/1'),
#             execute_scheduled_commands_task.s(),
#             name='Execute Scheduled Commands'
#         )
#         logger.info(f'Added periodic task: Execute Scheduled Commands (every minute). Task object: {task}')
        
#         logger.info('********PERIODIC TASKS SETUP COMPLETE********')
#     except ImportError as e:
#         logger.error(f">>>>>>>>> setup_periodic_tasks ERROR: Failed to import tasks: {e}")
#     except AttributeError as e:
#         logger.error(f">>>>>>>>> setup_periodic_tasks ERROR: Task not found or not callable: {e}")
#     except Exception as e:
#         logger.exception(f">>>>>>>>> setup_periodic_tasks ERROR: An unexpected error occurred while setting up periodic tasks: {e}")
    
#     logger.info('********EXITING PERIODIC TASKS SETUP FUNCTION********')



# @app.task
# def test_task(arg):
#     print(arg)
#     logger.info(f'Test task executed with argument: {arg}')

# app.conf.update(
#     task_time_limit=None,  # Allow long-running tasks
#     task_soft_time_limit=None,
# )

# REMOVED DUE TO USE OF THE DATABASE SCHEDULER:
# app.conf.beat_scheduler = 'celery.beat.PersistentScheduler'
# app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'
# app.conf.beat_schedule = {
#     'run-process-and-cleanup-commands': {
#         'task': 'app.tasks.process_and_cleanup_commands',
#         'schedule': schedule(run_every=10),
#     },
#     'run-execute-scheduled-commands': {
#         'task': 'app.tasks.execute_scheduled_commands_task',
#         'schedule': crontab(minute='*/1'),  # Executes every minute
#     },
# }

# @app.task(bind=True)
# def debug_task(self):
#     print(f'Request: {self.request!r}')

# if __name__ == '__main__':
#     logger.info('Celery app initialized')



#print("Celery Beat schedule:", app.conf.beat_schedule)


# Don't initialize MQTT here, do it after apps are loaded