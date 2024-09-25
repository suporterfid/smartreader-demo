# src/app/management/commands/populate_test_data.py

from django.core.management.base import BaseCommand
from app.models import Reader

class Command(BaseCommand):
    help = 'Populate initial database with a test reader'

    def handle(self, *args, **options):
        Reader.objects.create(
            serial_number='37022341016',
            ip_address='192.168.68.248',
            location='impinj-15-2b-62',
            enabled=True
        )
        self.stdout.write('Test reader created successfully')
