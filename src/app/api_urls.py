from django.urls import path
from .api_views import CommandDetailView, ReaderListView, ReaderDetailView, TagEventListView, CommandCreateView

urlpatterns = [
    path('readers/', ReaderListView.as_view(), name='api-reader-list'),
    path('readers/<str:serial_number>/', ReaderDetailView.as_view(), name='api-reader-detail'),
    path('tag-events/', TagEventListView.as_view(), name='api-tag-event-list'),
    path('commands/', CommandCreateView.as_view(), name='api-command-create'),
    path('commands/<str:command_id>/', CommandDetailView.as_view(), name='command-detail'),
]