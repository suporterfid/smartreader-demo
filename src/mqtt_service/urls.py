from django.urls import path
from . import views

urlpatterns = [
    path('api/mqtt/process/', views.ProcessMQTTMessageView.as_view(), name='process_mqtt_message'),
    
]