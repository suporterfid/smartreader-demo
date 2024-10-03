from django.http import JsonResponse
from django.utils.translation import gettext as _
from .models import APIKey
import logging

logger = logging.getLogger(__name__)

class APIKeyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/'):
            api_key = request.headers.get('X-API-Key')
            if not api_key:
                logger.warning("API request without API key")
                return JsonResponse({'error': _('API key is missing')}, status=401)

            try:
                api_key_obj = APIKey.objects.get(key=api_key, is_active=True)
                request.user = api_key_obj.user
            except APIKey.DoesNotExist:
                logger.warning(f"Invalid API key used: {api_key}")
                return JsonResponse({'error': _('Invalid API key')}, status=401)

        response = self.get_response(request)
        return response