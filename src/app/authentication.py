import os
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class APIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None

        expected_key = os.environ.get('API_KEY')
        if not expected_key:
            raise AuthenticationFailed(_('API key not configured'))

        if api_key == expected_key:
            # Use a system user for API authentication
            user, _ = User.objects.get_or_create(
                username='api_user',
                defaults={'is_active': True}
            )
            return (user, None)
        
        raise AuthenticationFailed(_('Invalid API key'))
