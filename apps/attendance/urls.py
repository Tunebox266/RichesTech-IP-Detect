# attendance/urls.py
from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    # Sessions
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    path('sessions/create/', views.session_create, name='session_create'),
    path('sessions/<int:pk>/edit/', views.session_edit, name='session_edit'),
    path('sessions/<int:pk>/qr/', views.generate_session_qr, name='generate_session_qr'),
    
    # Marking attendance
    path('mark/', views.mark_attendance, name='mark_attendance'),
    path('mark/qr/', views.mark_attendance_qr, name='mark_attendance_qr'),
    path('mark/manual/', views.mark_attendance_manual, name='mark_attendance_manual'),
    
    # Main attendance views
    path('mark/', views.mark_attendance, name='mark_attendance'),
    path('session/<int:session_id>/attendance/', views.get_session_attendance, name='get_session_attendance'),
    path('lookup-student/', views.lookup_student, name='lookup_student'),
    path('checkin/', views.checkin_student, name='checkin_student'),
    path('qr-checkin/', views.qr_checkin, name='qr_checkin'),
    path('checkin-all/<int:session_id>/', views.checkin_all, name='checkin_all'),
    path('bulk-checkin/<int:session_id>/', views.bulk_checkin, name='bulk_checkin'),
    
    # Session management
    path('get-sessions/', views.get_sessions, name='get_sessions'),
    path('session/<int:session_id>/download-qr/', views.download_session_qr, name='download_qr'),
    path('session/<int:session_id>/export-attendance/', views.export_session_attendance, name='export_session_attendance'),
    path('session/<int:session_id>/print-attendance/', views.print_attendance, name='print_attendance'),
    path('session/<int:session_id>/send-reminder/', views.send_session_reminder, name='send_session_reminder'),
    path('session/<int:session_id>/extend/', views.extend_session, name='extend_session'),
    
    # Manual check-in
    path('manual-checkin/<int:session_id>/', views.manual_checkin, name='manual_checkin'),
    
    # My attendance
    path('my-attendance/', views.my_attendance, name='my_attendance'),
    
    # Reports
    path('reports/', views.attendance_reports, name='attendance_reports'),
    path('export/<int:session_id>/', views.export_attendance_csv, name='export_attendance_csv'),
]