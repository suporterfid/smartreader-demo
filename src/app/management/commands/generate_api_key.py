from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from app.models import APIKey
from django.utils.translation import gettext as _

class Command(BaseCommand):
    help = 'Generates an API key for a given user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help=_('The username of the user to generate an API key for'))

    def handle(self, *args, **options):
        username = options['username']
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(_('User "%s" does not exist') % username)

        api_key, created = APIKey.objects.get_or_create(user=user)
        if not created:
            api_key.key = api_key.generate_key()
            api_key.save()

        self.stdout.write(self.style.SUCCESS(_('API key for user "%s" is: %s') % (username, api_key.key)))
