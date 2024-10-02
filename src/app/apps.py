import sys
import logging
from django.apps import AppConfig
from django.core.checks import register, Warning
import threading
from django.conf import settings
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from celery import shared_task
from celery.schedules import schedule
from celery.schedules import timedelta
from celery.schedules import crontab

logger = logging.getLogger(__name__)

# def create_periodic_tasks(sender, **kwargs):
#     from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
    
#     # Create an interval schedule
#     schedule, created = IntervalSchedule.objects.get_or_create(
#         every=10,
#         period=IntervalSchedule.SECONDS,
#     )
    
#     # Create a periodic task
#     PeriodicTask.objects.get_or_create(
#         name='Process and Cleanup Commands',
#         task='app.tasks.process_and_cleanup_commands',
#         interval=schedule,
#     )
    
#     # Create a crontab schedule
#     cron_schedule, _ = CrontabSchedule.objects.get_or_create(
#         minute='*/1'
#     )
    
#     # Create another periodic task
#     PeriodicTask.objects.get_or_create(
#         name='Execute Scheduled Commands',
#         task='app.tasks.execute_scheduled_commands_task',
#         crontab=cron_schedule,
#     )

class AppConfig(AppConfig):
    name = 'app'

    def ready(self):
        from celery import current_app
        print(f"Registered Celery tasks: {current_app.tasks.keys()}")
        print(f"Current beat schedule: {current_app.conf.beat_schedule}")
        # post_migrate.connect(create_periodic_tasks, sender=self)

        # try:
        #     from app.tasks import execute_scheduled_commands_task, process_and_cleanup_commands

        #     # Manually trigger the task
        #     process_and_cleanup_commands.apply_async()
        #     execute_scheduled_commands_task.apply_async()

        #     # Ensure the task is scheduled for future runs
        #     current_app.add_periodic_task(
        #         timedelta(seconds=10), 
        #         process_and_cleanup_commands.s(),
        #         name='Process and Cleanup Command'
        #     )

        #     current_app.add_periodic_task(
        #         crontab(hour=0, minute=0),
        #         execute_scheduled_commands_task.s(),
        #         name='Execute Scheduled Commands'
        #     )
        # except Exception as e:
        #     logger.error(f"Error processing commands: {e}")
        
        if not settings.TESTING:
            print('############### AppConfig ready ')

@register()
def check_celery_beat_schedule(app_configs, **kwargs):
    from celery import current_app
    if not current_app.conf.beat_schedule:
        return [Warning(
            'Celery beat schedule is empty',
            hint='Check your celery.py configuration',
            id='app.W001',
        )]
    return []
