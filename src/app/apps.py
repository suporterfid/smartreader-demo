import sys
from django.apps import AppConfig
import threading

from django.conf import settings

class AppConfig(AppConfig):
    name = 'app'

    # def ready(self):
    #     if not hasattr(self, 'initialized'):
    #         self.initialized = True
    #         from .mqtt_client import mqtt_manager
    #         threading.Thread(target=mqtt_manager.run, daemon=True).start()

    def ready(self):
        if not settings.TESTING:
            from config.celery import init_mqtt
            init_mqtt()