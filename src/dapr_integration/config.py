# dapr_integration/config.py
from django.conf import settings

# Dapr configuration settings
DAPR_PUBLISHER_HOST = getattr(settings, 'DAPR_PUBLISHER_HOST', 'dapr-mqtt-publisher')
DAPR_SUBSCRIBER_HOST = getattr(settings, 'DAPR_SUBSCRIBER_HOST', 'dapr-mqtt-subscriber')
DAPR_HTTP_PORT = getattr(settings, 'DAPR_HTTP_PORT', 3500)
DAPR_GRPC_PORT = getattr(settings, 'DAPR_GRPC_PORT', 50001)
DAPR_PUBSUB_NAME = getattr(settings, 'DAPR_PUBSUB_NAME', 'mqtt-pubsub')
DAPR_STATE_STORE = getattr(settings, 'DAPR_STATE_STORE', 'statestore')

# MQTT topics configuration
MQTT_TOPICS = [
    'smartreader/+/controlResult',
    'smartreader/+/manageResult',
    'smartreader/+/tagEvents',
    'smartreader/+/event',
    'smartreader/+/metrics',
    'smartreader/+/lwt'
]