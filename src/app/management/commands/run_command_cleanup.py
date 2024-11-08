import logging
import time
from django.core.management.base import BaseCommand
from django.core.wsgi import get_wsgi_application
from app.tasks import process_and_cleanup_commands

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the command cleanup service'

    def handle(self, *args, **options):
        application = get_wsgi_application()

        logger.info("Starting command cleanup service...")

        while True:
            try:
                process_and_cleanup_commands()
                logger.debug("Processed and cleaned up commands")
            except Exception as e:
                logger.error(f"Error cleaning up commands: {e}")

            time.sleep(10)  # Run every 10 seconds