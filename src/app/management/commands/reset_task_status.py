from django.core.management.base import BaseCommand



class Command(BaseCommand):
    help = 'Resets the task execution status.'

    def handle(self, *args, **kwargs):
        from app.models import TaskExecution
        TaskExecution.reset_task_status('start-mqtt-client-once')
        self.stdout.write(self.style.SUCCESS('Successfully reset the task status.'))
