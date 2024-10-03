from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import APIKey
from django.utils.translation import gettext_lazy as _

class APIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None

        try:
            api_key = APIKey.objects.get(key=api_key, is_active=True)
            return (api_key.user, None)
        except APIKey.DoesNotExist:
            raise AuthenticationFailed(_('Invalid API key'))