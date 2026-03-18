# apps/api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name='api'

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'courses', views.CourseViewSet)
router.register(r'dues', views.DueViewSet)
router.register(r'payments', views.PaymentViewSet)
router.register(r'announcements', views.AnnouncementViewSet)
router.register(r'events', views.EventViewSet)
router.register(r'messages', views.MessageViewSet)
router.register(r'complaints', views.ComplaintViewSet)
router.register(r'attendance', views.AttendanceViewSet)

urlpatterns = [
    # API root
    path('', include(router.urls)),
    
    # Authentication
    path('auth/login/', views.api_login, name='api_login'),
    path('auth/logout/', views.api_logout, name='api_logout'),
    path('auth/me/', views.api_me, name='api_me'),
    
    # Search
    path('search/', views.api_search, name='api_search'),
    
    # Dashboard data
    path('dashboard/student/', views.student_dashboard_data, name='student_dashboard_data'),
    path('dashboard/admin/', views.admin_dashboard_data, name='admin_dashboard_data'),
    
    # Directory
    path('directory/', views.directory_list, name='directory_list'),
    path('directory/<int:pk>/', views.directory_detail, name='directory_detail'),
    
    # Attendance
    path('attendance/mark/', views.mark_attendance_api, name='mark_attendance_api'),
    path('attendance/sessions/', views.attendance_sessions, name='attendance_sessions'),
    path('attendance/qr/<int:session_id>/', views.generate_attendance_qr, name='generate_attendance_qr'),
     
    # ===== MESSAGING API =====
    path('messages/inbox/', views.inbox, name='api_inbox'),
    path('messages/sent/', views.sent_messages, name='api_sent'),
    path('messages/unread-count/', views.unread_messages_count, name='unread_messages_count'),  # This matches your view
    path('messages/unread-count/', views.unread_count, name='unread_count'),
    path('messages/mark-read/<int:pk>/', views.mark_message_read, name='mark_message_read'),
    
    # ===== NOTIFICATIONS API =====
    path('notifications/unread-count/', views.unread_notifications_count, name='unread_notifications_count'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:pk>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # ===== CONTACT MESSAGES API =====
    path('contact/new-count/', views.new_contact_messages_count, name='new_contact_messages_count'),
    path('contact/messages/', views.contact_messages_list, name='contact_messages_list'),
    path('contact/messages/<int:pk>/', views.contact_message_detail, name='contact_message_detail'),
    path('contact/messages/<int:pk>/mark-read/', views.mark_contact_message_read, name='mark_contact_message_read'),
    path('contact/messages/<int:pk>/reply/', views.reply_contact_message_api, name='reply_contact_message_api'),
    
    # Complaints
    path('complaints/my/', views.my_complaints, name='my_complaints'),
    path('complaints/<int:pk>/respond/', views.respond_to_complaint, name='respond_to_complaint'),
     # ===== MESSAGING API =====
    path('messages/inbox/', views.inbox, name='api_inbox'),
    path('messages/sent/', views.sent_messages, name='api_sent'),
    path('messages/unread-count/', views.unread_messages_count, name='unread_messages_count'),  # ADD THIS LINE
    path('messages/mark-read/<int:pk>/', views.mark_message_read, name='mark_message_read'),
    # Statistics
    path('statistics/payments/', views.payment_statistics, name='payment_statistics'),
    path('statistics/attendance/', views.attendance_statistics, name='attendance_statistics'),
] 