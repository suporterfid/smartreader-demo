import sys
from django.apps import AppConfig
import threading

class AppConfig(AppConfig):
    name = 'app'

    def ready(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            from . import mqtt_client
            threading.Thread(target=mqtt_client.start_client).start()
