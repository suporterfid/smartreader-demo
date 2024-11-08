import json
import logging
import requests
from typing import Any, Optional

logger = logging.getLogger(__name__)

class DaprState:
    def __init__(self, store_name="statestore", dapr_port=3500):
        self.store_name = store_name
        self.dapr_url = f"http://localhost:{dapr_port}/v1.0"

    def save_state(self, key: str, value: Any) -> bool:
        """Save a value to the state store"""
        try:
            url = f"{self.dapr_url}/state/{self.store_name}"
            state_item = [{
                "key": key,
                "value": value
            }]

            response = requests.post(url, json=state_item)

            if response.status_code == 204:
                logger.info(f"Successfully saved state for key {key}")
                return True
            else:
                logger.error(f"Failed to save state: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
            return False

    def get_state(self, key: str) -> Optional[Any]:
        """Get a value from the state store"""
        try:
            url = f"{self.dapr_url}/state/{self.store_name}/{key}"
            response = requests.get(url)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return None
            else:
                logger.error(f"Failed to get state: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error getting state: {str(e)}")
            return None

# Create a singleton instance
dapr_state = DaprState()