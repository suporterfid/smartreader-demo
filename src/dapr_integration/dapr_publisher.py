# dapr_integration/dapr_publisher.py
from dapr.clients import DaprClient
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class DaprMQTTPublisher:
    def __init__(self):
        self.pubsub_name = 'mqtt-pub'
        self._client = None

    @property
    def client(self) -> DaprClient:
        if self._client is None:
            self._client = DaprClient()
        return self._client

    def publish(self, topic: str, message: Dict[str, Any], timeout: Optional[float] = None) -> bool:
        """
        Publish a message to an MQTT topic via Dapr
        
        Args:
            topic: MQTT topic to publish to
            message: Dictionary containing the message data
            timeout: Optional timeout in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Publishing message to topic {topic}")
            self.client.publish_event(
                pubsub_name=self.pubsub_name,
                topic_name=topic,
                data=json.dumps(message),
                data_content_type="application/json",
                publish_timeout=timeout
            )
            logger.info(f"Successfully published message to {topic}")
            return True
        except Exception as e:
            logger.error(f"Error publishing message to {topic}: {str(e)}")
            return False

    def close(self):
        """Close the Dapr client connection"""
        if self._client:
            self._client.close()
            self._client = None