# mqtt_service/apps.py

from django.apps import AppConfig
from django.db.models.signals import post_migrate

class MqttServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mqtt_service'

    def ready(self):
        # Connect the post_migrate signal to the initialize_mqtt_manager function
        post_migrate.connect(self.initialize_mqtt_manager, sender=self)
    
    def initialize_mqtt_manager(self, sender, **kwargs):
        # Import and initialize the mqtt_manager
        from .mqtt_manager import mqtt_manager
        #mqtt_manager.connect()