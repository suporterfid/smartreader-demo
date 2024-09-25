from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('readers/', views.reader_list, name='reader_list'),
    path('readers/send_command/', views.send_command_to_readers, name='send_command_to_readers'),
    path('readers/add/', views.reader_create, name='reader_create'),
    path('readers/<int:reader_id>/mode/', views.mode_command, name='mode_command'),
    path('tag-events/', views.tag_event_list, name='tag_event_list'),
    path('detailed-status-events/', views.detailed_status_event_list, name='detailed_status_event_list'),
    path('detailed-status-events/<int:event_id>/', views.detailed_status_event_detail, name='detailed_status_event_detail'),
    
    path('login/', auth_views.LoginView.as_view(template_name='app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    # Other URL patterns
]
