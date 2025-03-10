# mqtt_service/apps.py

from django.apps import AppConfig

class MqttServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mqtt_service'

    def ready(self):
        pass