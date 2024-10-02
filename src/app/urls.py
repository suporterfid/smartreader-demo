from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('readers/', views.reader_list, name='reader_list'),
    path('readers/add/', views.reader_create, name='reader_create'),
    path('readers/<int:reader_id>/mode/', views.mode_command, name='mode_command'),
    path('readers/edit/<int:pk>/', views.reader_edit, name='reader_edit'),

    #path('readers/send_command/', views.send_command_to_readers, name='send_command_to_readers'),
    path('send-command/<int:reader_id>/', views.send_command, name='send_command'),
    path('command-history/', views.command_history, name='command_history'),
    path('command-detail/<int:command_id>/', views.command_detail, name='command_detail'),

    path('tag-events/', views.tag_event_list, name='tag_event_list'),
    path('detailed-status-events/', views.detailed_status_event_list, name='detailed_status_event_list'),
    path('detailed-status-events/<int:event_id>/', views.detailed_status_event_detail, name='detailed_status_event_detail'),
    
    path('alerts/', views.alert_list, name='alert_list'),
    path('alerts/create/', views.alert_create, name='alert_create'),
    path('alerts/<int:pk>/edit/', views.alert_edit, name='alert_edit'),
    path('alerts/<int:pk>/delete/', views.alert_delete, name='alert_delete'),
    path('alerts/<int:pk>/toggle/', views.alert_toggle, name='alert_toggle'),
    path('alert-logs/', views.alert_log_list, name='alert_log_list'),

    path('scheduled-commands/', views.scheduled_command_list, name='scheduled_command_list'),
    path('scheduled-commands/add/', views.scheduled_command_create, name='scheduled_command_create'),
    path('scheduled-commands/edit/<int:pk>/', views.scheduled_command_edit, name='scheduled_command_edit'),
    path('scheduled-commands/delete/<int:pk>/', views.scheduled_command_delete, name='scheduled_command_delete'),
    
    path('login/', auth_views.LoginView.as_view(template_name='app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    # Other URL patterns
]
