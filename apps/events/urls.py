# events/urls.py
from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # Public event views
    path('', views.event_list, name='event_list'),
    path('<int:pk>/', views.event_detail, name='event_detail'),
    
    # Student event registration
    path('<int:pk>/register/', views.event_register, name='event_register'),
    path('<int:pk>/unregister/', views.event_unregister, name='event_unregister'),
    
    # My events (for logged in users)
    path('my-events/', views.my_events, name='my_events'),
    # apps/events/urls.py
    path('<int:pk>/feedback/', views.event_feedback, name='feedback'),
    
    # Student-specific events
    path('student/<int:student_id>/', views.student_events, name='student_events'),
    
    # Attendance check-in
    path('session-check-in/<int:session_id>/', views.session_check_in, name='session_check_in'),
    path('check-in/', views.session_check_in_code, name='session_check_in_code'),
    
    # Staff/Admin only views
    path('create/', views.event_create, name='event_create'),
    path('<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('<int:pk>/attendees/', views.event_attendees, name='event_attendees'),
    path('attendee/<int:attendee_id>/mark-attendance/', views.mark_attendance, name='mark_attendance'),
    path('<int:event_id>/bulk-mark-attendance/', views.bulk_mark_attendance, name='bulk_mark_attendance'),  
    path('<int:event_id>/export-attendees/', views.export_attendees, name='export_attendees'),  # <-- new
    
    # Session management
    path('<int:event_id>/sessions/create/', views.session_create, name='session_create'),
    #path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    
    
    # Session management URLs
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    path('sessions/<int:session_id>/edit/', views.session_edit, name='session_edit'),
    path('sessions/<int:session_id>/delete/', views.session_delete, name='session_delete'),
    path('sessions/<int:session_id>/manual-checkin/', views.manual_checkin, name='manual_check_in'),
    path('sessions/<int:session_id>/download-qr/', views.download_session_qr, name='download_session_qr'),
    path('sessions/<int:session_id>/export-attendance/', views.export_session_attendance, name='export_session_attendance'),
    path('sessions/<int:session_id>/print-attendance/', views.print_attendance, name='print_attendance'),
    path('sessions/<int:session_id>/send-reminder/', views.send_session_reminder, name='send_session_reminder'),
    path('sessions/<int:session_id>/extend/', views.extend_session, name='extend_session'),
    
    # API endpoints
    path('lookup-student/', views.lookup_student_api, name='lookup_student_api'),
    path('manual-checkin-api/', views.manual_checkin_api, name='manual_checkin_api'),
]