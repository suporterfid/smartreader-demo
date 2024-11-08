from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from app.authentication import APIKeyAuthentication
from .services import process_mqtt_message

class ProcessMQTTMessageView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        topic = request.data.get('topic')
        payload = request.data.get('payload')
        
        if not topic or not payload:
            return Response(
                {'error': 'Both topic and payload are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        success = process_mqtt_message(topic, payload)
        
        if success:
            return Response({'status': 'success'})
        else:
            return Response(
                {'error': 'Failed to process message'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
