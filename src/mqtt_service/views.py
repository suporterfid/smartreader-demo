import os
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from app.authentication import APIKeyAuthentication
from .services import process_mqtt_message

logger = logging.getLogger(__name__)

class ProcessMQTTMessageView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Extract topic and data from Dapr cloud event
            topic = request.data.get('topic', '')
            payload = request.data.get('data', {})  # Dapr wraps message in 'data' field
            
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
        except Exception as e:
            logger.error(f"Error processing MQTT message: {str(e)}")
            return Response(
                {'error': f'Internal server error: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
