import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class DaprPubSub:
    def __init__(self, pubsub_name="mqtt-pubsub", dapr_port=3500):
        self.pubsub_name = pubsub_name
        self.dapr_url = f"http://dapr-sidecar-publisher:{dapr_port}/v1.0"

    def publish(self, topic: str, data: dict) -> bool:
        """Publish a message to a topic via Dapr"""
        try:
            url = f"{self.dapr_url}/publish/{self.pubsub_name}/{topic}"
            response = requests.post(url, json=data)

            if response.status_code == 200:
                logger.info(f"Successfully published message to {topic}")
                return True
            else:
                logger.error(f"Failed to publish message: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error publishing message: {str(e)}")
            return False

    def subscribe(self, topic: str, route: str):
        """Subscribe to a topic"""
        try:
            subscription = {
                "pubsubname": self.pubsub_name,
                "topic": topic,
                "route": route
            }

            url = f"{self.dapr_url}/subscribe"
            response = requests.post(url, json=[subscription])

            if response.status_code == 200:
                logger.info(f"Successfully subscribed to {topic}")
                return True
            else:
                logger.error(f"Failed to subscribe: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error subscribing to topic: {str(e)}")
            return False