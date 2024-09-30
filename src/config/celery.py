import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create the Celery app
app = Celery('config')

# Load task modules from all registered Django app configs.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'process-and-cleanup-commands': {
        'task': 'app.tasks.process_and_cleanup_commands',
        'schedule': 10.0,
    },
    'execute-scheduled-commands': {
        'task': 'app.tasks.execute_scheduled_commands_task',
        'schedule': 60.0,  # Run every minute
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

def init_mqtt():
    from django.conf import settings
    if not settings.TESTING:
        from app.mqtt_client import get_mqtt_client
        get_mqtt_client()

@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    init_mqtt()

# Don't initialize MQTT here, do it after apps are loaded