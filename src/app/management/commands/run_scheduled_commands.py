import logging
import time
from django.core.management.base import BaseCommand
from django.core.wsgi import get_wsgi_application
from app.tasks import execute_scheduled_commands_task

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the scheduled commands service'

    def handle(self, *args, **options):
        application = get_wsgi_application()

        logger.info("Starting scheduled commands service...")

        while True:
            try:
                execute_scheduled_commands_task()
                logger.debug("Executed scheduled commands")
            except Exception as e:
                logger.error(f"Error executing scheduled commands: {e}")

            time.sleep(60)  # Run every minute